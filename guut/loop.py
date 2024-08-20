from enum import Enum
from itertools import takewhile
from random import randbytes
from typing import List

from loguru import logger

from guut.execution import TestResult
from guut.formatting import extract_code_block, pretty_message
from guut.llm import Conversation, LLMEndpoint, Message
from guut.logging import LOG_BASE_PATH, Logger
from guut.problem import Problem
from guut.prompts import PromptCollection

LOG_PATH = LOG_BASE_PATH / "loop"
LOG_PATH.mkdir(parents=True, exist_ok=True)


class State(str, Enum):
    # The conversation is empty
    EMPTY = "empty"

    # The prompt as well as the problem description have been stated.
    INITIAL = "initial"

    # The LLM has stated an experiment and is waiting for the results.
    EXPERIMENT_STATED = "experiment_stated"

    # The experiment does not compile.
    EXPERIMENT_INVALID = "experiment_invalid"

    # The execution result was given to the LLM.
    EXPERIMENT_RESULTS_GIVEN = "experiment_results_given"

    # The LLM has finished debugging and is ready to write the test.
    FINISHED_DEBUGGING = "finished_debugging"

    # Instructions for writing the unit test have been stated.
    TEST_INSTRUCTIONS_GIVEN = "test_instructions_given"

    # The LLM has stated a test.
    TEST_STATED = "test_stated"

    # The test does not compile or does not detect the mutant.
    TEST_INVALID = "test_invalid"

    # The LLM has finished writing the test.
    DONE = "done"

    # The LLM did not give a complete response.
    INCOMPLETE_RESPONSE = "incomplete_response"

    # The conversation is in an unknown or unrecoverable state.
    INVALID = "invalid"


class Loop:
    def __init__(
        self,
        problem: Problem,
        endpoint: LLMEndpoint,
        prompts: PromptCollection,
        conversation: Conversation | None = None,
        log: bool = True,
        print: bool = False,
        max_retries_for_invalid_test: int = 2,
        max_incomplete_responses: int = 2,
        max_num_experiments: int = 8,
    ):
        self.problem = problem
        self.endpoint = endpoint
        self.prompts = prompts
        self.log = log

        self.print = print
        self.new_messages: List[Message] = []

        self.max_retries_for_invalid_code = max_retries_for_invalid_test
        self.max_retries_for_incomplete_response = max_incomplete_responses
        self.max_num_experiments = max_num_experiments

        self.testcase = str | None
        self.test_result = TestResult | None

        if conversation is None:
            self.conversation = Conversation()

        self.conversation.name = "{}_{}".format("".join(f"{b:x}" for b in randbytes(4)), self.problem.name())
        self.logger = Logger(LOG_PATH, overwrite_old_logs=True)

    def perform_next_step(self):
        state = self.get_state()
        logger.info(state)

        self._perform_next_step(state)

        if self.print:
            for msg in self.new_messages:
                print(pretty_message(msg))
            self.new_messages = []

        if self.log:
            self.logger.log_conversation(self.conversation, name=self.conversation.name or "")

    def _perform_next_step(self, state: State):
        if state == State.EMPTY:
            self._init_conversation()
        elif state == State.INITIAL:
            self._prompt_for_hypothesis()
        elif state == State.EXPERIMENT_STATED:
            self._run_experiment()
        elif state == State.EXPERIMENT_RESULTS_GIVEN:
            self._prompt_for_hypothesis()
        elif state == State.EXPERIMENT_INVALID:
            self._prompt_for_hypothesis()
        elif state == State.FINISHED_DEBUGGING:
            self._add_test_prompt()
        elif state == State.TEST_INSTRUCTIONS_GIVEN:
            self._prompt_llm_for_test()
        elif state == State.TEST_STATED:
            self._run_test()
        elif state == State.TEST_INVALID:
            self._prompt_llm_for_test()
        elif state == State.DONE:
            logger.warning("perform_next_step called with conversation in completed state.")
        elif state == State.INCOMPLETE_RESPONSE:
            self._prompt_llm_for_incomplete_response()
        elif state == State.INVALID:
            raise InvalidStateException(State.INVALID)
        elif state is None:
            raise InvalidStateException(None)

    def iterate(self):
        while self.get_state() not in [State.DONE, State.INVALID, None]:
            self.perform_next_step()

    def get_state(self) -> State:
        if not self.conversation:
            return State.EMPTY
        elif self.conversation[-1].tag and isinstance(self.conversation[-1].tag, State):
            return self.conversation[-1].tag
        else:
            return State.INVALID

    def add_msg(self, msg: Message, tag: State | None = None):
        if tag:
            msg.tag = tag
        self.conversation.append(msg)
        self.new_messages.append(msg)

    def _init_conversation(self):
        """it's hard to so sometimes"""
        self.conversation = Conversation()
        if self.prompts.system_prompt:
            self.add_msg(self.prompts.system_prompt.render())
        self.add_msg(self.prompts.debug_prompt.render(self.problem))
        self.add_msg(self.prompts.problem_template.render(self.problem), State.INITIAL)

    def _prompt_for_hypothesis(self):
        response = self.endpoint.complete(self.conversation, stop=self.prompts.debug_stop_words)

        if "<DEBUGGING_DONE>" in response.content:
            self.add_msg(response, State.FINISHED_DEBUGGING)
            return

        test_code = extract_code_block(response.content, "python")

        if test_code:
            self.add_msg(response, State.EXPERIMENT_STATED)
        else:
            self.add_msg(response, State.INCOMPLETE_RESPONSE)

    def _run_experiment(self):
        relevant_messages = takewhile(
            lambda msg: msg.tag in [State.INCOMPLETE_RESPONSE, State.EXPERIMENT_STATED], reversed(self.conversation)
        )
        relevant_text = "\n".join(msg.content for msg in relevant_messages)

        test_code = extract_code_block(relevant_text, "python")
        if not test_code:
            raise InvalidStateException(
                State.EXPERIMENT_STATED, f"No code present but state is {State.EXPERIMENT_STATED.value}."
            )
        debugger_script = extract_code_block(relevant_text, "pdb")

        validation_result = self.problem.validate_code(test_code)
        if not validation_result.valid:
            new_message = self.prompts.experiment_doesnt_compile_template.render(
                result=validation_result,
            )
            self.add_msg(new_message, State.EXPERIMENT_INVALID)
            return

        experiment_result = self.problem.run_experiment(test_code, debugger_script)
        new_message = self.prompts.experiment_results_template.render(
            result=experiment_result,
        )
        self.add_msg(new_message, State.EXPERIMENT_RESULTS_GIVEN)

        num_experiments = len([msg for msg in self.conversation if msg.tag == State.EXPERIMENT_STATED])
        if num_experiments >= self.max_num_experiments:
            new_message = self.prompts.test_prompt.render(max_iterations=True)
            self.add_msg(new_message, State.TEST_INSTRUCTIONS_GIVEN)

    def _add_test_prompt(self):
        new_message = self.prompts.test_prompt.render(max_iterations=False)
        self.add_msg(new_message, State.TEST_INSTRUCTIONS_GIVEN)

    def _prompt_llm_for_test(self):
        response = self.endpoint.complete(self.conversation, stop=self.prompts.test_stop_words)

        test_code = extract_code_block(response.content, "python")
        if test_code:
            self.add_msg(response, State.TEST_STATED)
        else:
            self.add_msg(response, State.INCOMPLETE_RESPONSE)

    def _run_test(self):
        relevant_messages = takewhile(
            lambda msg: msg.tag in [State.INCOMPLETE_RESPONSE, State.TEST_STATED], reversed(self.conversation)
        )
        relevant_text = "\n".join(msg.content for msg in relevant_messages)

        test_code = extract_code_block(relevant_text, "python")
        if not test_code:
            raise InvalidStateException(State.TEST_STATED, f"No code present but state is {State.TEST_STATED.value}.")

        validation_result = self.problem.validate_code(test_code)
        if not validation_result.valid:
            new_message = self.prompts.test_doesnt_compile_template.render(
                result=validation_result,
            )
            self.add_msg(new_message, State.TEST_INVALID)
            return

        result = self.problem.run_test(test_code)
        if result.correct.exitcode == 0 and result.mutant.exitcode != 0:
            self.testcase = test_code
            self.test_result = result
            new_message = self.prompts.results_template.render(test=test_code, result=result)
            self.add_msg(new_message, State.DONE)
            return

        new_message = self.prompts.test_doesnt_detect_mutant_template.render(result=result)
        num_tries = len([msg for msg in self.conversation if msg.tag == State.TEST_INVALID])

        if num_tries < self.max_retries_for_invalid_code:
            self.add_msg(new_message, State.TEST_INVALID)
        else:
            self.add_msg(new_message, State.INVALID)

    def _prompt_llm_for_incomplete_response(self):
        num_tries = len([msg for msg in self.conversation if msg.tag == State.INCOMPLETE_RESPONSE])
        if num_tries > self.max_retries_for_incomplete_response:
            new_message = self.prompts.conversation_aborted_template.render(reason="incomplete_response")
            self.add_msg(new_message, State.INVALID)
            return

        msg_before = [msg for msg in self.conversation if msg.tag != State.INCOMPLETE_RESPONSE][-1]
        if isinstance(msg_before.tag, State):
            self._perform_next_step(msg_before.tag)
        else:
            raise InvalidStateException(None, f"No valid state before {State.INCOMPLETE_RESPONSE.value}.")


class InvalidStateException(Exception):
    def __init__(self, state: State | None, message: str | None = None):
        self.state = state
        if message:
            super().__init__(message)
        else:
            super().__init__(f'Invalid loop state: {state.value if state else 'None'}')
