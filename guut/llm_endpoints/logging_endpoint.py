import json
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import override

from llama_cpp.llama_cache import List

from guut.llm import AssistantMessage, Conversation, LLMEndpoint

LOGGING_PATH = Path(os.environ["LOGGING_PATH"])


class LoggingLLMEndpoint(LLMEndpoint):
    def __init__(self, delegate: LLMEndpoint):
        self.delegate = delegate

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        log_conversation(conversation, "before_completion")

        answer = self.delegate.complete(conversation, stop=stop, **kwargs)

        conversation_after = conversation.copy()
        conversation_after.append(answer)
        log_conversation(conversation_after, "after_completion")

        return answer


def format_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def get_logfile_path(name: str, suffix: str) -> Path:
    path = LOGGING_PATH / f"{name}{suffix}"

    i = 2
    while path.exists():
        path = LOGGING_PATH / f"{name} {i:02d}{suffix}"
        i += 1

    return path


def log_conversation(conversation: Conversation, name: str) -> None:
    timestamp = format_timestamp()
    name = f"{timestamp} {name}"

    pickle_path = get_logfile_path(name, ".pickle")
    json_path = get_logfile_path(name, ".json")
    text_path = get_logfile_path(name, ".txt")

    pickle_path.write_bytes(pickle.dumps(conversation))
    json_path.write_text(json.dumps(conversation.to_json()))
    text_path.write_text(repr(conversation))
