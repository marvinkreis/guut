import pickle
from collections import deque
from pathlib import Path
from typing import Deque, List, cast, override

from guut.llm import AssistantMessage, Conversation, LLMEndpoint, Role


class ReplayLLMEndpoint(LLMEndpoint):
    def __init__(self, replay_messages: Deque[AssistantMessage]):
        self.replay_messages = replay_messages

    @staticmethod
    def from_conversation(replay_conversation: Conversation):
        replay_messages = deque([msg for msg in replay_conversation if msg.role == Role.ASSISTANT])
        return ReplayLLMEndpoint(replay_messages)

    @staticmethod
    def from_pickled_conversation(pickled_replay_conversation: Path):
        bytes = Path(pickled_replay_conversation).read_bytes()
        replay_conversation = cast(Conversation, pickle.loads(bytes))
        return ReplayLLMEndpoint.from_conversation(replay_conversation)

    @staticmethod
    def from_raw_messages(raw_replay_messages: List[str]):
        replay_messages = deque([AssistantMessage(msg) for msg in raw_replay_messages])
        return ReplayLLMEndpoint(replay_messages)

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        if len(self.replay_messages) == 0:
            raise Exception("No more messages to replay.")
        return self.replay_messages.popleft()
