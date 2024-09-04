from functools import partial

from guut.dummy_problem import DummyProblem
from guut.llm import AssistantMessage, Conversation, UserMessage
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.loop import Loop, LoopSettings, State

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


Loop = partial(Loop, enable_print=False, enable_log=False)


def test__observation_with_code_and_debugger_script_gets_detected():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([observation(code, debugger_script)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_RESULTS_GIVEN
    assert loop.experiments[0].description.kind == "observation"
    assert code_raw in loop.experiments[0].description.code
    assert loop.experiments[0].description.debugger_script is not None
    assert debugger_script_raw in loop.experiments[0].description.debugger_script


def test__observation_with_just_code_gets_detected():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([observation(code)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED
    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_RESULTS_GIVEN
    assert loop.experiments[0].description.kind == "observation"


def test__observation_with_only_debugger_script_leads_to_incomple_response():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([observation(debugger_script)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.INCOMPLETE_RESPONSE
    loop.perform_next_step()
    assert loop.get_state() == State.INCOMPLETE_RESPONSE_INSTRUCTIONS_GIVEN


def test__single_experiment_gets_detected():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([experiment(code)])
    loop = Loop(endpoint=endpoint, conversation=conversation, problem=DummyProblem())

    loop.perform_next_step()
    assert loop.get_state() == State.EXPERIMENT_STATED


def test__single_test_gets_deteted():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([_test(code)])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
    )

    loop.perform_next_step()
    assert loop.get_state() == State.TEST_STATED


def test__test_is_preferred_over_experiment_if_no_test_instructions_were_given():
    conversation = Conversation([AssistantMessage("", tag=State.INITIAL)])
    endpoint = ReplayLLMEndpoint.from_raw_messages([f"{experiment(code)}\n\n{_test(code)}"])
    loop = Loop(
        endpoint=endpoint,
        conversation=conversation,
        problem=DummyProblem(),
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


# TODO: incomplete responses and max

# ==============================================================================================
