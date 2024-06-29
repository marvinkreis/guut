from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Callable, Tuple

from guut.execution import ExecutionResult

type ProblemDescription = Tuple[str, Callable[[], 'Problem']]


@dataclass
class CodeSnippet:
    content: str
    name: str
    language: str = None


class Problem(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def class_under_test(self) -> CodeSnippet:
        pass

    @abstractmethod
    def dependencies(self) -> Iterable[CodeSnippet]:
        pass

    @abstractmethod
    def mutant_diff(self, reverse: bool = False) -> CodeSnippet:
        pass

    @abstractmethod
    def run_test(self, code: str, use_mutant: bool) -> ExecutionResult:
        pass

    @abstractmethod
    def run_debugger(self, code: str, debugger_script: str, use_mutant: bool) -> ExecutionResult:
        pass

    @abstractmethod
    def validate(self):
        pass

    @staticmethod
    @abstractmethod
    def list_problems() -> Iterable[ProblemDescription]:
        pass
