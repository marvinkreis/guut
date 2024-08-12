from dotenv import load_dotenv

from guut.llm_endpoints.replay_endpoint import ReplayLLMEndpoint

load_dotenv()

import os

from llama_cpp import Llama
from loguru import logger
from openai import OpenAI

from guut.formatting import format_task
from guut.llm import Conversation
from guut.llm_endpoints.llamacpp_endpoint import LlamacppEndpoint
from guut.llm_endpoints.logging_endpoint import LoggingLLMEndpoint
from guut.llm_endpoints.openai_endpoint import OpenAIEndpoint
from guut.llm_endpoints.safeguard_endpoint import SafeguardLLMEndpoint
from guut.loop import Loop, State
from guut.prompts import LongInstructions3, SystemInstructions
from guut.quixbugs import QuixbugsProblem


def main():
    endpoint = LoggingLLMEndpoint(SafeguardLLMEndpoint(get_openai_endpoint()))
    # endpoint = SafeguardLLMEndpoint(get_llama_endpoint())
    # endpoint = MockLLMEndpoint()
    # endpoint = LoggingLLMEndpoint(
    #     ReplayLLMEndpoint(
    #         "/home/marvin/workspace/master-thesis-playground/logs/2024-08-12 11:28:20.180534 after_completion.pickle"
    #     )
    # )

    problem = QuixbugsProblem("sieve")
    problem.validate()

    conversation = Conversation([SystemInstructions().message(), LongInstructions3().message(format_task(problem))])

    loop = Loop(problem, endpoint=endpoint, conversation=conversation)
    loop.set_state(State.INITIAL)

    while loop.get_state() not in [State.DONE, State.BETWEEN, State.INVALID]:
        loop.perform_next_step()
    else:
        logger.info(f"Stopped with state {loop.get_state()}")


def get_llama_endpoint() -> LlamacppEndpoint:
    llama_path = os.environ["LLAMA_PATH"]
    client = Llama(model_path=llama_path)
    return LlamacppEndpoint(client)


def get_openai_endpoint() -> OpenAIEndpoint:
    client = OpenAI()
    return OpenAIEndpoint(client, "gpt-4o-mini")
