import os
from pathlib import Path

from guut.llm import FakeAssistantMessage, Message, SystemMessage, UserMessage

prompts_path = Path(__file__).parent.parent / "prompts"


class SystemInstructions:
    def __init__(self):
        self.content = (prompts_path / "system_instructions.md").read_text()

    def message(self) -> Message:
        return SystemMessage(self.content)


class LongInstructions:
    def __init__(self):
        self.content = (prompts_path / "long_instructions.md").read_text()

    def message(self, problem_str: str) -> Message:
        return UserMessage(self.content.replace("{problem}", problem_str))


class LongInstructions2:
    def __init__(self):
        self.content = (prompts_path / "long_instructions_2.md").read_text()

    def message(self, problem_str: str) -> Message:
        return UserMessage(self.content.replace("{problem}", problem_str))


class LongInstructions3:
    def __init__(self):
        self.content = (prompts_path / "long_instructions_3.md").read_text()

    def message(self, problem_str: str) -> Message:
        return UserMessage(self.content.replace("{problem}", problem_str))


class ShortInstructions:
    def __init__(self):
        self.content = (prompts_path / "short_instructions.md").read_text()

    def message(self) -> Message:
        return UserMessage(self.content)


class FewShotExample01:
    def __init__(self):
        example_dir = prompts_path / "example01"
        self.paths = sorted(example_dir / path for path in os.listdir(example_dir))

    @staticmethod
    def _path_to_msg(path: Path):
        if "assistant" in path.name:
            return FakeAssistantMessage(path.read_text())
        else:
            return UserMessage(path.read_text())

    def messages(self):
        return [FewShotExample01._path_to_msg(path) for path in self.paths]


stop_words = ["Experiment Result", "Experiment Output", "<DEBUGGING_DONE>"]
