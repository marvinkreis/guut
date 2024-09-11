import json
import re
from datetime import datetime
from pathlib import Path
from typing import List

from guut.config import config
from guut.formatting import format_conversation_pretty, format_message_pretty, format_timestamp
from guut.llm import Conversation

FILENAME_REPLACEMENET_REGEX = r"[^0-9a-zA-Z]+"


def clean_filename(name: str) -> str:
    return re.sub(FILENAME_REPLACEMENET_REGEX, "_", name)


class ConversationLogger:
    def __init__(self, directory: Path | None = None):
        self.old_logs: List[Path] = []
        if directory:
            self.directory = directory
        else:
            self.directory = Path(config.logging_path)

    def log_conversation(self, conversation: Conversation, name: str) -> None:
        for path in self.old_logs:
            path.unlink()
        self.old_logs = []

        timestamp = datetime.now()
        json_path = self.construct_file_name(name, "json", timestamp)
        text_path = self.construct_file_name(name, "txt", timestamp)

        self.old_logs += [json_path, text_path]

        with json_path.open("w") as file:
            json.dump(conversation.to_json(), file)
        text_path.write_text(format_conversation_pretty(conversation))

    def construct_file_name(self, name: str, suffix: str, timestamp: datetime) -> Path:
        return self.directory / f"[{format_timestamp(timestamp)}] {name}.{suffix}"


class MessagePrinter:
    def __init__(self, print_raw: bool):
        self.print_raw = print_raw
        self.seen_messages = []

    def print_new_messages(self, conversation: Conversation):
        new_messages = [msg for msg in conversation if msg not in self.seen_messages]
        for msg in new_messages:
            if self.print_raw:
                print(msg.content)
            else:
                print(format_message_pretty(msg))
        self.seen_messages += new_messages
