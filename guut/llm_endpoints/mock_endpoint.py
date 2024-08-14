import tempfile
import time

from llama_cpp import Path
from llama_cpp.llama_cache import List
from loguru import logger

from guut.llm import AssistantMessage, Conversation, LLMEndpoint

TEMP_PATH = Path(tempfile.gettempdir()) / "guut"
TEMP_PATH.mkdir(exist_ok=True)
CONVERSATION_PATH = TEMP_PATH / "guut/conversation"
RESPONSE_PATH = TEMP_PATH / "guut/response"


class MockLLMEndpoint(LLMEndpoint):
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        CONVERSATION_PATH.write_text(repr(conversation))
        logger.info(f"Wrote conversation to '{CONVERSATION_PATH}'.")
        logger.info(f"Please write the response to '{RESPONSE_PATH}'...")
        while True:
            if RESPONSE_PATH.is_file():
                logger.info("Found response.")
                content = RESPONSE_PATH.read_text()
                CONVERSATION_PATH.unlink()
                RESPONSE_PATH.unlink()
                return AssistantMessage(content=content)
            else:
                time.sleep(0.25)
