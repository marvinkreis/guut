import json
from typing import List, override

from llama_cpp import (
    ChatCompletionRequestAssistantMessage,
    ChatCompletionRequestMessage,
    ChatCompletionRequestSystemMessage,
    ChatCompletionRequestUserMessage,
    CreateChatCompletionResponse,
    Llama,
)
from loguru import logger

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


class LlamacppEndpoint(LLMEndpoint):
    def __init__(self, client: Llama):
        self.client = client

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
        response = self.client.create_chat_completion(messages=messages, stop=stop, **kwargs)
        return msg_from_response(response)  # pyright: ignore (create_chat_completion can also return an iterable)


def msg_to_api(message: Message) -> ChatCompletionRequestMessage:
    if isinstance(message, SystemMessage):
        return ChatCompletionRequestSystemMessage(content=message.content, role="system")
    elif isinstance(message, UserMessage):
        return ChatCompletionRequestUserMessage(content=message.content, role="user")
    elif isinstance(message, AssistantMessage):
        return ChatCompletionRequestAssistantMessage(content=message.content, role="assistant")
    elif isinstance(message, FakeAssistantMessage):
        return ChatCompletionRequestAssistantMessage(content=message.content, role="assistant")
    raise Exception("Unknown message type.")


def conversation_to_api(conversation: Conversation) -> List[ChatCompletionRequestMessage]:
    return [msg_to_api(msg) for msg in conversation]


def msg_from_response(response: CreateChatCompletionResponse) -> AssistantMessage:
    message = response["choices"][0]["message"]
    content = message.get("content")

    if not content or not response["usage"]:
        raise Exception("Incomplete OpenAI response")

    usage = Usage(
        completion_tokens=response["usage"]["completion_tokens"],
        prompt_tokens=response["usage"]["prompt_tokens"],
        total_tokens=response["usage"]["total_tokens"],
    )
    return AssistantMessage(content, response, usage)
