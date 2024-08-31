import json
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import List

from guut.formatting import format_conversation_pretty, format_message_pretty
from guut.llm import AssistantMessage, Conversation

LOG_BASE_PATH = Path(os.environ["LOGGING_PATH"])


class Logger:
    def __init__(self, path: Path, overwrite_old_logs: bool = False):
        self.path = path
        self.overwrite_old_logs = overwrite_old_logs
        self.old_conversation_logs: List[Path] = []
        self.old_message_logs: List[Path] = []

    def file(self, name: str, suffix: str, timestamp: datetime) -> Path:
        return self.path / f"[{timestamp.strftime("%Y-%m-%d %H:%M:%S")}] {name}.{suffix}"

    def log_conversation(self, conversation: Conversation, name: str) -> None:
        if self.overwrite_old_logs:
            for path in self.old_conversation_logs:
                path.unlink()
            self.old_conversation_logs = []

        timestamp = datetime.now()
        pickle_path = self.file(name, "pickle", timestamp)
        json_path = self.file(name, "json", timestamp)
        text_path = self.file(name, "txt", timestamp)

        self.old_conversation_logs += [pickle_path, json_path, text_path]

        pickle_path.write_bytes(pickle.dumps(conversation))
        json_path.write_text(json.dumps(conversation.to_json(), default=lambda x: None))
        text_path.write_text(format_conversation_pretty(conversation))

    def log_message(self, message: AssistantMessage, name: str) -> None:
        if self.overwrite_old_logs:
            for path in self.old_message_logs:
                path.unlink()
            self.old_message_logs = []

        timestamp = datetime.now()
        pickle_path = self.file(name, "pickle", timestamp)
        json_path = self.file(name, "json", timestamp)
        text_path = self.file(name, "txt", timestamp)

        self.old_message_logs += [pickle_path, json_path, text_path]

        pickle_path.write_bytes(pickle.dumps(message))
        json_path.write_text(json.dumps(message.to_json()))
        text_path.write_text(format_message_pretty(message))
