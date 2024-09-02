from dataclasses import dataclass
from pathlib import Path
from typing import List, override

from guut.llm import AssistantMessage, Conversation, EndpointDescription, LLMEndpoint, Role


class ReplayLLMEndpoint(LLMEndpoint):
    def __init__(
        self,
        replay_messages: List[AssistantMessage],
        delegate: LLMEndpoint | None = None,
        index: int | None = None,
        path: str | None = None,
        replay_file: Path | None = None,
    ):
        self.replay_messages = [msg.copy() for msg in replay_messages]
        for msg in replay_messages:
            msg.tag = None

        self.delegate = delegate
        self.path = path
        self.replay_file = replay_file

    @override
    def get_description(self) -> EndpointDescription:
        return ReplayEndpointDescription("openai", replay_file=self.replay_file)

    @staticmethod
    def from_conversation(
        replay_conversation: Conversation,
        delegate: LLMEndpoint | None = None,
        index: int | None = None,
        path: str | None = None,
        replay_file: Path | None = None,
    ):
        replay_messages = [msg.copy() for msg in replay_conversation if msg.role == Role.ASSISTANT]
        return ReplayLLMEndpoint(replay_messages, delegate, path=path, replay_file=replay_file)

    @staticmethod
    def from_raw_messages(
        raw_replay_messages: List[str],
        delegate: LLMEndpoint | None = None,
        index: int | None = None,
        path: str | None = None,
        replay_file: Path | None = None,
    ):
        replay_messages = [AssistantMessage(msg) for msg in raw_replay_messages]
        return ReplayLLMEndpoint(replay_messages, delegate, path=path, replay_file=replay_file)

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        if self.replay_messages:
            msg = self.replay_messages[0]
            self.replay_messages = self.replay_messages[1:]
            return msg

        if self.delegate:
            return self.delegate.complete(conversation, stop=stop, **kwargs)
        else:
            raise StopIteration("No more messages to replay.")


@dataclass
class ReplayEndpointDescription(EndpointDescription):
    replay_file: Path | None
