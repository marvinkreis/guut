import re
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from itertools import dropwhile
from random import randbytes
from typing import List, Literal, Tuple

from loguru import logger

from guut.formatting import format_message_pretty
from guut.llm import AssistantMessage, Conversation, LLMEndpoint, Message
from guut.logging import LOG_BASE_PATH
from guut.logging import Logger as ConversationLogger
from guut.parsing import detect_markdown_code_blocks, extract_markdown_code_blocks
from guut.problem import ExperimentResult, Problem, TestResult, ValidationResult
from guut.prompts import PromptCollection

LOG_PATH = LOG_BASE_PATH / "loop"
LOG_PATH.mkdir(parents=True, exist_ok=True)


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
    # Applies to: UserMst with compilation result.
    TEST_DOESNT_COMPILE = "test_invalid"

    # The test does not detect the mutant.
    # Applies to: UserMst with test result.
    TEST_DOESNT_DETECT_MUTANT = "test_doesnt_detect_mutant"

    # The LLM has finished writing the test.
    # Applies to: UserMst with test result.
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


@dataclass
class ExperimentOrTestDescription:
    text: str
    code: str
    raw: "RawExperiment"


@dataclass
class ExperimentDescription(ExperimentOrTestDescription):
    debugger_script: str | None
    kind: Literal["observation", "experiment", "none"]


@dataclass
class TestDescription(ExperimentOrTestDescription):
    pass


@dataclass
class RawExperimentSection:
    text: str
    code_blocks: List[str]
    debugger_blocks: List[str]
    kind: Literal["observation", "experiment", "test", "none"]


@dataclass
class RawExperiment:
    text: str
    sections: List[RawExperimentSection]

    def get_section(self, kind: Literal["observation", "experiment", "test", "none"]) -> RawExperimentSection | None:
        matches = [s for s in self.sections if s.kind == kind]
        return matches[-1] if matches else None

    def guess_code_blocks(self, section: RawExperimentSection) -> Tuple[str | None, str | None]:
        return (
            section.code_blocks[-1] if section.code_blocks else None,
            section.debugger_blocks[-1] if section.debugger_blocks else None,
        )

    def guess_experiment(self) -> ExperimentDescription | TestDescription | None:
        if (section := self.get_section("test")) and section.code_blocks:
            code, debugger_script = self.guess_code_blocks(section)
            if code:
                return TestDescription(text=section.text, code=code, raw=self)
        elif (section := self.get_section("experiment")) and section.code_blocks:
            code, debugger_script = self.guess_code_blocks(section)
            if code:
                return ExperimentDescription(
                    kind="experiment", text=section.text, code=code, debugger_script=debugger_script, raw=self
                )
        elif (section := self.get_section("observation")) and section.code_blocks:
            code, debugger_script = self.guess_code_blocks(section)
            if code:
                return ExperimentDescription(
                    kind="observation", text=section.text, code=code, debugger_script=debugger_script, raw=self
                )
        elif (section := self.get_section("none")) and section.code_blocks:
            code, debugger_script = self.guess_code_blocks(section)
            if code:
                return ExperimentDescription(
                    kind="none", text=section.text, code=code, debugger_script=debugger_script, raw=self
                )
        else:
            return None


@dataclass
class TestCase:
    description: TestDescription
    validation_result: ValidationResult
    result: TestResult | None
    kills_mutant: bool


@dataclass
class Experiment:
    description: ExperimentDescription
    validation_result: ValidationResult
    result: ExperimentResult | None


@dataclass
class Result:
    # main info
    tests: List[TestCase]
    experiments: List[Experiment]
    conversation: Conversation

    # extra info
    timestamp: datetime
    endpoint: LLMEndpoint
    prompts: PromptCollection
    problem: Problem
    max_retries_for_invalid_test: int
    max_num_incomplete_responses: int
    max_num_experiments: int

    def get_killing_test(self) -> TestCase | None:
        return next(filter(lambda test: test.kills_mutant, self.tests), None)


TEST_HEADLINE_REGEX = re.compile(r"^#+ (unit )?test", re.IGNORECASE)
EXPERIMENT_HEADLINE_REGEX = re.compile(r"^#+ experiment", re.IGNORECASE)
OBSERVATION_HEADLINE_REGEX = re.compile(r"^#+ observ", re.IGNORECASE)


class Loop:
    def __init__(
        self,
        problem: Problem,
        endpoint: LLMEndpoint,
        prompts: PromptCollection,
        conversation: Conversation | None = None,
        enable_log: bool = True,
        enable_print: bool = False,
        max_retries_for_invalid_test: int = 2,
        max_num_incomplete_responses: int = 2,
        max_num_experiments: int = 8,
    ):
        self.problem = problem
        self.endpoint = endpoint
        self.prompts = prompts
        self.enable_log = enable_log
        self.enable_print = enable_print

        if conversation is None:
            self.conversation = Conversation()
            self.new_messages: List[Message] = []
        else:
            self.conversation = conversation
            self.new_messages = conversation[::]

        self.max_retries_for_invalid_test = max_retries_for_invalid_test
        self.max_num_incimplete_responses = max_num_incomplete_responses
        self.max_num_experiments = max_num_experiments

        self.experiments: List[Experiment] = []
        self.testcases: List[TestCase] = []

        self.conversation.name = "{}_{}".format("".join(f"{b:x}" for b in randbytes(4)), self.problem.name())
        self.conversation_logger = ConversationLogger(LOG_PATH)
        self.timestamp = datetime.now()

    def perform_next_step(self):
        self._print_and_log_conversation()
        state = self.get_state()
        logger.info(state)
        self._perform_next_step(state)
        self._print_and_log_conversation()

    def _perform_next_step(self, state: State):
        if state == State.EMPTY:
            self._init_conversation()
        elif state == State.INITIAL:
            self._prompt_for_hypothesis_or_test()
        elif state == State.EXPERIMENT_STATED:
            self._run_experiment()
        elif state == State.EXPERIMENT_DOESNT_COMPILE:
            self._prompt_for_hypothesis_or_test()
        elif state == State.EXPERIMENT_RESULTS_GIVEN:
            self._prompt_for_hypothesis_or_test()
        elif state == State.TEST_INSTRUCTIONS_GIVEN:
            self._prompt_for_hypothesis_or_test()
        elif state == State.TEST_STATED:
            self._run_test()
        elif state == State.TEST_DOESNT_COMPILE:
            self._prompt_for_hypothesis_or_test()
        elif state == State.TEST_DOESNT_DETECT_MUTANT:
            self._prompt_for_hypothesis_or_test()
        elif state == State.DONE:
            raise InvalidStateException(State.DONE)
        elif state == State.INCOMPLETE_RESPONSE:
            self._handle_incomplete_response()
        elif state == State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN:
            self._prompt_for_hypothesis_or_test()
        elif state == State.ABORTED:
            raise InvalidStateException(State.ABORTED)
        elif state == State.INVALID:
            raise InvalidStateException(State.INVALID)
        elif state is None:
            raise InvalidStateException(None)

    def iterate(self):
        while self.get_state() not in [State.DONE, State.ABORTED, State.INVALID, None]:
            self.perform_next_step()

    def get_state(self) -> State:
        if not self.conversation:
            return State.EMPTY
        elif tag := self.conversation[-1].tag:
            return State(tag)
        return State.INVALID

    def get_result(self) -> Result:
        # TODO: translate timestamps, problem and endpoint
        return Result(
            tests=self.testcases,
            experiments=self.experiments,
            conversation=self.conversation,
            timestamp=self.timestamp,
            endpoint=self.endpoint,
            problem=self.problem,
            prompts=self.prompts,
            max_num_experiments=self.max_num_experiments,
            max_num_incomplete_responses=self.max_num_incimplete_responses,
            max_retries_for_invalid_test=self.max_retries_for_invalid_test,
        )

    def add_msg(self, msg: Message, tag: State | None):
        if tag:
            msg.tag = tag
        self.conversation.append(msg)
        self.new_messages.append(msg)

    def _init_conversation(self):
        """it's hard to do sometimes"""
        if self.prompts.system_prompt:
            self.add_msg(self.prompts.system_prompt.render(), tag=None)
        self.add_msg(self.prompts.debug_prompt.render(self.problem), tag=None)
        self.add_msg(self.prompts.problem_template.render(self.problem), State.INITIAL)

    def _prompt_for_hypothesis_or_test(self):
        response = self.endpoint.complete(self.conversation, stop=self.prompts.debug_stop_words)
        response = self._clean_response(response)

        relevant_text = self._concat_incomplete_responses(include_message=response)
        raw_experiment = self._parse_experiment_description(relevant_text)
        experiment = raw_experiment.guess_experiment()

        test_instructions_stated = any(msg.tag == State.TEST_INSTRUCTIONS_GIVEN for msg in self.conversation)

        if experiment is None:
            self.add_msg(response, State.INCOMPLETE_RESPONSE)
            return

        if isinstance(experiment, TestDescription):
            self.add_msg(response, State.TEST_STATED)
            return

        if isinstance(experiment, ExperimentDescription):
            if experiment.kind == "experiment":
                self.add_msg(response, State.EXPERIMENT_STATED)
                return
            elif experiment.kind == "observation":
                self.add_msg(response, State.EXPERIMENT_STATED)
                return
            elif experiment.kind == "none" and test_instructions_stated:
                self.add_msg(response, State.TEST_STATED)
                return
            elif experiment.kind == "none" and not test_instructions_stated:
                self.add_msg(response, State.EXPERIMENT_STATED)
                return

    def _run_experiment(self):
        relevant_text = self._concat_incomplete_responses()
        raw_experiment = self._parse_experiment_description(relevant_text)
        experiment = raw_experiment.guess_experiment()

        if not isinstance(experiment, ExperimentDescription):
            raise InvalidStateException(
                State.EXPERIMENT_STATED, f"No experiment present but state is {State.EXPERIMENT_STATED.value}."
            )

        validation_result = self.problem.validate_code(experiment.code)
        if not validation_result.valid:
            new_message = self.prompts.experiment_doesnt_compile_template.render(result=validation_result)
            self.add_msg(new_message, State.EXPERIMENT_DOESNT_COMPILE)
            self.experiments.append(
                Experiment(validation_result=validation_result, result=None, description=experiment)
            )
        else:
            experiment_result = self.problem.run_experiment(experiment.code, experiment.debugger_script)
            new_message = self.prompts.experiment_results_template.render(
                result=experiment_result, is_observation=(experiment.kind == "observation")
            )
            self.add_msg(new_message, State.EXPERIMENT_RESULTS_GIVEN)
            experiment = replace(experiment, kind="observation" if experiment.kind == "observation" else "experiment")
            self.experiments.append(
                Experiment(validation_result=validation_result, result=experiment_result, description=experiment)
            )

        num_experiments = len([msg for msg in self.conversation if msg.tag == State.EXPERIMENT_STATED])
        if num_experiments == self.max_num_experiments:
            new_message = self.prompts.test_prompt.render(max_iterations=True)
            self.add_msg(new_message, State.TEST_INSTRUCTIONS_GIVEN)
        elif num_experiments > self.max_num_experiments:
            new_message = self.prompts.conversation_aborted_template.render(
                reason="too_many_experiments", extra_reason="The LLM exceeded the allowed number of tests."
            )
            self.add_msg(new_message, State.ABORTED)

    def _run_test(self):
        relevant_text = self._concat_incomplete_responses()
        raw_experiment = self._parse_experiment_description(relevant_text)
        test = raw_experiment.guess_experiment()

        if not isinstance(test, TestDescription):
            raise InvalidStateException(State.TEST_STATED, f"No test present but state is {State.TEST_STATED.value}.")

        validation_result = self.problem.validate_code(test.code)
        if not validation_result.valid:
            new_message = self.prompts.test_doesnt_compile_template.render(
                result=validation_result,
            )
            self.add_msg(new_message, State.TEST_DOESNT_COMPILE)
            self.testcases.append(
                TestCase(description=test, validation_result=validation_result, result=None, kills_mutant=False)
            )
        else:
            result = self.problem.run_test(test.code)

            if result.correct.exitcode == 0 and result.mutant.exitcode != 0:
                new_message = self.prompts.results_template.render(test=test.code, result=result)
                self.add_msg(new_message, State.DONE)
                self.testcases.append(
                    TestCase(description=test, validation_result=validation_result, result=result, kills_mutant=True)
                )
            else:
                new_message = self.prompts.test_doesnt_detect_mutant_template.render(result=result)
                self.add_msg(new_message, State.TEST_DOESNT_DETECT_MUTANT)
                self.testcases.append(
                    TestCase(description=test, validation_result=validation_result, result=result, kills_mutant=False)
                )

        num_retries = len([msg for msg in self.conversation if msg.tag == State.TEST_DOESNT_COMPILE])
        if num_retries >= self.max_retries_for_invalid_test:
            new_message = self.prompts.conversation_aborted_template.render(
                reason="max_invalid_tests", extra_reason="The LLM has reached the maximum number of invalid tests."
            )
            self.add_msg(new_message, State.ABORTED)

    def _handle_incomplete_response(self):
        num_tries = len([msg for msg in self.conversation if msg.tag == State.INCOMPLETE_RESPONSE])
        if num_tries > self.max_num_incimplete_responses:
            new_message = self.prompts.conversation_aborted_template.render(
                reason="incomplete_response", extra_reason="The LLM has given too many incomplete responses."
            )
            self.add_msg(new_message, State.ABORTED)
            return

        msg_before = [msg for msg in self.conversation if msg.tag != State.INCOMPLETE_RESPONSE][-1]
        if isinstance(msg_before.tag, State):
            self.add_msg(
                self.prompts.incomplete_response_template.render(), State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN
            )
        else:
            raise InvalidStateException(None, f"No valid state before {State.INCOMPLETE_RESPONSE.value}.")

    def _clean_response(self, msg: AssistantMessage):
        content = self._remove_stop_word_residue(msg.content)
        return AssistantMessage(content=content + "\n", response=msg.response, usage=msg.usage, tag=msg.tag)

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

    def _print_and_log_conversation(self):
        if self.enable_print:
            for msg in self.new_messages:
                print(format_message_pretty(msg))
            self.new_messages = []
        if self.enable_log:
            self.conversation_logger.log_conversation(self.conversation, name=self.conversation.name or "")

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

    def _parse_experiment_description(self, text: str) -> RawExperiment:
        sections = []
        section_lines = []

        for line, is_code in reversed(detect_markdown_code_blocks(text)):
            section_lines.append(line)

            if is_code:
                continue

            kind = "none"
            if re.match(TEST_HEADLINE_REGEX, line):
                kind = "test"
            elif re.match(EXPERIMENT_HEADLINE_REGEX, line):
                kind = "experiment"
            elif re.match(OBSERVATION_HEADLINE_REGEX, line):
                kind = "observation"

            if kind != "none":
                section_text = "\n".join(reversed(section_lines))
                sections.append(self._parse_experiment_section(section_text, kind))
                section_lines = []

        if section_lines:
            section_text = "\n".join(reversed(section_lines))
            if section := self._parse_experiment_section(section_text, "none"):
                sections.append(section)

        return RawExperiment(text=text, sections=sections)

    def _parse_experiment_section(
        self, text: str, kind: Literal["observation", "experiment", "test", "none"]
    ) -> RawExperimentSection | None:
        markdown_blocks = extract_markdown_code_blocks(text)
        code_langs = self.problem.allowed_languages()
        dbg_langs = self.problem.allowed_debugger_languages()

        code_blocks = [block.code for block in markdown_blocks if (block.language or "") in code_langs]
        debugger_blocks = [block.code for block in markdown_blocks if (block.language or "") in dbg_langs]

        if code_blocks or (kind != "none"):
            return RawExperimentSection(kind=kind, text=text, code_blocks=code_blocks, debugger_blocks=debugger_blocks)
        else:
            return None


class InvalidStateException(Exception):
    def __init__(self, state: State | None, message: str | None = None):
        self.state = state
        if message:
            super().__init__(message)
        else:
            super().__init__(f'Invalid loop state: {state.value if state else 'None'}')
