import os

from llama_cpp import Llama
from openai import OpenAI

from guut.llm import OpenAIEndpoint, LlamacppEndpoint, LoggingLLMEndpoint, SafeLLMEndpoint
from guut.loop import Loop, LoopState
from guut.quixbugs_helper import Problem


def main():
    endpoint = LoggingLLMEndpoint(SafeLLMEndpoint(get_openai_endpoint()))
    loop = Loop(Problem('detect_cycle'), endpoint)
    loop.perform_next_step()

    while loop.get_state() != LoopState.TEST_DONE and loop.get_state() != LoopState.BETWEEN:
        loop.perform_next_step()


def get_llama_endpoint() -> LlamacppEndpoint:
    llama_path = os.environ['LLAMA_PATH']
    client = Llama(
        model_path=llama_path,
        n_gpu_layers=-1, # Uncomment to use GPU acceleration
        # seed=1337, # Uncomment to set a specific seed
        # n_ctx=2048, # Uncomment to increase the context window
    )
    return LlamacppEndpoint(client)


def get_openai_endpoint() -> OpenAIEndpoint:
    client = OpenAI()
    return OpenAIEndpoint(client, 'gpt-3.5-turbo-0125')


