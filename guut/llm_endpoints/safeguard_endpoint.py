import tempfile
import time
from pathlib import Path
from typing import override

from llama_cpp.llama_cache import List
from loguru import logger

from guut.llm import AssistantMessage, Conversation, LLMEndpoint

TEMP_DIR = Path(tempfile.gettempdir()) / "guut"
CONVERSATION_PATH = TEMP_DIR / "conversation"
RESPONSE_PATH = TEMP_DIR / "response"


class SafeguardLLMEndpoint(LLMEndpoint):
    def __init__(self, delegate: LLMEndpoint):
        self.delegate = delegate
        if not TEMP_DIR.exists():
            TEMP_DIR.mkdir()

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        CONVERSATION_PATH.write_text(repr(conversation))
        logger.info(f"Wrote conversation to '{CONVERSATION_PATH}'.")
        logger.info(f"Request this completion? Write [yn] to '{RESPONSE_PATH}'...")

        while True:
            if RESPONSE_PATH.is_file():
                content = RESPONSE_PATH.read_text()
                CONVERSATION_PATH.unlink()
                RESPONSE_PATH.unlink()
                if content.strip() == "y":
                    logger.info("Requesting completion.")
                    return self.delegate.complete(conversation, stop=stop, **kwargs)
                else:
                    logger.info("Denied completion.")
                    raise Exception("Denied completion.")
            else:
                time.sleep(0.5)
