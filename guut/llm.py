import copy
from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, override


class Role(Enum):
    """Represents the type of message in a LLM conversation."""

    # System message.
    SYSTEM = "system"

    # User message.
    USER = "user"

    # Generated response from the assistant.
    ASSISTANT = "assistant"


Json = Dict[str, object]


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

    @staticmethod
    def from_json(json: Dict[str, Any]) -> "Usage":
        return Usage(
            prompt_tokens=json["prompt_tokens"],
            completion_tokens=json["completion_tokens"],
            total_tokens=json["total_tokens"],
        )


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
        return f"Message(role={self.role.value}, tag={self.tag})\n{self.content}"

    def copy(self):
        return copy.deepcopy(self)

    @staticmethod
    def from_json(json: Dict[str, Any]) -> "Message":
        role = json["role"]
        if role == Role.SYSTEM.value:
            return SystemMessage(json["content"], tag=json.get("tag"))
        elif role == Role.USER.value:
            return UserMessage(json["content"], tag=json.get("tag"))
        elif role == Role.ASSISTANT.value:
            return AssistantMessage.from_json(json)
        else:
            raise Exception(f"Unknown role: {role}")


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
    # The response object from the API, as a dict.
    response: Any | None

    # The token usage to generate this message.
    usage: Usage | None

    # A unique id.
    id: str | None

    def __init__(
        self,
        content: str,
        response: Any = None,
        usage: Usage | None = None,
        tag: Any | None = None,
        id: str | None = None,
    ):
        super().__init__()
        self.role = Role.ASSISTANT
        self.content = content
        self.response = response
        self.usage = usage
        self.tag = tag
        self.id = id

    @override
    def to_json(self):
        json = super().to_json()
        json["usage"] = self.usage.to_json() if self.usage else None
        json["response"] = self.response
        json["id"] = self.id
        return json

    @override
    @staticmethod
    def from_json(json: Dict[str, Any]) -> "AssistantMessage":
        content = json["content"]
        tag = json.get("tag")
        usage = json.get("usage")
        response = json.get("response")
        id = json.get("id")
        return AssistantMessage(
            content=content, tag=tag, usage=(Usage.from_json(usage) if usage else None), response=response, id=id
        )


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
        self.name: str | None = None

    def to_json(self):
        """Converts the conversation into JSON for logging."""
        return [msg.to_json() for msg in self]

    def __repr__(self):
        return "\n\n".join(repr(msg) for msg in self)

    def __str__(self):
        return "\n".join(msg.content for msg in self)

    def copy(self) -> "Conversation":
        return Conversation([msg.copy() for msg in self])

    @staticmethod
    def from_json(json: List[Dict[str, Any]]):
        return Conversation([Message.from_json(msg) for msg in json])


class LLMEndpoint:
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        raise NotImplementedError()
