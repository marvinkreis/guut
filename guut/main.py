import os

from llama_cpp import Llama
from openai import OpenAI

from guut.llm import OpenAIEndpoint, LlamacppEndpoint, LoggingLLMEndpoint, SafeLLMEndpoint, Conversation, \
    MockLLMEndpoint, UserMessage
from guut.loop import Loop, LoopState
from guut.quixbugs_helper import Problem, format_problem
from prompts import LongInstructions, FewShotExample01


def main():
    endpoint = LoggingLLMEndpoint(SafeLLMEndpoint(get_openai_endpoint()))
    # endpoint = SafeLLMEndpoint(MockLLMEndpoint())

    conversation = Conversation([
        LongInstructions().message(),
        *FewShotExample01().messages(),
        UserMessage(format_problem(Problem('detect_cycle')))
    ])


    loop = Loop(Problem('sieve'), endpoint=endpoint, conversation=conversation)
    loop.set_state(LoopState.PROBLEM_STATED)

    while loop.get_state() not in [LoopState.TEST_DONE, LoopState.BETWEEN, LoopState.INVALID]:
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


