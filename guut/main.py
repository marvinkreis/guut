import sys
from dataclasses import replace

from loguru import logger
from openai import OpenAI

from guut.llm_endpoints.openai_endpoint import OpenAIEndpoint
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.llm_endpoints.safeguard_endpoint import SafeguardLLMEndpoint
from guut.loop import Loop
from guut.prompts import debug_prompt_alt_experiments_v2, default_prompts
from guut.quixbugs import QuixbugsProblem


def main():
    problem_name = sys.argv[1] if len(sys.argv) > 1 else "sieve"

    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [
            """Experiment:
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
p f"without mutant: primes={primes}, n={n}"
c
b mutant/sieve.py:5
commands
p f"with mutant: primes={primes}, n={n}"
c
c
```
"""
        ]
    )
    endpoint = SafeguardLLMEndpoint(get_openai_endpoint())
    problem = QuixbugsProblem(problem_name)
    problem.validate()

    prompts = replace(default_prompts, debug_prompt=debug_prompt_alt_experiments_v2)

    loop = Loop(problem, endpoint=endpoint, prompts=prompts, enable_print=True, enable_log=True)
    loop.iterate()
    logger.info(f"Stopped with state {loop.get_state()}")


def get_openai_endpoint() -> OpenAIEndpoint:
    return OpenAIEndpoint(OpenAI(), "gpt-4o-mini")
