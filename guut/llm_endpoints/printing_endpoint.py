from typing import override

from llama_cpp.llama_cache import List

from guut.formatting import format_message_pretty
from guut.llm import AssistantMessage, Conversation, LLMEndpoint, Message, Role


class PrintingLLMEndpoint(LLMEndpoint):
    def __init__(self, delegate: LLMEndpoint):
        self.delegate = delegate

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        for msg in self.get_new_messages(conversation):
            print(format_message_pretty(msg))

        response = self.delegate.complete(conversation, stop=stop, **kwargs)
        print(format_message_pretty(response))
        return response

    def get_new_messages(self, conversation: Conversation) -> List[Message]:
        messages_before = []
        for msg in conversation:
            if msg.role == Role.ASSISTANT:
                messages_before = []
            else:
                messages_before.append(msg)
        return messages_before
