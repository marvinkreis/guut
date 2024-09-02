from guut.dummy_problem import DummyProblem
from guut.llm import AssistantMessage, Conversation, UserMessage
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.loop import Loop, LoopSettings, State
from guut.prompts import default_prompts

code = """
```python
print("something")
```
"""

experiment = f"""
# Experiment

{code}
"""

test = f"""
# Test

{code}
"""


def test__single_experiment_gets_detected():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        prompts=default_prompts,
        problem=DummyProblem(),
        enable_print=False,
        enable_log=False,
        settings=LoopSettings(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED


def test__single_test_gets_deteted():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([test])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        prompts=default_prompts,
        problem=DummyProblem(),
        enable_print=False,
        enable_log=False,
        settings=LoopSettings(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED


def test__test_is_preferred_over_experiment_if_no_test_instructions_were_given():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([f"{experiment}\n\n{test}"])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        prompts=default_prompts,
        problem=DummyProblem(),
        enable_print=False,
        enable_log=False,
        settings=LoopSettings(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED


def test__test_is_preferred_over_experiment_if_test_instructions_were_given():
    conversation = Conversation(
        [
            AssistantMessage("", tag=State.INITIAL),
            AssistantMessage("", tag=State.EXPERIMENT_STATED),
            AssistantMessage("", tag=State.EXPERIMENT_RESULTS_GIVEN),
            AssistantMessage("", tag=State.TEST_INSTRUCTIONS_GIVEN),
        ]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages([f"{experiment}\n\n{test}"])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        prompts=default_prompts,
        problem=DummyProblem(),
        enable_print=False,
        enable_log=False,
        settings=LoopSettings(),
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
        prompts=default_prompts,
        problem=DummyProblem(),
        enable_print=False,
        enable_log=False,
        settings=LoopSettings(),
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
        prompts=default_prompts,
        problem=DummyProblem(),
        enable_print=False,
        enable_log=False,
        settings=LoopSettings(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED


def test__test_instructions_are_given_after_max_experiments_are_reached():
    conversation = Conversation(
        [
            AssistantMessage("", tag=State.INITIAL),
            UserMessage(experiment, tag=State.EXPERIMENT_STATED),
            UserMessage("", tag=State.EXPERIMENT_RESULTS_GIVEN),
        ]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        prompts=default_prompts,
        problem=DummyProblem(),
        enable_print=False,
        enable_log=False,
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
            UserMessage(experiment, tag=State.EXPERIMENT_STATED),
            UserMessage("", tag=State.EXPERIMENT_RESULTS_GIVEN),
            UserMessage(experiment, tag=State.EXPERIMENT_STATED),
            UserMessage("", tag=State.EXPERIMENT_RESULTS_GIVEN),
            UserMessage(experiment, tag=State.TEST_INSTRUCTIONS_GIVEN),
        ]
    )
    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [
            """
# Experiment

```python
print("something")
```
"""
        ]
    )
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        prompts=default_prompts,
        problem=DummyProblem(),
        enable_print=False,
        enable_log=False,
        settings=LoopSettings(max_num_experiments=2),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.ABORTED


# TODO: incomplete responses and max
