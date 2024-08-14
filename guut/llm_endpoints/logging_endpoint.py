from typing import override

from llama_cpp.llama_cache import List

from guut.llm import AssistantMessage, Conversation, LLMEndpoint
from guut.logging import LOG_BASE_PATH, Logger

LOG_PATH = LOG_BASE_PATH / "endpoint"
LOG_PATH.mkdir(parents=True, exist_ok=True)
logger = Logger(LOG_PATH, overwrite_old_logs=False)


class LoggingLLMEndpoint(LLMEndpoint):
    def __init__(self, delegate: LLMEndpoint):
        self.delegate = delegate

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        logger.log_conversation(conversation, name=f"{conversation.name} {len(conversation):02d} conversation")
        response = self.delegate.complete(conversation, stop=stop, **kwargs)
        logger.log_message(response, f"{conversation.name} {len(conversation):02d} response")
        return response
