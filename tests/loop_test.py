from functools import partial
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from guut.dummy_problem import DummyProblem
from guut.llm import AssistantMessage, Conversation, UserMessage
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.loop import Loop, LoopSettings, State
from guut.problem import ExecutionResult, TestResult, ValidationResult

code_raw = """def test_something():
    print("something")"""

debugger_script_raw = """p "something"
c"""

code = f"""```python
{code_raw}
```"""

debugger_script = f"""```pdb
{debugger_script_raw}
```"""


def observation(*text):
    return f"## Observation\n{"\n\n".join(text)}"


def experiment(*text):
    return f"## Experiment\n{"\n\n".join(text)}"


def _test(*text):
    return f"## Test\n{"\n\n".join(text)}"


Loop = partial(Loop, printer=None, logger=None)


def test__observation_with_code_and_debugger_script_gets_detected():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([observation(code, debugger_script)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_RESULTS_GIVEN
    assert loop.experiments[0].kind == "observation"
    assert code_raw in loop.experiments[0].code
    assert loop.experiments[0].debugger_script is not None
    assert debugger_script_raw in loop.experiments[0].debugger_script


def test__observation_with_just_code_gets_detected():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([observation(code)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_RESULTS_GIVEN
    assert loop.experiments[0].kind == "observation"
    assert code_raw in loop.experiments[0].code
    assert loop.experiments[0].debugger_script is None


def test__observation_with_only_debugger_script_leads_to_incomple_response():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([observation(debugger_script)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.INCOMPLETE_RESPONSE


def test__experiment_with_code_and_debugger_script_gets_detected():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment(code, debugger_script)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_RESULTS_GIVEN
    assert loop.experiments[0].kind == "experiment"
    assert code_raw in loop.experiments[0].code
    assert loop.experiments[0].debugger_script is not None
    assert debugger_script_raw in loop.experiments[0].debugger_script


def test__experiment_with_just_code_gets_detected():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment(code)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_RESULTS_GIVEN
    assert loop.experiments[0].kind == "experiment"
    assert code_raw in loop.experiments[0].code
    assert loop.experiments[0].debugger_script is None


def test__experiment_with_only_debugger_script_leads_to_incomple_response():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment(debugger_script)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.INCOMPLETE_RESPONSE


def test__test_with_code_and_debugger_script_gets_detected_but_debugger_script_gets_discarded():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([_test(code, debugger_script)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.TEST_DOESNT_DETECT_MUTANT  # TODO: mock problem
    assert code_raw in loop.tests[0].code
    assert not hasattr(loop.tests[0], "debugger_script")


def test__test_with_just_code_gets_detected():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([_test(code)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.TEST_DOESNT_DETECT_MUTANT  # TODO: mock problem
    assert code_raw in loop.tests[0].code
    assert not hasattr(loop.tests[0], "debugger_script")


def test__test_with_only_debugger_script_leads_to_incomple_response():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([_test(debugger_script)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.INCOMPLETE_RESPONSE


def test__experiment_is_preferred_over_observation_when_first():
    conversation = Conversation(
        [
            AssistantMessage("", tag=State.INITIAL),
        ]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages([f"{experiment(code)}\n\n{observation(code)}\n\n{experiment(code)}"])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED


def test__test_is_preferred_over_experiment_if_no_header_is_present_and_test_instructions_werent_given_yet():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([f"{experiment(code)}\n\n{_test(code)}"])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED


def test__test_is_preferred_over_experiment_if_no_header_is_present_and_test_instructions_were_already_given():
    conversation = Conversation(
        [
            AssistantMessage("", tag=State.INITIAL),
            AssistantMessage("", tag=State.EXPERIMENT_STATED),
            AssistantMessage("", tag=State.EXPERIMENT_RESULTS_GIVEN),
            AssistantMessage("", tag=State.TEST_INSTRUCTIONS_GIVEN),
        ]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages([f"{experiment(code)}\n\n{_test(code)}"])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED


def test__code_is_interpreted_as_experiment_if_no_test_instructions_were_given():
    conversation = Conversation(
        [
            AssistantMessage("", tag=State.INITIAL),
        ]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages([f"{code}"])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED


def test__code_is_interpreted_as_test_if_test_instructions_were_given():
    conversation = Conversation(
        [
            AssistantMessage("", tag=State.INITIAL),
            AssistantMessage("", tag=State.EXPERIMENT_STATED),
            AssistantMessage("", tag=State.EXPERIMENT_RESULTS_GIVEN),
            AssistantMessage("", tag=State.TEST_INSTRUCTIONS_GIVEN),
        ]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages([f"{code}"])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED


def test__test_instructions_are_given_after_max_experiments_are_reached():
    conversation = Conversation(
        [
            AssistantMessage("", tag=State.INITIAL),
            UserMessage(experiment(code), tag=State.EXPERIMENT_STATED),
            UserMessage("", tag=State.EXPERIMENT_RESULTS_GIVEN),
        ]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment(code)])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
        settings=LoopSettings(max_num_experiments=2),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.TEST_INSTRUCTIONS_GIVEN


def test__conversation_is_aborted_if_an_experiment_beyond_the_max_is_submitted():
    conversation = Conversation(
        [
            AssistantMessage("", tag=State.INITIAL),
            UserMessage(experiment(code), tag=State.EXPERIMENT_STATED),
            UserMessage("", tag=State.EXPERIMENT_RESULTS_GIVEN),
            UserMessage(experiment(code), tag=State.EXPERIMENT_STATED),
            UserMessage("", tag=State.EXPERIMENT_RESULTS_GIVEN),
            UserMessage(experiment(code), tag=State.TEST_INSTRUCTIONS_GIVEN),
        ]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment(code)])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
        settings=LoopSettings(max_num_experiments=2),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.ABORTED


def test__test_instructions_are_given_after_max_experiments_are_reached_and_a_test_was_already_submitted():
    exp_msgs = [
        UserMessage(experiment(code), tag=State.EXPERIMENT_STATED),
        UserMessage("", tag=State.EXPERIMENT_RESULTS_GIVEN),
    ]

    conversation = Conversation(
        [
            AssistantMessage("", tag=State.INITIAL),
            *(exp_msgs * 4),
            UserMessage(experiment(code), tag=State.TEST_STATED),
            UserMessage("", tag=State.TEST_DOESNT_DETECT_MUTANT),
            *(exp_msgs * 4),
        ]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment(code)] * 2)
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
        settings=LoopSettings(max_num_experiments=10),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_RESULTS_GIVEN
    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.TEST_INSTRUCTIONS_GIVEN


def test__incomplete_response_instructions_are_given_after_incomplete_response():
    conversation = Conversation([AssistantMessage("", tag=State.INCOMPLETE_RESPONSE)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN


def test__conversation_is_continued_with_experiment_after_incomplete_response():
    conversation = Conversation([AssistantMessage("", tag=State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment(code)])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED


def test__conversation_is_continued_with_test_after_incomplete_response():
    conversation = Conversation([AssistantMessage("", tag=State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([_test(code)])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED


def test__conversation_is_aborted_if_an_incomplete_response_beyond_the_max_is_submitted():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment(debugger_script)] * 3)
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
        settings=LoopSettings(max_num_incomplete_responses=2),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.INCOMPLETE_RESPONSE
    loop.perform_next_step()
    assert loop.get_state() == State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN
    loop.perform_next_step()
    assert loop.get_state() == State.INCOMPLETE_RESPONSE
    loop.perform_next_step()
    assert loop.get_state() == State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN
    loop.perform_next_step()
    assert loop.get_state() == State.INCOMPLETE_RESPONSE
    loop.perform_next_step()
    assert loop.get_state() == State.ABORTED


def test__experiment_doesnt_compile():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment(code)])

    problem = DummyProblem()
    problem.validate_code = MagicMock(return_value=ValidationResult(valid=False, error=""))

    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
    )

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_DOESNT_COMPILE


def test__test_doesnt_compile():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([_test(code)])

    problem = DummyProblem()
    problem.validate_code = MagicMock(return_value=ValidationResult(valid=False, error=""))

    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.TEST_DOESNT_COMPILE


@pytest.mark.parametrize(argnames=["correct_exit_code", "mutant_exit_code"], argvalues=[(0, 0), (1, 1), (1, 0)])
def test__test_doesnt_detect_mutant(correct_exit_code, mutant_exit_code):
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([_test(code)])

    problem = DummyProblem()
    problem.run_test = MagicMock(
        return_value=TestResult(
            correct=ExecutionResult(
                input="", args=[], cwd=Path("."), output="", target=Path("."), exitcode=correct_exit_code
            ),
            mutant=ExecutionResult(
                input="", args=[], cwd=Path("."), output="", target=Path("."), exitcode=mutant_exit_code
            ),
        )
    )

    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.TEST_DOESNT_DETECT_MUTANT


def test__response_when_successful_test():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([_test(code)])

    problem = DummyProblem()
    problem.run_test = MagicMock(
        return_value=TestResult(
            correct=ExecutionResult(input="", args=[], cwd=Path("."), output="", target=Path("."), exitcode=0),
            mutant=ExecutionResult(input="", args=[], cwd=Path("."), output="", target=Path("."), exitcode=1),
        )
    )

    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.DONE
