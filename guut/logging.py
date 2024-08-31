import json
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import List

from guut.formatting import format_conversation_pretty, format_timestamp
from guut.llm import Conversation

LOG_BASE_PATH = Path(os.environ["LOGGING_PATH"])


class Logger:
    def __init__(self, path: Path):
        self.path = path
        self.old_logs: List[Path] = []

    def file(self, name: str, suffix: str, timestamp: datetime) -> Path:
        return self.path / f"[{format_timestamp(timestamp)}] {name}.{suffix}"

    def log_conversation(self, conversation: Conversation, name: str) -> None:
        for path in self.old_logs:
            path.unlink()
        self.old_logs = []

        timestamp = datetime.now()
        pickle_path = self.file(name, "pickle", timestamp)
        json_path = self.file(name, "json", timestamp)
        text_path = self.file(name, "txt", timestamp)

        self.old_logs += [pickle_path, json_path, text_path]

        pickle_path.write_bytes(pickle.dumps(conversation))
        json_path.write_text(json.dumps(conversation.to_json(), default=lambda x: None))
        text_path.write_text(format_conversation_pretty(conversation))
