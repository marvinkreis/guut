from pathlib import Path
from typing import Iterable, Literal, override

from guut.execution import ExecutionResult
from guut.problem import Problem, ProblemDescription, TextFile, ValidationResult


class DummyProblem(Problem):
    @override
    def name(self) -> str:
        return "dummy_problem"

    @override
    def class_under_test(self) -> TextFile:
        return TextFile("", "dummy.py", "python")

    @override
    def dependencies(self) -> Iterable[TextFile]:
        return []

    @override
    def mutant_diff(self, reverse: bool = False) -> str:
        return ""

    @override
    def run_code(self, code: str, use_mutant: Literal["no", "yes", "insert"]) -> ExecutionResult:
        return ExecutionResult(target=Path("."), args=[], cwd=Path("."), input="", output="")

    @override
    def run_debugger(
        self, code: str, debugger_script: str, use_mutant: Literal["no", "yes", "insert"]
    ) -> ExecutionResult:
        return ExecutionResult(target=Path("."), args=[], cwd=Path("."), input="", output="")

    @override
    def validate(self):
        pass

    @override
    def validate_code(self, code: str) -> ValidationResult:
        return ValidationResult(True)

    @staticmethod
    @override
    def list_problems() -> Iterable[ProblemDescription]:
        return [ProblemDescription("dummy_problem", lambda: DummyProblem())]
