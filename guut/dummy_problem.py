from pathlib import Path
from typing import Iterable, List, Literal, override

from guut.problem import ExecutionResult, Problem, ProblemDescription, TextFile, ValidationResult
from guut.prompts import PromptCollection, default_prompts


class DummyProblem(Problem):
    @override
    def __init__(self):
        pass

    @override
    def get_description(self) -> ProblemDescription:
        return ProblemDescription("dummy_problem")

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
    def run_code(
        self, code: str, use_mutant: Literal["no", "yes", "insert"], collect_coverage: bool
    ) -> ExecutionResult:
        return ExecutionResult(target=Path("."), command=[], cwd=Path("."), input="", output="")

    @override
    def run_debugger(
        self, code: str, debugger_script: str, use_mutant: Literal["no", "yes", "insert"]
    ) -> ExecutionResult:
        return ExecutionResult(target=Path("."), command=[], cwd=Path("."), input="", output="")

    @override
    def validate_self(self):
        pass

    @override
    def validate_code(self, code: str) -> ValidationResult:
        return ValidationResult(True)

    @override
    @staticmethod
    def list_problems() -> Iterable[str]:
        return ["dummy_problem"]

    @override
    @staticmethod
    def get_type() -> str:
        return "dummy_problem"

    @override
    def get_default_prompts(self) -> PromptCollection:
        return default_prompts
