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

    endpoint = SafeguardLLMEndpoint(get_openai_endpoint())
    endpoint = ReplayLLMEndpoint.from_pickled_conversation(
        "file:///home/marvin/workspace/master-thesis-playground/chatlogs/loop/%5B2024-08-26 11:24:30%5D 3ad11d9f_bucketsort.pickle",
        endpoint,
    )
    endpoint.drop_messages(1)

    problem = QuixbugsProblem(problem_name)
    problem.validate()

    prompts = replace(default_prompts, debug_prompt=debug_prompt_alt_experiments_v2)

    loop = Loop(problem, endpoint=endpoint, prompts=prompts, enable_print=True, enable_log=True)
    loop.iterate()
    logger.info(f"Stopped with state {loop.get_state()}")


def get_openai_endpoint() -> OpenAIEndpoint:
    return OpenAIEndpoint(OpenAI(), "gpt-4o-mini")
