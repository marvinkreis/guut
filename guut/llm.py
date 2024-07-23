import copy
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, override

from llama_cpp import (
    ChatCompletionRequestAssistantMessage,
    ChatCompletionRequestSystemMessage,
    ChatCompletionRequestUserMessage,
    CreateChatCompletionResponse,
    Llama,
)
from loguru import logger
from openai import OpenAI
from openai.types.chat import ChatCompletion

from guut.formatting import indent_block
from guut.log import log_conversation


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

    def to_openai_api(self):
        """Converts the message into JSON for the OpenAI API."""
        return {"role": self.role.value, "content": self.content}

    @abstractmethod
    def to_llamacpp_api(self):
        """Converts the message into the format for the llama.cpp API."""
        raise Exception("Can't convert base message.")

    def to_json(self):
        """Converts the message into JSON for logging."""
        return {"role": self.role.value, "content": self.content}

    def __str__(self):
        return self.content

    def __repr__(self):
        return f"{self.role.name} MESSAGE:\n{indent_block(self.content)}"


class SystemMessage(Message):
    def __init__(self, content: str, tag: Any = None):
        super().__init__()
        self.role = Role.SYSTEM
        self.content = content
        self.tag = tag

    @override
    def to_llamacpp_api(self):
        return ChatCompletionRequestSystemMessage(content=self.content, role="system")


class UserMessage(Message):
    def __init__(self, content: str, tag: Any = None):
        super().__init__()
        self.role = Role.USER
        self.content = content
        self.tag = tag

    @override
    def to_llamacpp_api(self):
        return ChatCompletionRequestUserMessage(content=self.content, role="user")


class AssistantMessage(Message):
    # The full response object from the API.
    response: Any

    # The token usage to generate this message.
    usage: Usage

    def __init__(self, content: str, response: Any = None, usage: Usage = None, tag: Any = None):
        super().__init__()
        self.role = Role.ASSISTANT
        self.content = content
        self.response = response
        self.usage = usage
        self.tag = tag

    @staticmethod
    def from_openai_api(response: ChatCompletion) -> "AssistantMessage":
        content = response.choices[0].message.content

        if not content or not response.usage:
            raise Exception("Incomplete OpenAI response")

        usage = Usage(
            completion_tokens=response.usage.completion_tokens,
            prompt_tokens=response.usage.prompt_tokens,
            total_tokens=response.usage.total_tokens,
        )
        return AssistantMessage(content, response, usage)

    @staticmethod
    def from_llamacpp_api(response: CreateChatCompletionResponse) -> "AssistantMessage":
        message = response["choices"][0]["message"]
        content = message.get("content")
        usage = Usage(
            completion_tokens=response["usage"]["completion_tokens"],
            prompt_tokens=response["usage"]["prompt_tokens"],
            total_tokens=response["usage"]["total_tokens"],
        )
        return AssistantMessage(content, response, usage)

    @override
    def to_llamacpp_api(self):
        return ChatCompletionRequestAssistantMessage(content=self.content, role="assistant")

    @override
    def to_json(self):
        json: Dict[str, Any] = {"role": Role.ASSISTANT.name, "content": self.content}
        if self.usage:
            json["usage"] = self.usage.to_json()
        return json


class FakeAssistantMessage(Message):
    def __init__(self, content: str, tag: Any = None):
        super().__init__()
        self.role = Role.ASSISTANT
        self.content = content
        self.tag = tag

    @override
    def to_llamacpp_api(self):
        return ChatCompletionRequestAssistantMessage(content=self.content, role="assistant")


class Conversation(list):
    def __init__(self, messages: List[Message] | None = None):
        if messages:
            super().__init__(messages)
        else:
            super().__init__()

    def to_openai_api(self):
        """converts the conversation into json for the openai api."""
        return [msg.to_openai_api() for msg in self]

    def to_llamacpp_api(self):
        """Converts the conversation into the format for the llama.cpp API."""
        return [msg.to_llamacpp_api() for msg in self]

    def to_json(self):
        """Converts the conversation into JSON for logging."""
        return [msg.to_json() for msg in self]

    def __repr__(self):
        return "\n".join(repr(msg) for msg in self)

    def __str__(self):
        return "\n".join(msg.content for msg in self)

    def copy(self) -> "Conversation":
        return Conversation([copy.deepcopy(msg) for msg in self])


class LLMEndpoint:
    def complete(self, conversation: Conversation, stop: List[str] = None, **kwargs) -> AssistantMessage:
        pass


class LoggingLLMEndpoint(LLMEndpoint):
    def __init__(self, delegate: LLMEndpoint):
        self.delegate = delegate

    @override
    def complete(self, conversation: Conversation, stop: List[str] = None, **kwargs) -> AssistantMessage:
        log_conversation(conversation)
        return self.delegate.complete(conversation, stop=stop, **kwargs)


class SafeLLMEndpoint(LLMEndpoint):
    def __init__(self, delegate: LLMEndpoint):
        self.delegate = delegate

    @override
    def complete(self, conversation: Conversation, stop: List[str] = None, **kwargs) -> AssistantMessage:
        answer = input(f"""Requesting completion (args: {kwargs})
{repr(conversation)}

Request this completion? [yn] """)
        if answer.strip().lower() == "y":
            msg = self.delegate.complete(conversation, stop=stop, **kwargs)
            print(f"Response:\n{repr(msg)}")
            return msg
        else:
            raise Exception("Request denied.")


class OpenAIEndpoint(LLMEndpoint):
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        stop = stop or kwargs.get("stop")
        log_data = {
            "args": kwargs,
            "stop": stop,
            "conversation": conversation.to_json(),
        }
        logger.info(f"Requesting completion: {json.dumps(log_data)}")
        response = self.client.chat.completions.create(
            model=self.model, messages=conversation.to_openai_api(), stop=stop, **kwargs
        )
        return AssistantMessage.from_openai_api(response)


class LlamacppEndpoint(LLMEndpoint):
    def __init__(self, client: Llama):
        self.client = client

    @override
    def complete(self, conversation: Conversation, stop: List[str] = None, **kwargs) -> AssistantMessage:
        stop = stop or kwargs.get("stop")
        log_data = {
            "args": kwargs,
            "stop": stop,
            "conversation": conversation.to_json(),
        }
        logger.info(f"Requesting completion: {json.dumps(log_data)}")
        response = self.client.create_chat_completion(messages=conversation.to_llamacpp_api(), stop=stop, **kwargs)
        return AssistantMessage.from_llamacpp_api(response)


class MockLLMEndpoint(LLMEndpoint):
    def complete(self, conversation: Conversation, stop: List[str] = None, **kwargs) -> AssistantMessage:
        path = Path("/tmp/answer")
        print(f"{repr(conversation)}\n\nWrite answer to {path}...")
        while True:
            if path.is_file():
                print("Found answer!")
                content = path.read_text()
                path.unlink()
                return AssistantMessage(content=content)
            else:
                time.sleep(1)
