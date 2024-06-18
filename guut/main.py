import os
import sys

from llama_cpp import Llama
from openai import OpenAI

from guut.llm import OpenAIEndpoint, Conversation, LlamacppEndpoint, UserMessage
from guut.log import log_conversation
from guut.prompts import prompt
from guut.quixbugs_helper import Problem, format_problem


def main():
    problem = get_problem()
    conversation = prepare_conversation(problem)
    endpoint = get_openai_endpoint()

    print(repr(conversation))

    response = endpoint.complete(conversation)
    conversation.append(response)

    print(repr(response))

    log_conversation(conversation)


def get_problem() -> Problem:
    if len(sys.argv) != 2:
        print("Please provide a QuixBugs problem name")

    problem = Problem(sys.argv[1])
    problem.validate()
    return problem


def prepare_conversation(problem: Problem) -> Conversation:
    prompt_instance = f'{prompt}\n{format_problem(problem)}'

    return Conversation([
        UserMessage(prompt_instance)
    ])


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
