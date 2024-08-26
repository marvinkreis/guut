import sys
from dataclasses import replace

from loguru import logger
from openai import OpenAI

from guut.llm import Conversation
from guut.llm_endpoints.openai_endpoint import OpenAIEndpoint
from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint
from guut.llm_endpoints.safeguard_endpoint import SafeguardLLMEndpoint
from guut.loop import Loop
from guut.prompts import debug_prompt_alt_experiments_v2, default_prompts
from guut.quixbugs import QuixbugsProblem


def main():
    problem_name = sys.argv[1] if len(sys.argv) > 1 else "sieve"

    openai_endpoint = SafeguardLLMEndpoint(get_openai_endpoint())
    replay_endpoint = ReplayLLMEndpoint.from_pickled_conversation(
        "",
        select_messages=2,
    )

    endpoint = replay_endpoint

    problem = QuixbugsProblem(problem_name)
    problem.validate()

    prompts = replace(default_prompts, debug_prompt=debug_prompt_alt_experiments_v2)

    conversation = None

    loop = Loop(
        problem, endpoint=endpoint, prompts=prompts, enable_print=True, enable_log=True, conversation=conversation
    )
    loop.iterate()
    logger.info(f"Stopped with state {loop.get_state()}")


def get_openai_endpoint() -> OpenAIEndpoint:
    return OpenAIEndpoint(OpenAI(), "gpt-4o-mini")
