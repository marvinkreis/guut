from pathlib import Path
from typing import override

from llama_cpp.llama_cache import List
from loguru import logger

from guut.llm import AssistantMessage, Conversation, LLMEndpoint

CONVERSATION_PATH = Path("/tmp/guut/conversation")
Path("/tmp/guut").mkdir(exist_ok=True)


class SafeguardLLMEndpoint(LLMEndpoint):
    def __init__(self, delegate: LLMEndpoint):
        self.delegate = delegate

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        CONVERSATION_PATH.write_text(repr(conversation))
        answer = input(f"Wrote conversation to '{CONVERSATION_PATH}'. Request this completion? [y/n] ")

        while True:
            if answer.strip() == "y":
                logger.info("Requesting completion.")
                return self.delegate.complete(conversation, stop=stop, **kwargs)
            elif answer.strip() == "n":
                logger.info("Denied completion.")
                raise Exception("Denied completion.")
            else:
                answer = input("Request this completion? [y/n] ")
