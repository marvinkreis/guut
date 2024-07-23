import os

from llama_cpp import Llama
from openai import OpenAI

from guut.formatting import format_problem
from guut.llm import Conversation, LlamacppEndpoint, MockLLMEndpoint, OpenAIEndpoint, SafeLLMEndpoint, UserMessage
from guut.loop import Loop, State
from guut.quixbugs import QuixbugsProblem
from prompts import FewShotExample01, LongInstructions


def main():
    # endpoint = LoggingLLMEndpoint(SafeLLMEndpoint(get_openai_endpoint()))
    endpoint = SafeLLMEndpoint(MockLLMEndpoint())

    conversation = Conversation(
        [
            LongInstructions().message(),
            *FewShotExample01().messages(),
            UserMessage(format_problem(QuixbugsProblem("detect_cycle"))),
        ]
    )

    loop = Loop(QuixbugsProblem("sieve"), endpoint=endpoint, conversation=conversation)
    loop.set_state(State.INITIAL)

    while loop.get_state() not in [State.DONE, State.BETWEEN, State.INVALID]:
        loop.perform_next_step()


def get_llama_endpoint() -> LlamacppEndpoint:
    llama_path = os.environ["LLAMA_PATH"]
    client = Llama(
        model_path=llama_path,
        n_gpu_layers=-1,  # Uncomment to use GPU acceleration
        # seed=1337, # Uncomment to set a specific seed
        # n_ctx=2048, # Uncomment to increase the context window
    )
    return LlamacppEndpoint(client)


def get_openai_endpoint() -> OpenAIEndpoint:
    client = OpenAI()
    return OpenAIEndpoint(client, "gpt-3.5-turbo-0125")
