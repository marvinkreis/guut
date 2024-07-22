from pathlib import Path
import os

from guut.llm import UserMessage, Message, FakeAssistantMessage

prompts_path = Path(__file__).parent.parent / 'prompts'


class LongInstructions:
    def __init__(self):
        self.content = (prompts_path / 'long_instructions').read_text()

    def message(self) -> [Message]:
        return UserMessage(self.content)


class ShortInstructions:
    def __init__(self):
        self.content = (prompts_path / 'short_instructions').read_text()

    def message(self) -> [Message]:
        return UserMessage(self.content)


class FewShotExample01:
    def __init__(self):
        example_dir = prompts_path / 'example01'
        self.paths = sorted(example_dir / path for path in os.listdir(example_dir))

    @staticmethod
    def _path_to_msg(path: Path):
        if 'assistant' in path.name:
            return FakeAssistantMessage(path.read_text())
        else:
            return UserMessage(path.read_text())

    def messages(self):
        return [FewShotExample01._path_to_msg(path) for path in self.paths]


stop_words = [
    'Experiment Results:',
    'Experiment Result:',
    'Experiment Output:',
    'Experiment Outputs',
    '<DEBUGGING_DONE>'
]
