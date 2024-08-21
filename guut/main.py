import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.environ["DOTENV_PATH"])


from loguru import logger
from openai import OpenAI

from guut.llm_endpoints.openai_endpoint import OpenAIEndpoint
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.llm_endpoints.safeguard_endpoint import SafeguardLLMEndpoint
from guut.loop import Loop
from guut.prompts import default_prompts
from guut.quixbugs import QuixbugsProblem


def main():
    endpoint = ReplayLLMEndpoint.from_raw_messages(
        [
            """Experiment:
```python
print("something")
```

```pdb
p "something from debugger"
```""",
            """Experiment:
```python
assert 1 == 2
```""",
            """<DEBUGGING_DONE>""",
            """```python
from sieve import sieve

assert len(sieve(10)) > 0
```""",
        ]
    )
    # endpoint = SafeguardLLMEndpoint(get_openai_endpoint())
    problem = QuixbugsProblem("sieve")
    problem.validate()

    loop = Loop(problem, endpoint=endpoint, prompts=default_prompts, enable_print=True, enable_log=False)
    loop.iterate()
    logger.info(f"Stopped with state {loop.get_state()}")


def get_openai_endpoint() -> OpenAIEndpoint:
    return OpenAIEndpoint(OpenAI(), "gpt-4o-mini")
