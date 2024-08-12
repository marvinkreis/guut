import json
import pickle
from collections import deque
from pathlib import Path
from typing import List, cast, override

from guut.llm import AssistantMessage, Conversation, LLMEndpoint, Role


class ReplayLLMEndpoint(LLMEndpoint):
    def __init__(self, replay_conversation: Conversation | str):
        if isinstance(replay_conversation, str):
            bytes = Path(replay_conversation).read_bytes()
            replay_conversation = cast(Conversation, pickle.loads(bytes))
        self.replay_messages = deque([msg for msg in replay_conversation if msg.role == Role.ASSISTANT])

    @override
    def complete(self, conversation: Conversation, stop: List[str] | None = None, **kwargs) -> AssistantMessage:
        if len(self.replay_messages) == 0:
            raise Exception("No more messages to replay.")
        return self.replay_messages.popleft()
