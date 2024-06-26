from enum import Enum
from itertools import takewhile
from typing import List

from loguru import logger

from guut.formatting import extract_code_block, format_execution_results
from guut.llm import Conversation, Role, Message, UserMessage, LLMEndpoint
from guut.quixbugs_helper import Problem, run_test_on_problem, run_debugger_on_problem


# TODO: repair states
class LoopState(Enum):
    # The instructions (and examples), as well as the problem description are given.
    PROBLEM_STATED = 'problem_stated'

    # The LLM has stated the experiment and is waiting for the results.
    EXPERIMENT_STATED = 'experiment_stated'

    # The execution result was given to the LLM.
    EXPERIMENT_RESULTS_GIVEN = 'experiment_results_given'

    # The LLM has finished debugging and is ready to write the test.
    FINISHED_DEBUGGING = 'finished_debugging'

    # The LLM has finished debugging and is ready to write the test.
    TEST_INSTRUCTIONS_GIVEN = 'test_instructions_given'

    # The LLM has finished writing the test.
    TEST_DONE = 'test_done'

    # The LLM finished inbetween two steps.
    BETWEEN = 'between'

    # The conversation is in an unrecoverable state.
    INVALID = 'invalid'


class Loop:
    def __init__(self, problem: Problem, endpoint: LLMEndpoint, conversation: Conversation):
        self.problem = problem
        self.conversation = conversation
        self.llm = endpoint

    def perform_next_step(self):
        logger.info(self.get_state())
        state = self.get_state()

        if state == LoopState.PROBLEM_STATED:
            self._prompt_llm_for_hypothesis()
        elif state == LoopState.EXPERIMENT_STATED:
            self._run_experiment()
        elif state == LoopState.EXPERIMENT_RESULTS_GIVEN:
            self._prompt_llm_for_conclusion_and_hypothesis()
        elif state == LoopState.FINISHED_DEBUGGING:
            self._add_test_prompt()
        elif state == LoopState.TEST_INSTRUCTIONS_GIVEN:
            self._prompt_llm_for_test()
        elif state == LoopState.TEST_DONE:
            logger.warning('perform_next_step called with conversation in completed state.')
        elif state == LoopState.BETWEEN:
            self._prompt_llm_for_between()
        elif state == LoopState.INVALID:
            logger.warning('perform_next_step called with conversation in invalid state.')
        elif state is None:
            logger.warning('perform_next_step called with conversation in None state.')

    def get_state(self) -> LoopState:
        if self.conversation and self.conversation[-1].tag and isinstance(self.conversation[-1].tag, LoopState):
            return self.conversation[-1].tag
        return LoopState.INVALID

    def set_state(self, state: LoopState) -> None:
        self.conversation[-1].tag = state

    def get_last_messages(self, states: List[LoopState] = None, roles: List[Role] = None) -> List[Message]:
        states = states or []
        roles = roles or []

        def condition(message: Message):
            return any(message.tag == state for state in states) and any(message.role == role for role in roles)

        return list(takewhile(condition, reversed(self.conversation)))

    def _prompt_llm_for_hypothesis(self):
        response = self.llm.complete(self.conversation, stop=['Experiment Results:', '<DEBUGGING_DONE>'])

        test_code = extract_code_block(response.content, 'python')

        if (not test_code) or ('Experiment:' not in response.content):
            if self.get_state() != LoopState.BETWEEN:
                response.tag = LoopState.BETWEEN
            else:
                response.tag = LoopState.INVALID
            self.conversation.append(response)
            return

        response.tag = LoopState.EXPERIMENT_STATED
        self.conversation.append(response)
        return

    def _run_experiment(self):
        relevant_messages = self.get_last_messages(
            states=[LoopState.EXPERIMENT_STATED, LoopState.BETWEEN], roles=[Role.ASSISTANT])
        relevant_text = '\n'.join(msg.content for msg in relevant_messages)

        test_code = extract_code_block(relevant_text, 'python')
        debugger_script = extract_code_block(relevant_text, 'debugger')
        if debugger_script:
            debugger_script = debugger_script.strip().splitlines()

        # TODO: validate the python code

        test_results_correct = run_test_on_problem(self.problem, test_code, buggy_version=False)
        test_results_buggy = run_test_on_problem(self.problem, test_code, buggy_version=True)

        # TODO: Lead the response with "Experiment Results"

        if debugger_script:
            debugger_results_correct = run_debugger_on_problem(self.problem, test_code, debugger_script, buggy_version=False)
            debugger_results_buggy = run_debugger_on_problem(self.problem, test_code, debugger_script, buggy_version=True)
            new_text = format_execution_results(test_results_correct, test_results_buggy,
                                                debugger_results_correct, debugger_results_buggy)
        else:
            new_text = format_execution_results(test_results_correct, test_results_buggy)

        new_message = UserMessage(content=new_text)
        new_message.tag = LoopState.EXPERIMENT_RESULTS_GIVEN
        self.conversation.append(new_message)

    def _prompt_llm_for_conclusion_and_hypothesis(self):
        response = self.llm.complete(self.conversation, stop=['Experiment Result', 'Experiment Results:', '<DEBUGGING_DONE>'])

        if '<DEBUGGING_DONE>' in response.content:
            response.tag = LoopState.FINISHED_DEBUGGING
            self.conversation.append(response)
            return

        test_code = extract_code_block(response.content, 'python')

        if (not test_code) or ('Experiment:' not in response.content):
            if self.get_state() != LoopState.BETWEEN:
                response.tag = LoopState.BETWEEN
            else:
                response.tag = LoopState.INVALID
            self.conversation.append(response)
            return

        response.tag = LoopState.EXPERIMENT_STATED
        self.conversation.append(response)
        return

    def _add_test_prompt(self):
        prompt = f'''Perfect. Now please write the bug-detecting test using the following template:
```python
from {self.problem.name} import {self.problem.name}

def test_{self.problem.name}():
    # your code here
```
Make sure to include the backticks and language name.
'''
        message = UserMessage(prompt)
        message.tag = LoopState.TEST_INSTRUCTIONS_GIVEN
        self.conversation.append(message)
        return

    def _prompt_llm_for_test(self):
        response = self.llm.complete(self.conversation, stop=['Experiment Result:', 'Experiment Results:', '<DEBUGGING_DONE>'])

        test_block = extract_code_block(response.content, 'python')
        if test_block:
            response.tag = LoopState.TEST_DONE
        else:
            # TODO
            response.tag = LoopState.BETWEEN

        self.conversation.append(response)

    def _prompt_llm_for_between(self):
        pass
