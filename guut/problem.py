from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Iterable

from guut.execution import ExecutionResult, ExperimentResult


@dataclass
class ProblemDescription:
    name: str
    constructor: Callable[[], "Problem"]


@dataclass
class TextFile:
    content: str
    name: str
    language: str | None = None


class Problem(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def class_under_test(self) -> TextFile:
        pass

    @abstractmethod
    def dependencies(self) -> Iterable[TextFile]:
        pass

    @abstractmethod
    def mutant_diff(self, reverse: bool = False) -> str:
        pass

    @abstractmethod
    def run_test(self, code: str, use_mutant: bool) -> ExecutionResult:
        pass

    @abstractmethod
    def run_debugger(self, code: str, debugger_script: str, use_mutant: bool) -> ExecutionResult:
        pass

    def run_experiment(self, code: str, debugger_script: str | None) -> ExperimentResult:
        if debugger_script:
            return ExperimentResult(
                test_correct=self.run_test(code, use_mutant=False),
                test_mutant=self.run_test(code, use_mutant=True),
                debug_correct=self.run_debugger(code, debugger_script, use_mutant=False),
                debug_mutant=self.run_debugger(code, debugger_script, use_mutant=True),
            )
        else:
            return ExperimentResult(
                test_correct=self.run_test(code, use_mutant=False), test_mutant=self.run_test(code, use_mutant=True)
            )

    @abstractmethod
    def validate(self):
        pass

    @staticmethod
    @abstractmethod
    def list_problems() -> Iterable[ProblemDescription]:
        pass
