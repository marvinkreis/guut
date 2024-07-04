from pathlib import Path

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
        self.paths = sorted(prompts_path.glob('example01__*__*'), key=lambda path: path.name)

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
