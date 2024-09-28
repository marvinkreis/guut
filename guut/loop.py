import re
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from itertools import dropwhile
from random import randbytes
from typing import List, Literal, Tuple

from loguru import logger

from guut.llm import AssistantMessage, Conversation, LLMEndpoint, Message
from guut.logging import ConversationLogger, MessagePrinter
from guut.parsing import detect_markdown_code_blocks, extract_markdown_code_blocks
from guut.problem import AltExperimentResult, ExperimentResult, Problem, TestResult, ValidationResult
from guut.prompts import PromptCollection


class State(str, Enum):
    # The conversation is empty.
    # Applies to: Nothing
    EMPTY = "empty"

    # The prompt including the problem description have been stated.
    # Applies to: UserMsg with problem description
    INITIAL = "initial"

    # The LLM has stated an experiment.
    # Applies to: AssistantMsg with experiment description.
    EXPERIMENT_STATED = "experiment_stated"

    # The experiment does not compile.
    # Applies to: UserMsg with compilation result.
    EXPERIMENT_DOESNT_COMPILE = "experiment_doesnt_compile"

    # The experiment result was given to the LLM.
    # Applies to: UserMsg with experiment result.
    EXPERIMENT_RESULTS_GIVEN = "experiment_results_given"

    # The LLM has finished debugging and is ready to write the test.
    # FINISHED_DEBUGGING = "finished_debugging"

    # Instructions for writing the unit test have been stated.
    # Applies to: UserMsg with test instructions.
    TEST_INSTRUCTIONS_GIVEN = "test_instructions_given"

    # The LLM has stated a test.
    # Applies to: AssistantMsg with test.
    TEST_STATED = "test_stated"

    # The test does not compile.
    # Applies to: UserMsg with compilation result.
    TEST_DOESNT_COMPILE = "test_invalid"

    # The test does not detect the mutant.
    # Applies to: UserMsg with test result.
    TEST_DOESNT_DETECT_MUTANT = "test_doesnt_detect_mutant"

    # The LLM has claimed the mutant to be equivalent
    # Applies to: AssistantMsg with equivalence claim
    CLAIMED_EQUIVALENT = "claimed_equivalent"

    # The LLM has claimed the mutant to be equivalent
    # Applies to: UserMsg with instructions for how to continue after equivalence claim.
    EQUIVALENCE_MESSAGE_GIVEN = "equivalence_message_given"

    # The loop has concluded normally.
    # Applies to: UserMsg with result.
    DONE = "done"

    # The LLM did not give a complete response.
    # Applies to: Any incomplete AssistantMsg
    INCOMPLETE_RESPONSE = "incomplete_response"

    # The LLM did not give a complete response.
    # Applies to: UserMsg with instructions for how to continue after incomplete response.
    INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN = "incomplete_response_instructions_given"

    # The conversation was aborted.
    # Applies to: UserMsg containing the reason.
    ABORTED = "aborted"

    # The conversation is in an unknown or unrecoverable state.
    # Applies to: Nothing, it's a placeholder.
    INVALID = "invalid"


ActionKind = Literal["observation", "experiment", "test", "equivalence", "none"]


@dataclass
class ExperimentDescription:
    text: str
    code: str
    debugger_script: str | None
    kind: Literal["observation", "experiment", "none"]


@dataclass
class TestDescription:
    text: str
    code: str


@dataclass
class EquivalenceClaim:
    text: str


@dataclass
class ResponseSection:
    text: str
    code_blocks: List[str]
    debugger_blocks: List[str]
    kind: ActionKind


@dataclass
class Response:
    text: str
    sections: List[ResponseSection]

    def _guess_section(self, kind: ActionKind) -> ResponseSection | None:
        matches_with_code = [s for s in self.sections if s.kind == kind and s.code_blocks]
        matches_without_code = [s for s in self.sections if s.kind == kind and not s.code_blocks]
        if matches_with_code:
            return matches_with_code[-1]
        elif matches_without_code:
            return matches_without_code[-1]
        else:
            return None

    def _guess_code_blocks(self, section: ResponseSection) -> Tuple[str | None, str | None]:
        return (
            section.code_blocks[-1] if section.code_blocks else None,
            section.debugger_blocks[-1] if section.debugger_blocks else None,
        )

    def guess_action(self) -> Tuple[ExperimentDescription | TestDescription | None, EquivalenceClaim | None]:
        claim = None
        if section := self._guess_section("equivalence"):
            claim = EquivalenceClaim(text=section.text)

        if (section := self._guess_section("test")) and section.code_blocks:
            code, debugger_script = self._guess_code_blocks(section)
            if code:
                return TestDescription(text=section.text, code=code), claim
        elif (section := self._guess_section("experiment")) and section.code_blocks:
            code, debugger_script = self._guess_code_blocks(section)
            if code:
                return ExperimentDescription(
                    kind="experiment",
                    text=section.text,
                    code=code,
                    debugger_script=debugger_script,
                ), claim
        elif (section := self._guess_section("observation")) and section.code_blocks:
            code, debugger_script = self._guess_code_blocks(section)
            if code:
                return ExperimentDescription(
                    kind="observation",
                    text=section.text,
                    code=code,
                    debugger_script=debugger_script,
                ), claim
        elif (section := self._guess_section("none")) and section.code_blocks:
            code, debugger_script = self._guess_code_blocks(section)
            if code:
                return ExperimentDescription(
                    kind="none",
                    text=section.text,
                    code=code,
                    debugger_script=debugger_script,
                ), claim

        return None, claim

    def guess_experiment(self) -> ExperimentDescription | None:
        action, claim = self.guess_action()
        if isinstance(action, TestDescription):
            return ExperimentDescription(text=action.text, code=action.code, debugger_script=None, kind="experiment")
        if isinstance(action, EquivalenceClaim):
            return None
        return action

    def guess_test(self) -> TestDescription | None:
        action, claim = self.guess_action()
        if isinstance(action, ExperimentDescription):
            return TestDescription(text=action.text, code=action.code)
        if isinstance(action, EquivalenceClaim):
            return None
        return action


@dataclass
class Test(TestDescription):
    validation_result: ValidationResult
    result: TestResult | None
    kills_mutant: bool

    @staticmethod
    def with_description(
        description: TestDescription, validation_result: ValidationResult, result: TestResult | None, kills_mutant: bool
    ) -> "Test":
        return Test(
            text=description.text,
            code=description.code,
            validation_result=validation_result,
            result=result,
            kills_mutant=kills_mutant,
        )


@dataclass
class Experiment(ExperimentDescription):
    validation_result: ValidationResult
    result: ExperimentResult | AltExperimentResult | None

    @staticmethod
    def with_description(
        description: ExperimentDescription,
        validation_result: ValidationResult,
        result: ExperimentResult | AltExperimentResult | None,
    ) -> "Experiment":
        return Experiment(
            text=description.text,
            code=description.code,
            debugger_script=description.debugger_script,
            kind=description.kind,
            validation_result=validation_result,
            result=result,
        )


@dataclass
class LoopSettings:
    max_num_experiments: int = 99
    max_retries_for_invalid_test: int = 99
    max_num_incomplete_responses: int = 2
    max_num_turns: int = 10
    test_inctructions_after_turn: int = 8
    altexp: bool = False
    shortexp: bool = False
    is_baseline: bool = False


@dataclass
class Result:
    # main info
    tests: List[Test]
    experiments: List[Experiment]
    conversation: Conversation
    mutant_killed: bool
    equivalence: EquivalenceClaim | None

    # extra info
    timestamp: datetime
    endpoint: LLMEndpoint
    prompts: PromptCollection
    problem: Problem
    settings: LoopSettings
    id: str
    implementation: str

    def get_killing_test(self) -> Test | None:
        return next(filter(lambda test: test.kills_mutant, self.tests), None)


TEST_HEADLINE_REGEX = re.compile(r"^(#+) +([a-zA-Z0-9]+ +)*test", re.IGNORECASE)
EXPERIMENT_HEADLINE_REGEX = re.compile(r"^(#+) +([a-zA-Z0-9]+ +)*experiment", re.IGNORECASE)
OBSERVATION_HEADLINE_REGEX = re.compile(r"^(#+) +([a-zA-Z0-9]+ +)*observ", re.IGNORECASE)
EQUIVALENCE_HEADLINE_REGEX = re.compile(r"^(#+) +([a-zA-Z0-9]+ +)*equiv", re.IGNORECASE)


class Loop:
    def __init__(
        self,
        problem: Problem,
        endpoint: LLMEndpoint,
        prompts: PromptCollection | None = None,
        settings: LoopSettings | None = None,
        logger: ConversationLogger | None = None,
        printer: MessagePrinter | None = None,
        conversation: Conversation | None = None,
    ):
        if prompts is None:
            self.prompts = problem.get_default_prompts()
        else:
            self.prompts = prompts

        if settings is None:
            self.settings = LoopSettings()
        else:
            self.settings = settings

        self.problem = problem
        self.endpoint = endpoint
        self.logger = logger
        self.printer = printer

        if conversation is None:
            self.conversation = Conversation()
        else:
            self.conversation = conversation

        self.experiments: List[Experiment] = []
        self.tests: List[Test] = []
        self.equivalence: EquivalenceClaim | None = None
        self.id = self._generate_id()

    def perform_next_step(self):
        if self.printer:
            self.printer.print_new_messages(self.conversation)

        state = self.get_state()
        logger.info(state)

        self._perform_next_step(state)

        if self.printer:
            self.printer.print_new_messages(self.conversation)

        if self.logger:
            self.logger.log_conversation(self.conversation, name=self.id)

    def _perform_next_step(self, state: State):
        if state == State.EMPTY:
            self._init_conversation()
        elif state == State.INITIAL:
            self._prompt_for_action()
        elif state == State.EXPERIMENT_STATED:
            self._run_experiment()
        elif state == State.EXPERIMENT_DOESNT_COMPILE:
            self._prompt_for_action()
        elif state == State.EXPERIMENT_RESULTS_GIVEN:
            self._prompt_for_action()
        elif state == State.TEST_INSTRUCTIONS_GIVEN:
            self._prompt_for_action()
        elif state == State.TEST_STATED:
            self._run_test()
        elif state == State.TEST_DOESNT_COMPILE:
            self._prompt_for_action()
        elif state == State.TEST_DOESNT_DETECT_MUTANT:
            self._prompt_for_action()
        elif state == State.DONE:
            raise InvalidStateException(State.DONE)
        elif state == State.CLAIMED_EQUIVALENT:
            self._write_equivalence_message()
            # self._write_equivalence_result()
        elif state == State.EQUIVALENCE_MESSAGE_GIVEN:
            self._prompt_for_action()
        elif state == State.INCOMPLETE_RESPONSE:
            self._handle_incomplete_response()
        elif state == State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN:
            self._prompt_for_action()
        elif state == State.ABORTED:
            raise InvalidStateException(State.ABORTED)
        elif state == State.INVALID:
            raise InvalidStateException(State.INVALID)
        elif state is None:
            raise InvalidStateException(None)

    def iterate(self) -> Result:
        while self.get_state() not in [State.DONE, State.ABORTED, State.INVALID, None]:
            self.perform_next_step()
        return self.get_result()

    def get_state(self) -> State:
        if not self.conversation:
            return State.EMPTY
        elif tag := self.conversation[-1].tag:
            return State(tag)
        return State.INVALID

    def get_result(self) -> Result:
        killing_test_found = any([test.kills_mutant for test in self.tests])
        return Result(
            tests=self.tests,
            experiments=self.experiments,
            conversation=self.conversation,
            timestamp=datetime.now(),
            endpoint=self.endpoint,
            problem=self.problem,
            prompts=self.prompts,
            settings=self.settings,
            mutant_killed=killing_test_found,
            equivalence=self.equivalence,
            id=self.id,
            implementation="loop",
        )

    def add_msg(self, msg: Message, tag: State | None):
        if tag:
            msg.tag = tag
        self.conversation.append(msg)

    def _init_conversation(self):
        """it's hard to do sometimes"""
        if self.prompts.system_prompt:
            self.add_msg(self.prompts.system_prompt.render(), tag=None)
        self.add_msg(self.prompts.debug_prompt.render(self.problem, shortexp=self.settings.shortexp), tag=None)
        self.add_msg(self.prompts.problem_template.render(self.problem), State.INITIAL)

    def _prompt_for_action(self):
        response = self._complete()
        response = self._clean_response(response)

        relevant_text = self._concat_incomplete_responses(include_message=response)
        raw_experiment = self._parse_response(relevant_text)
        action, claim = raw_experiment.guess_action()

        test_instructions_stated = any(msg.tag == State.TEST_INSTRUCTIONS_GIVEN for msg in self.conversation)

        if claim:
            self.equivalence = claim

        if action is None:
            if claim is not None:
                self.add_msg(response, State.CLAIMED_EQUIVALENT)
                return
            else:
                self.add_msg(response, State.INCOMPLETE_RESPONSE)
                return

        if isinstance(action, TestDescription):
            self.add_msg(response, State.TEST_STATED)
            return

        if isinstance(action, ExperimentDescription):
            if action.kind == "experiment":
                self.add_msg(response, State.EXPERIMENT_STATED)
                return
            elif action.kind == "observation":
                self.add_msg(response, State.EXPERIMENT_STATED)
                return
            elif action.kind == "none" and test_instructions_stated:
                self.add_msg(response, State.TEST_STATED)
                return
            elif action.kind == "none" and not test_instructions_stated:
                self.add_msg(response, State.EXPERIMENT_STATED)
                return

    def _run_experiment(self):
        relevant_text = self._concat_incomplete_responses()
        raw_experiment = self._parse_response(relevant_text)
        experiment = raw_experiment.guess_experiment()

        if not isinstance(experiment, ExperimentDescription):
            raise InvalidStateException(
                State.EXPERIMENT_STATED, f"No experiment present but state is {State.EXPERIMENT_STATED.value}."
            )

        name = "Observation" if experiment.kind == "observation" else "Experiment"
        validation_result = self.problem.validate_code(experiment.code)
        if not validation_result.valid:
            new_message = self.prompts.experiment_doesnt_compile_template.render(result=validation_result, name=name)
            self.add_msg(new_message, State.EXPERIMENT_DOESNT_COMPILE)
            self.experiments.append(
                Experiment.with_description(experiment, validation_result=validation_result, result=None)
            )
        else:
            experiment_result = self.problem.run_experiment(
                experiment.code, experiment.debugger_script, collect_coverage=True, altexp=self.settings.altexp
            )
            new_message = self.prompts.experiment_results_template.render(
                result=experiment_result,
                name=name,
                altexp=isinstance(experiment_result, AltExperimentResult),
                shortexp=self.settings.shortexp,
            )
            self.add_msg(new_message, State.EXPERIMENT_RESULTS_GIVEN)
            experiment = replace(experiment, kind="observation" if experiment.kind == "observation" else "experiment")
            self.experiments.append(
                Experiment.with_description(experiment, validation_result=validation_result, result=experiment_result)
            )

        num_experiments = len([msg for msg in self.conversation if msg.tag == State.EXPERIMENT_STATED])
        num_tests = len([msg for msg in self.conversation if msg.tag == State.TEST_STATED])
        num_turns = num_experiments + num_tests

        if num_turns >= self.settings.max_num_turns:
            new_message = self.prompts.conversation_aborted_template.render(
                reason="too_many_turns", extra_reason="The LLM exceeded the allowed number of turns."
            )
            self.add_msg(new_message, State.ABORTED)

        elif (
            num_experiments == self.settings.max_num_experiments
            or num_turns == self.settings.test_inctructions_after_turn
        ):
            new_message = self.prompts.test_prompt.render(
                max_experiments_reached=(num_experiments == self.settings.max_num_experiments),
                num_turns_left=(self.settings.max_num_turns - num_turns),
            )
            self.add_msg(new_message, State.TEST_INSTRUCTIONS_GIVEN)

        elif num_experiments > self.settings.max_num_experiments:
            new_message = self.prompts.conversation_aborted_template.render(
                reason="too_many_experiments", extra_reason="The LLM exceeded the allowed number of experiments."
            )
            self.add_msg(new_message, State.ABORTED)

    def _run_test(self):
        relevant_text = self._concat_incomplete_responses()
        raw_experiment = self._parse_response(relevant_text)
        test = raw_experiment.guess_test()

        if not isinstance(test, TestDescription):
            raise InvalidStateException(State.TEST_STATED, f"No test present but state is {State.TEST_STATED.value}.")

        validation_result = self.problem.validate_code(test.code)
        if not validation_result.valid:
            new_message = self.prompts.test_doesnt_compile_template.render(
                result=validation_result,
            )
            self.add_msg(new_message, State.TEST_DOESNT_COMPILE)
            self.tests.append(
                Test.with_description(test, validation_result=validation_result, result=None, kills_mutant=False)
            )
        else:
            result = self.problem.run_test(test.code, collect_coverage=True)

            if result.correct.exitcode == 0 and result.mutant.exitcode != 0:
                new_message = self.prompts.results_template.render_for_test(
                    test=test.code, result=result, problem=self.problem
                )
                self.add_msg(new_message, State.DONE)

                self.tests.append(
                    Test.with_description(test, validation_result=validation_result, result=result, kills_mutant=True)
                )
                return
            else:
                new_message = self.prompts.test_doesnt_detect_mutant_template.render(
                    result=result, baseline=self.settings.is_baseline
                )
                self.add_msg(new_message, State.TEST_DOESNT_DETECT_MUTANT)
                self.tests.append(
                    Test.with_description(test, validation_result=validation_result, result=result, kills_mutant=False)
                )

        num_experiments = len([msg for msg in self.conversation if msg.tag == State.EXPERIMENT_STATED])
        num_tests = len([msg for msg in self.conversation if msg.tag == State.TEST_STATED])
        num_turns = num_experiments + num_tests

        if num_turns >= self.settings.max_num_turns:
            new_message = self.prompts.conversation_aborted_template.render(
                reason="too_many_turns", extra_reason="The LLM exceeded the allowed number of turns."
            )
            self.add_msg(new_message, State.ABORTED)
            return

        elif num_turns == self.settings.test_inctructions_after_turn:
            new_message = self.prompts.test_prompt.render(
                max_experiments_reached=False,
                num_turns_left=(self.settings.max_num_turns - num_turns),
            )
            self.add_msg(new_message, State.TEST_INSTRUCTIONS_GIVEN)

        if num_tests > self.settings.max_retries_for_invalid_test:
            new_message = self.prompts.conversation_aborted_template.render(
                reason="max_invalid_tests", extra_reason="The LLM has reached the maximum number of invalid tests."
            )
            self.add_msg(new_message, State.ABORTED)

    def _handle_incomplete_response(self):
        num_tries = len([msg for msg in self.conversation if msg.tag == State.INCOMPLETE_RESPONSE])
        if num_tries > self.settings.max_num_incomplete_responses:
            new_message = self.prompts.conversation_aborted_template.render(
                reason="incomplete_response", extra_reason="The LLM has given too many incomplete responses."
            )
            self.add_msg(new_message, State.ABORTED)
            return

        self.add_msg(self.prompts.incomplete_response_template.render(), State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN)

    def _write_equivalence_result(self):
        self.add_msg(self.prompts.results_template.render_for_equivalence(self.problem), State.DONE)

    def _write_equivalence_message(self):
        self.add_msg(self.prompts.equivalence_claim_template.render(), State.EQUIVALENCE_MESSAGE_GIVEN)

    def _clean_response(self, msg: AssistantMessage):
        content = self._remove_stop_word_residue(msg.content)
        return AssistantMessage(content=content + "\n", response=msg.response, usage=msg.usage, tag=msg.tag, id=msg.id)

    def _remove_stop_word_residue(self, text: str):
        lines = text.splitlines()

        def condition(line: str):
            if not line:
                return True
            if not line.strip():
                return True
            if all([c == "#" for c in line.strip()]):
                return True
            return False

        lines = reversed(list(dropwhile(condition, reversed(lines))))
        return "\n".join(lines)

    def _concat_incomplete_responses(self, include_message: Message | None = None):
        if include_message:
            relevant_messages = [include_message]
            messages = self.conversation
        else:
            relevant_messages = [self.conversation[-1]]
            messages = self.conversation[:-1]

        for msg in messages[::-1]:
            if msg.tag == State.INCOMPLETE_RESPONSE:
                relevant_messages = [msg] + relevant_messages
            elif msg.tag == State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN:
                continue
            else:
                break

        relevant_text = "\n".join(msg.content for msg in relevant_messages)
        return relevant_text

    def _parse_response(self, text: str) -> Response:
        sections = []

        section_kind = "none"
        section_level = 0
        section_lines = []

        for line, is_code in detect_markdown_code_blocks(text):
            if is_code:
                section_lines.append(line)
                continue

            kind: ActionKind = "none"
            level = 99
            if match := re.match(TEST_HEADLINE_REGEX, line):
                kind = "test"
                level = len(match.group(1))
            elif match := re.match(EXPERIMENT_HEADLINE_REGEX, line):
                kind = "experiment"
                level = len(match.group(1))
            elif match := re.match(OBSERVATION_HEADLINE_REGEX, line):
                kind = "observation"
                level = len(match.group(1))
            elif match := re.match(EQUIVALENCE_HEADLINE_REGEX, line):
                kind = "equivalence"
                level = 1

            if kind == "none":
                section_lines.append(line)
                continue

            if kind != section_kind or level <= section_level:
                # Start new section
                if section := self._parse_response_section("\n".join(section_lines), kind=section_kind):
                    sections.append(section)
                section_kind = kind
                section_level = level
                section_lines = [line]

            section_lines.append(line)

        if section_lines:
            if section := self._parse_response_section("\n".join(section_lines), kind=section_kind):
                sections.append(section)

        return Response(text=text, sections=sections)

    def _parse_response_section(self, text: str, kind: ActionKind) -> ResponseSection | None:
        markdown_blocks = extract_markdown_code_blocks(text)
        code_langs = self.problem.allowed_languages()
        dbg_langs = self.problem.allowed_debugger_languages()

        code_blocks = [block.code for block in markdown_blocks if (block.language or "") in code_langs]
        debugger_blocks = [block.code for block in markdown_blocks if (block.language or "") in dbg_langs]

        if code_blocks or (kind != "none"):
            return ResponseSection(kind=kind, text=text, code_blocks=code_blocks, debugger_blocks=debugger_blocks)
        else:
            return None

    def _generate_id(self) -> str:
        randchars = "".join(f"{b:02x}" for b in randbytes(4))
        id = "{}_{}".format(self.problem.get_description().format(), randchars)
        return id

    def _complete(self) -> AssistantMessage:
        return self.endpoint.complete(self.conversation, stop=self.prompts.stop_words)


class InvalidStateException(Exception):
    def __init__(self, state: State | None, message: str | None = None):
        self.state = state
        if message:
            super().__init__(message)
        else:
            super().__init__(f'Invalid loop state: {state.value if state else 'None'}')
