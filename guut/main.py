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
    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [
            """Experiment:
```python
from sieve import sieve
from mutant.sieve import sieve as mutant_sieve

print(f"correct: {sieve(10)}")
print(f"mutant: {mutant_sieve(10)}")
```

```pdb
b sieve.py:14
commands
p "ok"
c
b mutant/sieve.py:14
commands
p "ok"
c
c
```"""
        ]
    )
    endpoint = SafeguardLLMEndpoint(get_openai_endpoint())
    problem = QuixbugsProblem("kth")
    problem.validate()

    prompts = replace(default_prompts, debug_prompt=debug_prompt_alt_experiments_v2)

    loop = Loop(problem, endpoint=endpoint, prompts=prompts, enable_print=True, enable_log=True)
    loop.iterate()
    logger.info(f"Stopped with state {loop.get_state()}")


def get_openai_endpoint() -> OpenAIEndpoint:
    return OpenAIEndpoint(OpenAI(), "gpt-4o-mini")
