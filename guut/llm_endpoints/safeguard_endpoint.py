from typing import override

from llama_cpp.llama_cache import List
from loguru import logger

from guut.llm import AssistantMessage, Conversation, EndpointDescription, LLMEndpoint


class SafeguardLLMEndpoint(LLMEndpoint):
    def __init__(self, delegate: LLMEndpoint):
        self.delegate = delegate

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        while True:
            answer = input("Request this completion? [y/n] ")
            if answer.strip() == "y":
                logger.info("Requesting completion.")
                return self.delegate.complete(conversation, stop=stop, **kwargs)
            elif answer.strip() == "n":
                logger.info("Denied completion.")
                raise Exception("Denied completion.")

    @override
    def get_description(self) -> EndpointDescription:
        return self.delegate.get_description()
