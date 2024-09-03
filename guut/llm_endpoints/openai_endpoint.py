from dataclasses import dataclass
from typing import List, override

from loguru import logger
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_assistant_message_param import ChatCompletionAssistantMessageParam
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam

from guut.llm import (
    AssistantMessage,
    Conversation,
    EndpointDescription,
    FakeAssistantMessage,
    LLMEndpoint,
    Message,
    SystemMessage,
    Usage,
    UserMessage,
)


class OpenAIEndpoint(LLMEndpoint):
    def __init__(self, client: OpenAI, model: str, temperature: int = 1):
        self.client = client
        self.model = model
        self.temperature = 1

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        messages = conversation_to_api(conversation)
        stop = stop or kwargs.get("stop")
        logger.info(f"Requesting completion: num_messages={len(conversation)}, stop={stop}, args={kwargs}")
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, stop=stop, max_tokens=2000, **kwargs
        )
        return msg_from_response(response)

    @override
    def get_description(self) -> EndpointDescription:
        return OpenAIEndpointDescription("openai", model=self.model, temperature=self.temperature)


@dataclass
class OpenAIEndpointDescription(EndpointDescription):
    model: str
    temperature: float


def msg_to_api(message: Message) -> ChatCompletionMessageParam:
    if isinstance(message, SystemMessage):
        return ChatCompletionSystemMessageParam(content=message.content, role="system")
    elif isinstance(message, UserMessage):
        return ChatCompletionUserMessageParam(content=message.content, role="user")
    elif isinstance(message, AssistantMessage):
        return ChatCompletionAssistantMessageParam(content=message.content, role="assistant")
    elif isinstance(message, FakeAssistantMessage):
        return ChatCompletionAssistantMessageParam(content=message.content, role="assistant")
    raise Exception("Unknown message type.")


def conversation_to_api(conversation: Conversation) -> List[ChatCompletionMessageParam]:
    return [msg_to_api(msg) for msg in conversation]


def msg_from_response(response: ChatCompletion) -> AssistantMessage:
    try:
        content = response.choices[0].message.content or ""
    except Exception:
        content = ""

    usage = (
        Usage(
            completion_tokens=response.usage.completion_tokens,
            prompt_tokens=response.usage.prompt_tokens,
            total_tokens=response.usage.total_tokens,
        )
        if response.usage
        else None
    )

    return AssistantMessage(content=content, response=response.to_dict(), usage=usage, id=response.id)
