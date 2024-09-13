from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Literal


@dataclass
class TextFile:
    content: str
    name: str
    language: str | None = None


@dataclass
class ValidationResult:
    valid: bool
    error: str | None = None


@dataclass
class Coverage:
    covered_lines: List[int]
    missing_lines: List[int]
    raw: Any


@dataclass
class ExecutionResult:
    command: List[str]
    cwd: Path
    target: Path
    input: str

    output: str
    exitcode: int = 0
    timeout: bool = False
    coverage: Coverage | None = None


@dataclass
class AltExperimentResult:
    test_correct: ExecutionResult
    test_mutant: ExecutionResult
    debug_correct: ExecutionResult | None = None
    debug_mutant: ExecutionResult | None = None


@dataclass
class ExperimentResult:
    test: ExecutionResult
    debug: ExecutionResult | None = None


@dataclass
class TestResult:
    correct: ExecutionResult
    mutant: ExecutionResult


@dataclass
class ProblemDescription:
    type: str

    def format(self):
        return self.type


class Problem(ABC):
    @abstractmethod
    def __init__(self, args: str):
        pass

    @abstractmethod
    def class_under_test(self) -> TextFile:
        pass

    @abstractmethod
    def dependencies(self) -> Iterable[TextFile]:
        pass

    @abstractmethod
    def allowed_languages(self) -> Iterable[str]:
        pass

    @abstractmethod
    def allowed_debugger_languages(self) -> Iterable[str]:
        pass

    @abstractmethod
    def mutant_diff(self, reverse: bool = False) -> str:
        pass

    @abstractmethod
    def run_code(
        self, code: str, use_mutant: Literal["no", "yes", "insert"], collect_coverage: bool
    ) -> ExecutionResult:
        pass

    @abstractmethod
    def run_debugger(
        self, code: str, debugger_script: str, use_mutant: Literal["no", "yes", "insert"]
    ) -> ExecutionResult:
        pass

    def run_experiment(
        self, code: str, debugger_script: str | None, collect_coverage: bool, altexp: bool = False
    ) -> ExperimentResult | AltExperimentResult:
        if not altexp:
            return ExperimentResult(
                test=self.run_code(code, use_mutant="insert", collect_coverage=collect_coverage),
                debug=self.run_debugger(code, debugger_script, use_mutant="insert") if debugger_script else None,
            )
        else:
            return AltExperimentResult(
                test_correct=self.run_code(code, use_mutant="no", collect_coverage=collect_coverage),
                test_mutant=self.run_code(code, use_mutant="yes", collect_coverage=collect_coverage),
                debug_correct=self.run_debugger(code, debugger_script, use_mutant="no") if debugger_script else None,
                debug_mutant=self.run_debugger(code, debugger_script, use_mutant="yes") if debugger_script else None,
            )

    def run_test(self, code: str, collect_coverage: bool) -> TestResult:
        return TestResult(
            correct=self.run_code(code, use_mutant="no", collect_coverage=collect_coverage),
            mutant=self.run_code(code, use_mutant="yes", collect_coverage=collect_coverage),
        )

    @abstractmethod
    def validate_self(self):
        pass

    @abstractmethod
    def validate_code(self, code: str) -> ValidationResult:
        pass

    @abstractmethod
    def get_default_prompts(self) -> "PromptCollection":  # noqa: F821  # pyright: ignore
        pass

    @abstractmethod
    def get_description(self) -> ProblemDescription:
        pass

    @staticmethod
    def list_problems() -> Iterable[str]:
        return []

    @staticmethod
    @abstractmethod
    def get_type() -> str:
        pass
