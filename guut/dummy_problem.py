from pathlib import Path
from typing import Iterable, List, Literal, override

from guut.problem import ExecutionResult, Problem, TextFile, ValidationResult


class DummyProblem(Problem):
    @override
    def __init__(self):
        pass

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
    def allowed_languages(self) -> List[str]:
        return ["python"]

    @override
    def allowed_debugger_languages(self) -> List[str]:
        return ["pdb", "debugger"]

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
    def validate_self(self):
        pass

    @override
    def validate_code(self, code: str) -> ValidationResult:
        return ValidationResult(True)

    @staticmethod
    @override
    def list_problems() -> Iterable[str]:
        return ["dummy_problem"]
