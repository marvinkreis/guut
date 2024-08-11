from enum import Enum
from itertools import takewhile
from typing import List

from loguru import logger

from guut.formatting import extract_code_block, format_execution_results
from guut.llm import Conversation, LLMEndpoint, Message, Role, UserMessage
from guut.problem import Problem
from guut.prompts import stop_words


# TODO: repair states
class State(str, Enum):
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
    def __init__(self, problem: Problem, endpoint: LLMEndpoint, conversation: Conversation):
        self.problem = problem
        self.conversation = conversation
        self.llm = endpoint

    def perform_next_step(self):
        state = self.get_state()
        logger.info(state)

        if state == State.INITIAL:
            self._prompt_llm_for_hypothesis()
        elif state == State.EXPERIMENT_STATED:
            self._run_experiment()
        elif state == State.EXPERIMENT_RESULTS_GIVEN:
            self._prompt_llm_for_conclusion_and_hypothesis()
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

    def get_state(self) -> State:
        if self.conversation and self.conversation[-1].tag and isinstance(self.conversation[-1].tag, State):
            return self.conversation[-1].tag
        return State.INVALID

    def set_state(self, state: State) -> None:
        self.conversation[-1].tag = state

    def get_last_messages(self, states: List[State] | None = None, roles: List[Role] | None = None) -> List[Message]:
        states = states or []
        roles = roles or []

        def condition(message: Message):
            return any(message.tag == state for state in states) and any(message.role == role for role in roles)

        return list(takewhile(condition, reversed(self.conversation)))

    def _prompt_llm_for_hypothesis(self):
        response = self.llm.complete(self.conversation, stop=stop_words)

        test_code = extract_code_block(response.content, "python")

        if (not test_code) or ("Experiment:" not in response.content):
            if self.get_state() != State.BETWEEN:
                response.tag = State.BETWEEN
            else:
                response.tag = State.INVALID
            self.conversation.append(response)
            return

        response.tag = State.EXPERIMENT_STATED
        self.conversation.append(response)
        return

    def _run_experiment(self):
        relevant_messages = self.get_last_messages(
            states=[State.EXPERIMENT_STATED, State.BETWEEN], roles=[Role.ASSISTANT]
        )
        relevant_text = "\n".join(msg.content for msg in relevant_messages)

        test_code = extract_code_block(relevant_text, "python")
        debugger_script = extract_code_block(relevant_text, "pdb")

        # TODO: validate the python code

        test_results_correct = self.problem.run_test(test_code, use_mutant=False)
        test_results_buggy = self.problem.run_test(test_code, use_mutant=True)

        # TODO: Lead the response with "Experiment Results"

        if debugger_script:
            debugger_results_correct = self.problem.run_debugger(test_code, debugger_script.strip(), use_mutant=False)
            debugger_results_buggy = self.problem.run_debugger(test_code, debugger_script.strip(), use_mutant=True)
            new_text = format_execution_results(
                test_results_correct, test_results_buggy, debugger_results_correct, debugger_results_buggy
            )
        else:
            new_text = format_execution_results(test_results_correct, test_results_buggy)

        new_message = UserMessage(content=new_text)
        new_message.tag = State.EXPERIMENT_RESULTS_GIVEN
        self.conversation.append(new_message)

    def _prompt_llm_for_conclusion_and_hypothesis(self):
        response = self.llm.complete(self.conversation, stop=stop_words)

        if "<DEBUGGING_DONE>" in response.content:
            response.tag = State.FINISHED_DEBUGGING
            self.conversation.append(response)
            return

        test_code = extract_code_block(response.content, "python")

        if (not test_code) or ("Experiment:" not in response.content):
            if self.get_state() != State.BETWEEN:
                response.tag = State.BETWEEN
            else:
                response.tag = State.INVALID
            self.conversation.append(response)
            return

        response.tag = State.EXPERIMENT_STATED
        self.conversation.append(response)
        return

    def _add_test_prompt(self):
        prompt = f"""Perfect. Now please write the bug-detecting test using the following template:
```python
from {self.problem.name} import {self.problem.name}

def test_{self.problem.name}():
    # your code here
```
Make sure to include the backticks and language name.
"""
        message = UserMessage(prompt)
        message.tag = State.TEST_INSTRUCTIONS_GIVEN
        self.conversation.append(message)
        return

    def _prompt_llm_for_test(self):
        response = self.llm.complete(self.conversation, stop=stop_words)

        test_block = extract_code_block(response.content, "python")
        if test_block:
            response.tag = State.DONE
        else:
            # TODO
            response.tag = State.BETWEEN

        self.conversation.append(response)

    def _prompt_llm_for_between(self):
        pass


class InvalidStateException(Exception):
    def __init__(self, state: State | None):
        self.state = state
        super().__init__(f'Invalid loop state: {state.value if state else 'None'}')
