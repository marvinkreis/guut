from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, cast

from llama_cpp import Llama, ChatCompletionRequestSystemMessage, ChatCompletionRequestUserMessage, \
    ChatCompletionRequestAssistantMessage, CreateChatCompletionResponse
from loguru import logger
from openai import OpenAI
from openai.types.chat import ChatCompletion

from guut.formatting import indent_block


class Role(Enum):
    """Represents the type of message in a LLM conversation."""

    # System message.
    SYSTEM = 'system'

    # User message.
    USER = 'user'

    # Generated response from the assistant.
    ASSISTANT = 'assistant'


@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    def to_json(self):
        return {
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
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
        raise Exception("Can't convert base message.")

    def to_llamacpp_api(self):
        """Converts the message into the format for the llama.cpp API."""
        raise Exception("Can't convert base message.")

    def to_json(self):
        """Converts the message into JSON for logging."""
        raise Exception("Can't convert base message.")

    def __str__(self):
        return self.content

    def __repr__(self):
        return f'{self.role.name} MESSAGE:\n{indent_block(self.content)})'


class SystemMessage(Message):
    def __init__(self, content):
        super().__init__()
        self.role = Role.SYSTEM
        self.content = content

    def to_openai_api(self):
        return {'role': 'system', 'content': self.content}

    def to_llamacpp_api(self):
        return ChatCompletionRequestSystemMessage(content=self.content, role='system')

    def to_json(self):
        return {'role': 'system', 'content': self.content}


class UserMessage(Message):
    def __init__(self, content):
        super().__init__()
        self.role = Role.USER
        self.content = content

    def to_openai_api(self):
        return {'role': 'user', 'content': self.content}

    def to_llamacpp_api(self):
        return ChatCompletionRequestUserMessage(content=self.content, role='user')

    def to_json(self):
        return {'role': 'user', 'content': self.content}


class AssistantMessage(Message):
    # The full response object from the API.
    response: Any

    # The token usage to generate this message.
    usage: Usage

    def __init__(self, content: str, response: Any = None, usage: Usage = None):
        super().__init__()
        self.role = Role.ASSISTANT
        self.content = content
        self.response = response
        self.usage = usage

    @staticmethod
    def from_openai_api(response: ChatCompletion) -> 'AssistantMessage':
        content = response.choices[0].message.content
        usage = Usage(completion_tokens=response.usage.completion_tokens,
                      prompt_tokens=response.usage.prompt_tokens,
                      total_tokens=response.usage.total_tokens)
        return AssistantMessage(content, response, usage)

    @classmethod
    def from_llamacpp_api(cls, response: CreateChatCompletionResponse) -> 'AssistantMessage':
        message = response['choices'][0]['message']
        content = message.get('content')
        usage = Usage(completion_tokens=response['usage']['completion_tokens'],
                      prompt_tokens=response['usage']['prompt_tokens'],
                      total_tokens=response['usage']['total_tokens'])
        return AssistantMessage(content, response, usage)

    def to_openai_api(self):
        return {'role': 'assistant', 'content': self.content}

    def to_llamacpp_api(self):
        return ChatCompletionRequestAssistantMessage(content=self.content, role='assistant')

    def to_json(self):
        json = {'role': 'user', 'content': self.content}
        if self.usage:
            json['usage'] = self.usage.to_json()
        return


class Conversation(list):
    def __init__(self, messages: List[Message] = None):
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
        return '\n'.join(repr(msg) for msg in self)

    def __str__(self):
        return '\n'.join(msg.content for msg in self)

    def copy(self) -> 'Conversation':
        return Conversation([*self])


class LLMEndpoint:
    def complete(self, conversation: Conversation, stop: List[str] = None, **kwargs) -> AssistantMessage:
        pass


class OpenAIEndpoint(LLMEndpoint):
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def complete(self, conversation: Conversation, stop: List[str] = None, **kwargs) -> AssistantMessage:
        stop = stop or kwargs.get('stop')
        logger.info(f'''Requesting completion:
    args: {kwargs}
    conversation: {conversation.to_openai_api()}''')
        response = self.client.chat.completions.create(
            model=self.model,
            messages=conversation.to_openai_api(),
            stop=stop,
            **kwargs)
        return AssistantMessage.from_openai_api(response)


class LlamacppEndpoint(LLMEndpoint):
    def __init__(self, client: Llama):
        self.client = client

    def complete(self, conversation: Conversation, stop: List[str] = None, **kwargs) -> AssistantMessage:
        stop = stop or kwargs.get('stop')
        logger.info(f'''Requesting completion:
    args: {kwargs}
    conversation: {conversation.to_llamacpp_api()}''')
        response = self.client.create_chat_completion(
            messages=conversation.to_llamacpp_api(),
            stop=stop,
            **kwargs)
        return AssistantMessage.from_llamacpp_api(response)

