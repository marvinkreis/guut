import os

from llama_cpp import Llama
from openai import OpenAI

from guut.formatting import format_task
from guut.llm import Conversation, UserMessage
from guut.llm_endpoints.llamacpp_endpoint import LlamacppEndpoint
from guut.llm_endpoints.logging_endpoint import LoggingLLMEndpoint
from guut.llm_endpoints.openai_endpoint import OpenAIEndpoint
from guut.llm_endpoints.safeguard_endpoint import SafeguardLLMEndpoint
from guut.loop import Loop, State
from guut.prompts import LongInstructions, SystemInstructions
from guut.quixbugs import QuixbugsProblem


def main():
    endpoint = LoggingLLMEndpoint(SafeguardLLMEndpoint(get_openai_endpoint()))
    # endpoint = SafeguardLLMEndpoint(get_llama_endpoint())
    # endpoint = MockLLMEndpoint()

    problem = QuixbugsProblem("detect_cycle")
    problem.validate()

    conversation = Conversation(
        [
            SystemInstructions().message(),
            LongInstructions().message(),
            UserMessage(f"# Task\n\n{format_task(problem)}"),
        ]
    )

    loop = Loop(problem, endpoint=endpoint, conversation=conversation)
    loop.set_state(State.INITIAL)

    while loop.get_state() not in [State.DONE, State.BETWEEN, State.INVALID]:
        loop.perform_next_step()


def get_llama_endpoint() -> LlamacppEndpoint:
    llama_path = os.environ["LLAMA_PATH"]
    client = Llama(model_path=llama_path)
    return LlamacppEndpoint(client)


def get_openai_endpoint() -> OpenAIEndpoint:
    client = OpenAI()
    return OpenAIEndpoint(client, "gpt-4o-mini")
