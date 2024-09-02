import json
import os
import pickle
import re
from datetime import datetime
from pathlib import Path
from typing import List

from guut.formatting import format_conversation_pretty, format_timestamp
from guut.llm import Conversation

FILENAME_REPLACEMENET_REGEX = r"[^0-9a-zA-Z]+"
LOG_PATH = Path(os.environ["LOGGING_PATH"])


def clean_filename(name: str) -> str:
    return re.sub(FILENAME_REPLACEMENET_REGEX, "_", name)


class ConversationLogger:
    def __init__(self, directory: Path = LOG_PATH):
        self.old_logs: List[Path] = []
        self.directory = directory

    def log_conversation(self, conversation: Conversation, name: str) -> None:
        for path in self.old_logs:
            path.unlink()
        self.old_logs = []

        timestamp = datetime.now()
        pickle_path = self.construct_file_name(name, "pickle", timestamp)
        json_path = self.construct_file_name(name, "json", timestamp)
        text_path = self.construct_file_name(name, "txt", timestamp)

        self.old_logs += [pickle_path, json_path, text_path]

        pickle_path.write_bytes(pickle.dumps(conversation))
        json_path.write_text(json.dumps(conversation.to_json()))
        text_path.write_text(format_conversation_pretty(conversation))

    def construct_file_name(self, name: str, suffix: str, timestamp: datetime) -> Path:
        return self.directory / f"[{format_timestamp(timestamp)}] {name}.{suffix}"
