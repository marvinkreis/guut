from dataclasses import dataclass
from enum import Enum
from typing import Any, List

from llama_cpp import Llama, ChatCompletionRequestSystemMessage, ChatCompletionRequestUserMessage, \
    ChatCompletionRequestAssistantMessage, CreateChatCompletionResponse
from loguru import logger
from openai import OpenAI
from openai.types.chat import ChatCompletion


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


@dataclass
class Message:
    # The type of message (system, user, assistant).
    role: Role

    # Text content of the message.
    content: str

    def to_openai_api(self):
        """Converts the message into JSON for the OpenAI API."""
        return {
            'role': self.role.value,
            'content': self.content
        }

    def to_llamacpp_api(self):
        """Converts the message into JSON for the llama.cpp API."""
        raise Exception("Can't convert base message to llama.cpp API.")

    def __str__(self):
        return self.content

    def __repr__(self):
        content = ''.join(['    ' + line for line in self.content.splitlines(keepends=True)])
        return f'Message({self.role.name},\n{content})'


class SystemMessage(Message):
    def __init__(self, content):
        self.role = Role.SYSTEM
        self.content = content

    def to_llamacpp_api(self):
        return ChatCompletionRequestSystemMessage(content=self.content, role='system')


class UserMessage(Message):
    def __init__(self, content):
        self.role = Role.USER
        self.content = content

    def to_llamacpp_api(self):
        return ChatCompletionRequestUserMessage(content=self.content, role='user')


class AssistantMessage(Message):
    # The full response object from the API.
    response: Any

    # The token usage to generate this message.
    usage: Usage

    def __init__(self, content: str, response: Any, usage: Usage):
        self.role = Role.ASSISTANT
        self.content = content
        self.response = response
        self.usage = usage

    @staticmethod
    def from_openai_api(response: ChatCompletion):
        message = response['choices'][0]['message']
        content = message.get('content')
        usage = Usage(**response['usage'])
        return AssistantMessage(content, response, usage)

    @classmethod
    def from_llamacpp_api(cls, response: CreateChatCompletionResponse):
        message = response['choices'][0]['message']
        content = message.get('content')
        usage = Usage(**response['usage'])
        return AssistantMessage(content, response, usage)

    def to_llamacpp_api(self):
        return ChatCompletionRequestAssistantMessage(content=self.content, role='assistant')


class Conversation(list):
    def __init__(self, messages: List[Message] = None):
        super().__init__(messages)

    def to_openai_api(self):
        """Converts the conversation into JSON for the OpenAI API."""
        return [msg.to_openai_api() for msg in self]

    def to_llamacpp_api(self):
        """Converts the conversation into JSON for the llama.cpp API."""
        return [msg.to_llamacpp_api() for msg in self]

    def __repr__(self):
        return '\n'.join(repr(msg) for msg in self)

    def __str__(self):
        return '\n'.join(msg.content for msg in self)


class LLMEndpoint:
    def complete(self, conversation: Conversation, **kwargs):
        pass


class OpenAIEndpoint(LLMEndpoint):
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    def complete(self, conversation: Conversation, **kwargs):
        logger.info(f'''Requesting completion:
    args: {kwargs}
    conversation: {conversation.to_openai_api()}''')
        response = self.client.chat.completions.create(
            model=self.model,
            messages=conversation.to_openai_api(),
            **kwargs)
        return AssistantMessage.from_openai_api(response)


class LlamacppEndpoint(LLMEndpoint):
    def __init__(self, client: Llama):
        self.client = client

    def complete(self, conversation: Conversation, **kwargs):
        logger.info(f'''Requesting completion:
    args: {kwargs}
    conversation: {conversation.to_llamacpp_api()}''')
        response = self.client.create_chat_completion(
            messages=conversation.to_llamacpp_api(),
            **kwargs)
        return AssistantMessage.from_llamacpp_api(response)

