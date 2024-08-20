import json
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
    FakeAssistantMessage,
    LLMEndpoint,
    Message,
    SystemMessage,
    Usage,
    UserMessage,
)


class OpenAIEndpoint(LLMEndpoint):
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        messages = conversation_to_api(conversation)
        stop = stop or kwargs.get("stop")
        log_data = {
            "args": kwargs,
            "stop": stop,
            "conversation": conversation.to_json(),
        }
        logger.info(f"Requesting completion for conversation {json.dumps(log_data)}")
        response = self.client.chat.completions.create(model=self.model, messages=messages, stop=stop, **kwargs)
        return msg_from_response(response)


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
    content = response.choices[0].message.content

    if not content or not response.usage:
        raise Exception("Incomplete OpenAI response")

    usage = Usage(
        completion_tokens=response.usage.completion_tokens,
        prompt_tokens=response.usage.prompt_tokens,
        total_tokens=response.usage.total_tokens,
    )
    return AssistantMessage(content, response, usage)