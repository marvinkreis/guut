from enum import Enum
from itertools import takewhile
from random import randbytes
from typing import List

from loguru import logger

from guut.formatting import extract_code_block, pretty_message
from guut.llm import Conversation, LLMEndpoint, Message, Role
from guut.logging import LOG_BASE_PATH, Logger
from guut.problem import Problem
from guut.prompts import PromptCollection, test_prompt

LOG_PATH = LOG_BASE_PATH / "loop"
LOG_PATH.mkdir(parents=True, exist_ok=True)


class State(str, Enum):
    # The conversation is empty
    EMPTY = "empty"

    # The prompt as well as the problem description have been stated.
    INITIAL = "initial"

    # The LLM has stated an experiment and is waiting for the results.
    EXPERIMENT_STATED = "experiment_stated"

    # The execution result was given to the LLM.
    EXPERIMENT_RESULTS_GIVEN = "experiment_results_given"

    # The LLM has finished debugging and is ready to write the test.
    FINISHED_DEBUGGING = "finished_debugging"

    # Instructions for writing the unit test have been stated.
    TEST_INSTRUCTIONS_GIVEN = "test_instructions_given"

    # The LLM has finished writing the test.
    DONE = "done"

    # The LLM finished between two steps.
    BETWEEN = "between"

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
    ):
        self.problem = problem
        self.endpoint = endpoint
        self.prompts = prompts
        self.log = log
        self.print = print
        self.new_messages: List[Message] = []

        self.testcase = None
        self.testcase_result = None

        if conversation is None:
            self.conversation = Conversation()

        self.conversation.name = "{}_{}".format("".join(f"{b:x}" for b in randbytes(4)), self.problem.name())
        self.logger = Logger(LOG_PATH, overwrite_old_logs=True)

    def perform_next_step(self):
        state = self.get_state()
        logger.info(state)

        if state == State.EMPTY:
            self._init_conversation()
        elif state == State.INITIAL:
            self._prompt_for_hypothesis()
        elif state == State.EXPERIMENT_STATED:
            self._run_experiment()
        elif state == State.EXPERIMENT_RESULTS_GIVEN:
            self._prompt_for_hypothesis()
        elif state == State.FINISHED_DEBUGGING:
            self._add_test_prompt()
        elif state == State.TEST_INSTRUCTIONS_GIVEN:
            self._prompt_llm_for_test()
        elif state == State.DONE:
            logger.warning("perform_next_step called with conversation in completed state.")
        elif state == State.BETWEEN:
            self._prompt_llm_for_between()
        elif state == State.INVALID:
            raise InvalidStateException(State.INVALID)
        elif state is None:
            raise InvalidStateException(None)

        if self.print:
            for msg in self.new_messages:
                print(pretty_message(msg))
            self.new_messages = []

        if self.log:
            self.logger.log_conversation(self.conversation, name=self.conversation.name or "")

    def iterate(self):
        # TODO: handle between
        while self.get_state() not in [State.DONE, State.BETWEEN, State.INVALID]:
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

    def get_last_messages(self, states: List[State] | None = None, roles: List[Role] | None = None) -> List[Message]:
        states = states or []
        roles = roles or []

        def condition(message: Message):
            return any(message.tag == state for state in states) and any(message.role == role for role in roles)

        return list(takewhile(condition, reversed(self.conversation)))

    def _init_conversation(self):
        """it's hard to so sometimes"""
        self.conversation = Conversation()
        if self.prompts.system_prompt:
            self.add_msg(self.prompts.system_prompt.render(), State.BETWEEN)
        self.add_msg(self.prompts.debug_prompt.render(self.problem), State.BETWEEN)
        self.add_msg(self.prompts.problem_template.render(self.problem), State.INITIAL)

    def _prompt_for_hypothesis(self):
        response = self.endpoint.complete(self.conversation, stop=self.prompts.debug_prompt.stop_words)

        if "<DEBUGGING_DONE>" in response.content:
            self.add_msg(response, State.FINISHED_DEBUGGING)
            return

        test_code = extract_code_block(response.content, "python")

        if not test_code:
            if self.get_state() != State.BETWEEN:
                self.add_msg(response, State.BETWEEN)
            else:
                self.add_msg(response, State.INVALID)
            return

        self.add_msg(response, State.EXPERIMENT_STATED)

    def _run_experiment(self):
        relevant_messages = self.get_last_messages(
            states=[State.EXPERIMENT_STATED, State.BETWEEN], roles=[Role.ASSISTANT]
        )
        relevant_text = "\n".join(msg.content for msg in relevant_messages)

        test_code = extract_code_block(relevant_text, "python")
        debugger_script = extract_code_block(relevant_text, "pdb")

        # TODO: validate the python code

        experiment_result = self.problem.run_experiment(test_code, debugger_script)
        new_message = self.prompts.experiment_results_template.render(
            result=experiment_result,
        )
        self.add_msg(new_message, State.EXPERIMENT_RESULTS_GIVEN)

    def _add_test_prompt(self, max_iterations: bool = False):
        self.add_msg(test_prompt.render(max_iterations=max_iterations), State.TEST_INSTRUCTIONS_GIVEN)

    def _prompt_llm_for_test(self):
        response = self.endpoint.complete(self.conversation, stop=self.prompts.test_prompt.stop_words)

        test_block = extract_code_block(response.content, "python")
        if test_block:
            self.add_msg(response, State.DONE)
        else:
            # TODO
            self.add_msg(response, State.BETWEEN)

    def _prompt_llm_for_between(self):
        pass


class InvalidStateException(Exception):
    def __init__(self, state: State | None, message: str | None = None):
        self.state = state
        if message:
            super().__init__(message)
        else:
            super().__init__(f'Invalid loop state: {state.value if state else 'None'}')
