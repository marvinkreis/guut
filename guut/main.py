import sys
from dataclasses import replace

from loguru import logger
from openai import OpenAI

from guut.llm import Conversation
from guut.llm_endpoints.openai_endpoint import OpenAIEndpoint
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.llm_endpoints.safeguard_endpoint import SafeguardLLMEndpoint
from guut.loop import Loop
from guut.prompts import debug_prompt_alt_experiments_v3, default_prompts
from guut.quixbugs import QuixbugsProblem


def main():
    problem_name = sys.argv[1] if len(sys.argv) > 1 else "sieve"

    endpoint = SafeguardLLMEndpoint(get_openai_endpoint())

    if False:
        endpoint = ReplayLLMEndpoint.from_raw_messages(
            [
                """
# Observation

```python
from sieve import sieve
from mutant.sieve import sieve as sieve_mutant

print(f"Correct output: {sieve(5)}")
print(f"Mutant output: {sieve_mutant(5)}")
```

```pdb
b sieve.py:5
commands
silent
print(f"without mutant: n={n}, primes={primes}")
c
b mutant/sieve.py:5
commands
silent
print(f"with mutant: n={n}, primes={primes}")
c
c
```
""",
                """
# Experiment

```python
from sieve import sieve
from mutant.sieve import sieve as sieve_mutant

output_correct = sieve(10)
output_mutant = sieve_mutant(10)

print(f"Correct output: {output_correct}")
print(f"Mutant output: {output_mutant}")
print(f"Verifying expression: {len(output_mutant) == 0 and len(output_correct) > 0}")
```

```pdb
b sieve.py:5
commands
print(f"without mutant: added {n} to {primes}")
silent
c
b mutant/sieve.py:5
commands
silent
print(f"with mutant: added {n} to {primes}. This should not print!")
c
c
```
""",
            ],
            select_messages=None,
        )

    if False:
        endpoint = ReplayLLMEndpoint.from_pickled_conversation(
            "file:///home/marvin/workspace/master-thesis-playground/chatlogs/loop/%5B2024-08-28 20:43:57%5D 51944bce_flatten.pickle"
        )

    problem = QuixbugsProblem(problem_name)
    problem.validate()

    prompts = replace(default_prompts, debug_prompt=debug_prompt_alt_experiments_v3)

    conversation = None

    loop = Loop(
        problem, endpoint=endpoint, prompts=prompts, enable_print=True, enable_log=True, conversation=conversation
    )
    loop.iterate()
    logger.info(f"Stopped with state {loop.get_state()}")


def get_openai_endpoint() -> OpenAIEndpoint:
    return OpenAIEndpoint(OpenAI(), "gpt-4o-mini")
