import pickle
from pathlib import Path
from typing import List, cast, override
from urllib.parse import unquote, urlparse

from guut.llm import AssistantMessage, Conversation, LLMEndpoint, Role


class ReplayLLMEndpoint(LLMEndpoint):
    def __init__(self, replay_messages: List[AssistantMessage], delegate: LLMEndpoint | None = None):
        self.replay_messages = replay_messages
        self.delegate = delegate

    @staticmethod
    def from_conversation(replay_conversation: Conversation, delegate: LLMEndpoint | None = None):
        replay_messages = [msg for msg in replay_conversation if msg.role == Role.ASSISTANT]
        return ReplayLLMEndpoint(replay_messages, delegate)

    @staticmethod
    def from_pickled_conversation(pickled_replay_conversation: Path | str, delegate: LLMEndpoint | None = None):
        if isinstance(pickled_replay_conversation, str):
            pickled_replay_conversation = unquote(urlparse(pickled_replay_conversation).path)

        bytes = Path(pickled_replay_conversation).read_bytes()
        replay_conversation = cast(Conversation, pickle.loads(bytes))
        return ReplayLLMEndpoint.from_conversation(replay_conversation, delegate)

    @staticmethod
    def from_raw_messages(raw_replay_messages: List[str], delegate: LLMEndpoint | None = None):
        replay_messages = [AssistantMessage(msg) for msg in raw_replay_messages]
        return ReplayLLMEndpoint(replay_messages, delegate)

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        if self.replay_messages:
            msg = self.replay_messages[0]
            self.replay_messages = self.replay_messages[1:]
            return msg

        if self.delegate:
            return self.delegate.complete(conversation, stop=stop, **kwargs)
        else:
            raise Exception("No more messages to replay.")

    def drop_messages(self, count: int):
        self.replay_messages = self.replay_messages[:-count]
