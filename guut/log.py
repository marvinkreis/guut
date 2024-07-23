import json
import os
import pickle
from datetime import datetime
from pathlib import Path

LOGGING_PATH = Path(os.environ["LOGGING_PATH"])


def format_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")


def get_logfile_path(timestamp: str, suffix: str) -> Path:
    path = LOGGING_PATH / f"{timestamp}{suffix}"

    i = 2
    while path.exists():
        path = LOGGING_PATH / f"{timestamp} {i}{suffix}"
        i += 1

    return path


def log_conversation(conversation: "Conversation") -> None:
    timestamp = format_timestamp()

    pickle_path = get_logfile_path(timestamp, ".pickle")
    json_path = get_logfile_path(timestamp, ".json")
    text_path = get_logfile_path(timestamp, ".txt")

    pickle_path.write_bytes(pickle.dumps(conversation))
    json_path.write_text(json.dumps(conversation.to_json()))
    text_path.write_text(repr(conversation))
