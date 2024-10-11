from functools import partial
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from guut.baseline_loop import BaselineLoop, BaselineSettings
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


def experiment(*text):
    return f"## Experiment\n{"\n\n".join(text)}"


def _test(*text):
    return f"## Test\n{"\n\n".join(text)}"


Loop = partial(Loop, printer=None, logger=None, settings=LoopSettings())
Baseline = partial(BaselineLoop, printer=None, logger=None, settings=BaselineSettings())


def test__experiment_with_code_and_debugger_script_gets_detected():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment(code, debugger_script)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_RESULTS_GIVEN
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
        settings=LoopSettings(max_num_experiments=10, max_num_turns=99),
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


def test__conversation_is_aborted_if_a_test_beyond_the_max_is_submitted():
    conversation = Conversation(
        [
            UserMessage("", tag=State.INITIAL),
            *(
                [
                    AssistantMessage(_test(code), tag=State.TEST_STATED),
                    UserMessage("", tag=State.TEST_DOESNT_DETECT_MUTANT),
                ]
                * 2
            ),
        ]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages([_test(code)] * 2)

    problem = DummyProblem()
    problem.run_test = MagicMock(
        return_value=TestResult(
            correct=ExecutionResult(command=[], input="", cwd=Path("."), output="", target=Path("."), exitcode=0),
            mutant=ExecutionResult(command=[], input="", cwd=Path("."), output="", target=Path("."), exitcode=0),
        )
    )

    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
        settings=LoopSettings(max_num_tests=3),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED
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
                input="", command=[], cwd=Path("."), output="", target=Path("."), exitcode=correct_exit_code
            ),
            mutant=ExecutionResult(
                input="", command=[], cwd=Path("."), output="", target=Path("."), exitcode=mutant_exit_code
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
            correct=ExecutionResult(input="", command=[], cwd=Path("."), output="", target=Path("."), exitcode=0),
            mutant=ExecutionResult(input="", command=[], cwd=Path("."), output="", target=Path("."), exitcode=1),
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


@pytest.mark.parametrize(
    argnames=["section_name", "expected_state"],
    argvalues=[
        ("Experiment", State.EXPERIMENT_STATED),
        ("Test", State.TEST_STATED),
    ],
)
def test__subsections_get_combined(section_name, expected_state):
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [
            f"""
# {section_name}

bla bla bla

## {section_name} Code

{code}
"""
        ]
    )

    problem = DummyProblem()
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
    )

    loop.perform_next_step()
    assert loop.get_state() == expected_state


@pytest.mark.parametrize(
    argnames=["section_name", "expected_state"],
    argvalues=[
        ("Experiment", State.EXPERIMENT_STATED),
        ("Test", State.TEST_STATED),
    ],
)
def test__same_level_sections_get_combined(section_name, expected_state):
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [
            f"""
# {section_name}

bla bla bla

# {section_name} Code

{code}
"""
        ]
    )

    problem = DummyProblem()
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
    )

    loop.perform_next_step()
    assert loop.get_state() == expected_state


def test__mixed_subsections_dont_get_combined():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [
            f"""
# Test

bla bla bla

## Experiment

{code}
"""
        ]
    )

    problem = DummyProblem()
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
    )

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED


def test__bug_1():
    msg = """
To create a test that effectively distinguishes between the correct implementation and the mutant, we will take advantage of the modified `forward_exceed` condition in the mutant code. This change may allow an invalid configuration to circumvent normal validation checks.

Given the prior insights, we can focus on the case where `step` is zero, which should typically raise a `ValueError` in the original code but may produce a different behavior in the mutant.

### Mutant-Killing Test Code
We will target a scenario involving `roman_range` with specific inputs likely to expose the mutant's behavior while continuing to ensure that both implementations maintain expected functionality.

```python
from string_utils.generation import roman_range

def test_roman_range_mutant_kill():
    # Test for a zero step, which should raise a ValueError in the correct implementation
    try:
        result = list(roman_range(10, 1, 0))  # This should raise ValueError for both
        assert False, "Expected ValueError for zero step was not raised."
        except ValueError as e:
        assert str(e) == '"step" must be an integer in the range 1-3999', "Unexpected error message."

    # Test with backward generation where normally it should cause OverflowError
    try:
        result = list(roman_range(10, 1, -1))  # This is expected to raise an OverflowError
        assert False, "Expected OverflowError for backward generation was not raised."
        except OverflowError:
        pass  # This is expected in the original code

    # Valid forward case
    result = list(roman_range(5, 1, 1))  # Should yield I, II, III, IV, V
    assert result == ['I', 'II', 'III', 'IV', 'V'], "Forward range case failed."

test_roman_range_mutant_kill()
```

### Objective of the Test
1. **Zero Step Validation**: Ensure that the mutant cannot handle zero steps correctly and raises a `ValueError` with the appropriate message. This test should fail if the mutant's logic unwittingly allows this situation to pass.
2. **Overflow Handling**: Confirm that the correct implementation raises an `OverflowError` for appropriately invalid configurations while asserting mid-experiment that the mutant cannot maintain this check.
3. **Standard Functionality**: Finally, ensure standard sorted functionality across valid cases remains aligned with expected outputs, assuring no changes in desired outcomes under the stipulated scenarios of correctness.

This structured approach should effectively kill the mutant by leveraging previously established observations regarding the impact of adjustments made to the function's logic in handling these various edge cases.
        """

    conversation = Conversation(
        [UserMessage("", tag=State.INITIAL), UserMessage("", tag=State.TEST_INSTRUCTIONS_GIVEN)]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages([msg])

    problem = DummyProblem()
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED
    loop.perform_next_step()  # This used to cause an exception, because the was parsed as an experiment.


def test__experiment_after_equivalence():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [
            f"""
# Equivalent Mutant

bla bla bla

# Experiment

{code}
"""
        ]
    )

    problem = DummyProblem()
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
    )

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    result = loop.get_result()
    assert result.claimed_equivalent


@pytest.mark.parametrize(argnames=["LoopCls"], argvalues=[(Loop,), (Baseline,)])
def test__test_after_equivalence(LoopCls):
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [
            f"""
# Equivalent Mutant

bla bla bla

# Test

{code}
"""
        ]
    )

    problem = DummyProblem()
    loop = LoopCls(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED
    result = loop.get_result()
    assert result.claimed_equivalent


@pytest.mark.parametrize(argnames=["LoopCls"], argvalues=[(Loop,), (Baseline,)])
def test__equivalence_message(LoopCls):
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [
            """
# Equivalent Mutant

bla bla bla
"""
        ]
    )

    problem = DummyProblem()
    loop = LoopCls(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
    )

    loop.perform_next_step()
    assert loop.get_state() == State.CLAIMED_EQUIVALENT
    result = loop.get_result()
    assert result.claimed_equivalent


def test__max_num_turns_after_experiment():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [*([experiment(code)] * 3), *([_test(code)] * 3), *([experiment(code)] * 3), experiment(code)]
    )

    problem = DummyProblem()
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=problem, settings=LoopSettings(max_num_turns=10))

    for _ in range(19):
        loop.perform_next_step()
    loop.perform_next_step()
    assert loop.get_state() == State.ABORTED


def test__max_num_turns_after_test():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [*([experiment(code)] * 3), *([_test(code)] * 3), *([experiment(code)] * 3), _test(code)]
    )

    problem = DummyProblem()
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=problem, settings=LoopSettings(max_num_turns=10))

    for _ in range(19):
        loop.perform_next_step()
    loop.perform_next_step()
    assert loop.get_state() == State.ABORTED


def test__test_instructions_given_after_turn_reached_with_experiment():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([*([experiment(code)] * 3)])

    problem = DummyProblem()
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
        settings=LoopSettings(max_num_turns=4, test_inctructions_after_turn=3),
    )

    for _ in range(6):
        loop.perform_next_step()
    assert loop.get_state() == State.TEST_INSTRUCTIONS_GIVEN


@pytest.mark.parametrize(argnames=["LoopCls"], argvalues=[(Loop,), (Baseline,)])
def test__test_instructions_given_after_turn_reached_with_test(LoopCls):
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([*([_test(code)] * 3)])

    problem = DummyProblem()
    loop = LoopCls(
        endpoint=endpoint,
        conversation=conversation,
        problem=problem,
        settings=LoopSettings(max_num_turns=4, test_inctructions_after_turn=3),
    )

    for _ in range(6):
        loop.perform_next_step()
    print(loop.conversation)
    assert loop.get_state() == State.TEST_INSTRUCTIONS_GIVEN
