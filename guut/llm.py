import copy
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, override

from guut.formatting import indent_text


class Role(Enum):
    """Represents the type of message in a LLM conversation."""

    # System message.
    SYSTEM = "system"

    # User message.
    USER = "user"

    # Generated response from the assistant.
    ASSISTANT = "assistant"


@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def to_json(self):
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class Message(ABC):
    # The type of message (system, user, assistant).
    role: Role

    # Text content of the message.
    content: str

    # Any additional data.
    tag: Any

    def __init__(self):
        self.tag = None

    def to_json(self):
        """Converts the message into JSON for logging."""
        return {"role": self.role.value, "content": self.content, "tag": self.tag}

    def __str__(self):
        return self.content

    def __repr__(self):
        return f"Message (role = {self.role.value}, tag = {self.tag}):\n{indent_text(self.content)}"

    def copy(self):
        return copy.deepcopy(self)


class SystemMessage(Message):
    def __init__(self, content: str, tag: Any = None):
        super().__init__()
        self.role = Role.SYSTEM
        self.content = content
        self.tag = tag


class UserMessage(Message):
    def __init__(self, content: str, tag: Any = None):
        super().__init__()
        self.role = Role.USER
        self.content = content
        self.tag = tag


class AssistantMessage(Message):
    # The full response object from the API.
    response: Any | None

    # The token usage to generate this message.
    usage: Usage | None

    def __init__(self, content: str, response: Any = None, usage: Usage | None = None, tag: Any = None):
        super().__init__()
        self.role = Role.ASSISTANT
        self.content = content
        self.response = response
        self.usage = usage
        self.tag = tag

    @override
    def to_json(self):
        json = super().to_json()
        json["usage"] = self.usage.to_json() if self.usage else None
        return json


class FakeAssistantMessage(Message):
    def __init__(self, content: str, tag: Any = None):
        super().__init__()
        self.role = Role.ASSISTANT
        self.content = content
        self.tag = tag


class Conversation(list):
    def __init__(self, messages: List[Message] | None = None):
        if messages:
            super().__init__(messages)
        else:
            super().__init__()

    def to_json(self):
        """Converts the conversation into JSON for logging."""
        return [msg.to_json() for msg in self]

    def __repr__(self):
        return "\n\n".join(repr(msg) for msg in self)

    def __str__(self):
        return "\n".join(msg.content for msg in self)

    def copy(self) -> "Conversation":
        return Conversation([msg.copy() for msg in self])


class LLMEndpoint:
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        raise NotImplementedError()
