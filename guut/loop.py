import re
from enum import Enum
from itertools import dropwhile
from random import randbytes
from typing import List, Literal

from loguru import logger

from guut.execution import TestResult
from guut.formatting import extract_code_blocks, pretty_message, remove_code_blocks
from guut.llm import AssistantMessage, Conversation, LLMEndpoint, Message
from guut.logging import LOG_BASE_PATH
from guut.logging import Logger as ConversationLogger
from guut.problem import Problem
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

        self.testcase: str | None = None
        self.test_result: TestResult | None = None

        self.conversation.name = "{}_{}".format("".join(f"{b:x}" for b in randbytes(4)), self.problem.name())
        self.conversation_logger = ConversationLogger(LOG_PATH, overwrite_old_logs=True)

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
        # elif state == State.FINISHED_DEBUGGING:
        #     self._add_test_prompt()
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
        elif self.conversation[-1].tag and isinstance(self.conversation[-1].tag, State):
            return self.conversation[-1].tag
        else:
            return State.INVALID

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

    def _concat_incomplete_responses(self, include_message: Message | None = None, include_state: State | None = None):
        all_relevant_messages = []
        included_state_found = False if include_state else True
        for msg in reversed(self.conversation):
            if msg.tag == State.INCOMPLETE_RESPONSE:
                all_relevant_messages = [msg] + all_relevant_messages
            elif msg.tag == State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN:
                continue
            elif not included_state_found and msg.tag == include_state:
                all_relevant_messages = [msg] + all_relevant_messages
                included_state_found = True

        if include_message:
            all_relevant_messages.append(include_message)

        relevant_text = "\n".join(msg.content for msg in all_relevant_messages)
        return relevant_text

    def _prompt_for_hypothesis_or_test(self):
        response = self.endpoint.complete(self.conversation, stop=self.prompts.debug_stop_words)
        self._remove_stop_word_residue(response)

        relevant_text = self._concat_incomplete_responses(include_message=response)
        relevant_markdown_text = remove_code_blocks(response.content)

        python_blocks = extract_code_blocks(relevant_text, "python")

        test_instructions_stated = any(msg.tag == State.TEST_INSTRUCTIONS_GIVEN for msg in self.conversation)

        found_experiment = False
        found_test = False
        found_observation = False
        for line in reversed(relevant_markdown_text.splitlines()):
            if re.match(TEST_HEADLINE_REGEX, line):
                found_test = True
            elif re.match(EXPERIMENT_HEADLINE_REGEX, line):
                found_experiment = True
            elif re.match(OBSERVATION_HEADLINE_REGEX, line):
                found_observation = True

        if not python_blocks:
            self.add_msg(response, State.INCOMPLETE_RESPONSE)
            return

        if found_test:
            self.add_msg(response, State.TEST_STATED)
            return
        elif found_experiment:
            self.add_msg(response, State.EXPERIMENT_STATED)
            return
        elif found_observation:
            self.add_msg(response, State.EXPERIMENT_STATED)
            return
        elif test_instructions_stated:
            self.add_msg(response, State.TEST_STATED)
            return
        elif not test_instructions_stated:
            self.add_msg(response, State.EXPERIMENT_STATED)
            return
        else:
            self.add_msg(response, State.INCOMPLETE_RESPONSE)
            return

    def _run_experiment(self):
        relevant_text = self._concat_incomplete_responses(include_state=State.EXPERIMENT_STATED)

        python_blocks = extract_code_blocks(relevant_text, "python")
        if not python_blocks:
            raise InvalidStateException(
                State.EXPERIMENT_STATED, f"No code present but state is {State.EXPERIMENT_STATED.value}."
            )
        debugger_blocks = extract_code_blocks(relevant_text, "pdb") + extract_code_blocks(relevant_text, "debugger")

        experiment_code = python_blocks[-1]
        validation_result = self.problem.validate_code(experiment_code)
        if not validation_result.valid:
            new_message = self.prompts.experiment_doesnt_compile_template.render(result=validation_result)
            self.add_msg(new_message, State.EXPERIMENT_DOESNT_COMPILE)
        else:
            relevant_text = self._concat_incomplete_responses(include_state=State.EXPERIMENT_STATED)
            relevant_markdown_text = remove_code_blocks(relevant_text)

            found_experiment = False
            found_observation = False
            for line in reversed(relevant_markdown_text.splitlines()):
                if re.match(EXPERIMENT_HEADLINE_REGEX, line):
                    found_experiment = True
                elif re.match(OBSERVATION_HEADLINE_REGEX, line):
                    found_observation = True

            debugger_code = debugger_blocks[-1] if debugger_blocks else None
            experiment_result = self.problem.run_experiment(experiment_code, debugger_code)
            new_message = self.prompts.experiment_results_template.render(
                result=experiment_result, is_observaion=(found_observation and not found_experiment)
            )
            self.add_msg(new_message, State.EXPERIMENT_RESULTS_GIVEN)

        num_experiments = len([msg for msg in self.conversation if msg.tag == State.EXPERIMENT_STATED])
        if num_experiments == self.max_num_experiments:
            new_message = self.prompts.test_prompt.render(max_iterations=True)
            self.add_msg(new_message, State.TEST_INSTRUCTIONS_GIVEN)
        elif num_experiments > self.max_num_experiments:
            new_message = self.prompts.conversation_aborted_template.render(
                reason="too_many_experiments", extra_reason="The LLM exceeded the allowed number of tests."
            )
            self.add_msg(new_message, State.ABORTED)

    def _add_test_prompt(self):
        new_message = self.prompts.test_prompt.render(max_iterations=False)
        self.add_msg(new_message, State.TEST_INSTRUCTIONS_GIVEN)

    def _run_test(self):
        relevant_text = self._concat_incomplete_responses(include_state=State.EXPERIMENT_STATED)

        python_blocks = extract_code_blocks(relevant_text, "python")
        if not python_blocks:
            raise InvalidStateException(State.TEST_STATED, f"No code present but state is {State.TEST_STATED.value}.")

        test_code = python_blocks[-1]
        validation_result = self.problem.validate_code(test_code)
        if not validation_result.valid:
            new_message = self.prompts.test_doesnt_compile_template.render(
                result=validation_result,
            )
            self.add_msg(new_message, State.TEST_DOESNT_COMPILE)
        else:
            result = self.problem.run_test(test_code)

            self.testcase = test_code
            self.test_result = result

            if result.correct.exitcode == 0 and result.mutant.exitcode != 0:
                new_message = self.prompts.results_template.render(test=test_code, result=result)
                self.add_msg(new_message, State.DONE)
            else:
                new_message = self.prompts.test_doesnt_detect_mutant_template.render(result=result)
                self.add_msg(new_message, State.TEST_DOESNT_DETECT_MUTANT)

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

    def _remove_stop_word_residue(self, msg: AssistantMessage):
        lines = msg.content.splitlines()

        def condition(line: str):
            if not line:
                return True
            if not line.strip():
                return True
            if all([c == "#" for c in line.strip()]):
                return True
            return False

        lines = reversed(list(dropwhile(condition, reversed(lines))))
        return AssistantMessage(content="\n".join(lines), response=msg.response, usage=msg.usage)

    def _print_and_log_conversation(self):
        if self.enable_print:
            for msg in self.new_messages:
                print(pretty_message(msg))
            self.new_messages = []
        if self.enable_log:
            self.conversation_logger.log_conversation(self.conversation, name=self.conversation.name or "")


class InvalidStateException(Exception):
    def __init__(self, state: State | None, message: str | None = None):
        self.state = state
        if message:
            super().__init__(message)
        else:
            super().__init__(f'Invalid loop state: {state.value if state else 'None'}')
