import sys
from dataclasses import replace

from loguru import logger
from openai import OpenAI

from guut.llm import Conversation
from guut.llm_endpoints.openai_endpoint import OpenAIEndpoint
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.llm_endpoints.safeguard_endpoint import SafeguardLLMEndpoint
from guut.loop import Loop
from guut.prompts import default_prompts
from guut.quixbugs import QuixbugsProblem


def main():
    problem_name = sys.argv[1] if len(sys.argv) > 1 else "sieve"

    endpoint = SafeguardLLMEndpoint(get_openai_endpoint())

    if False:
        endpoint = ReplayLLMEndpoint.from_raw_messages(
            [
                """
# Test

Observation

```python
from sieve import sieve

def test_something():
    output = sieve(10)
    assert len(output) > 0, "sieve must output prime numbers"
```
""",
            ],
            select_messages=None,
        )

    if True:
        endpoint = ReplayLLMEndpoint.from_pickled_conversation(
            "file:///home/marvin/workspace/master-thesis-playground/chatlogs/loop/%5B2024-08-30 14:37:51%5D d7284074_to_base.pickle"
        )

    problem = QuixbugsProblem(problem_name)
    problem.validate()

    prompts = default_prompts
    conversation = None

    loop = Loop(
        problem, endpoint=endpoint, prompts=prompts, enable_print=True, enable_log=False, conversation=conversation
    )
    loop.iterate()
    logger.info(f"Stopped with state {loop.get_state()}")


def get_openai_endpoint() -> OpenAIEndpoint:
    return OpenAIEndpoint(OpenAI(), "gpt-4o-mini")
