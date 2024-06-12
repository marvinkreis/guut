from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from openai import AsyncOpenAI

JSON = Any  # good enough for now


class Role(Enum):
    """Represents the type of message in a LLM conversation."""

    # System message.
    SYSTEM = 'system'

    # User message.
    USER = 'user'

    # Generated response from the assistant.
    ASSISTANT = 'assistant'


@dataclass
class Message:
    # The type of message (system, user, assistant).
    role: Role

    # Text content of the message.
    content: str

    # The full response object from the API. Only LLM-generated messages.
    response: Optional[Any] = None

    def to_openai_api(self):
        """Converts the message into JSON for the OpenAI API."""
        return {
            'role': self.role.value,
            'content': self.content
        }

    def __str__(self):
        return self.content

    def __repr__(self):
        return f'''Message({self.role.name},
{self.content})'''

    @staticmethod
    def system(content: str):
        return Message(Role.SYSTEM, content)

    @staticmethod
    def user(content: str):
        return Message(Role.USER, content)

    @staticmethod
    def assistant(content: str = None, response=None):
        return Message(Role.ASSISTANT, content, response)

    @staticmethod
    def from_openai_api(response: JSON):
        message = response['choices'][0]['message']
        content = message.get('content')
        return Message(Role.ASSISTANT, content, response=response)


class Conversation(list):
    def to_openai_api(self):
        """Converts the conversation into JSON for the OpenAI API."""
        return [msg.to_openai_api() for msg in self]

    def __repr__(self):
        return '\n'.join(repr(msg) for msg in self)

    def __str__(self):
        return '\n'.join(msg.content for msg in self)


class ChatGPTEndpoint:
    def __init__(self, client: AsyncOpenAI):
        self.model = 'gpt-3.5-turbo-0125'
        self.client = client

    async def complete(self, conversation: Conversation, **kwargs):
        print(f'''Requesting completion:
    args: {kwargs}
    conversation: {conversation.to_openai_api()}''')
        return await self.client.chat.completions.create(
            model=self.model,
            messages=conversation.to_openai_api(),
            **kwargs)
