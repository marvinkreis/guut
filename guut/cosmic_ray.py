import errno
import os
import shutil
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from typing import Any, Iterable, List, Literal, Tuple, override

from cosmic_ray.mutating import apply_mutation, mutate_code
from cosmic_ray.plugins import get_operator

from guut.config import config
from guut.execution import PythonExecutor
from guut.parsing import parse_uncalled_python_tests
from guut.problem import (
    ExecutionResult,
    ExperimentResult,
    Problem,
    ProblemDescription,
    Test,
    TestResult,
    TextFile,
    ValidationResult,
)
from guut.prompts import PromptCollection, default_prompts

MutantOp = Any


# TODO: add python interpreter?
@dataclass
class CosmicRayProblemDescription(ProblemDescription):
    module_path: Path
    target_path: str
    mutant_op: str
    occurrence: int

    def format(self):
        return f"{self.module_path.name}_{self.target_path}_{self.mutant_op}_{self.occurrence}"


class CosmicRayProblem(Problem):
    def __init__(
        self,
        module_path: Path,
        target_path: str,
        mutant_op_name: str,
        occurrence: int,
        python_interpreter: Path | None = None,
    ):
        self.module_path = module_path
        self.module_name = module_path.name
        self.target_path = target_path
        self.mutant_op_name = mutant_op_name
        self.occurrence = occurrence
        self.python_interpreter = python_interpreter or config.python_interpreter
        self.executor = PythonExecutor(python_interpreter=self.python_interpreter)
        self.mutant_op = get_operator(mutant_op_name)()

    @override
    def class_under_test(self) -> TextFile:
        content = self.full_module_path().read_text().rstrip() + "\n"
        name = str(Path(self.module_name) / self.target_path)
        return TextFile(content=content, name=name, language="python")

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
        return self.compute_mutant_diff(reverse=reverse)

    @override
    def run_code(
        self, code: str, use_mutant: Literal["no", "yes", "insert"], collect_coverage: bool
    ) -> ExecutionResult:
        with self.prepare_code_dir(code=code, use_mutant=use_mutant) as code_dir:
            if collect_coverage:
                return self.executor.run_script_with_coverage(
                    target=code_dir.test_path,
                    cut_file=code_dir.cut_path,
                    cwd=code_dir.root_path,
                )
            else:
                return self.executor.run_script(target=code_dir.test_path, cwd=code_dir.root_path)

    @override
    def run_debugger(
        self, code: str, debugger_script: str, use_mutant: Literal["no", "yes", "insert"]
    ) -> ExecutionResult:
        with self.prepare_code_dir(code=code, use_mutant=use_mutant) as code_dir:
            return self.executor.run_debugger(code_dir.test_path, debugger_script, cwd=code_dir.root_path)

    @override
    def run_test(self, code: str, collect_coverage: bool) -> TestResult:
        for test_name in parse_uncalled_python_tests(code):
            code += f"\n{test_name}()"  # add test call
        return super().run_test(code, collect_coverage=collect_coverage)

    @override
    def run_experiment(
        self,
        code: str,
        debugger_script: str | None,
        collect_coverage: bool,
    ) -> ExperimentResult:
        for test_name in parse_uncalled_python_tests(code):
            code += f"\n{test_name}()"  # add test call
        return super().run_experiment(
            code,
            debugger_script=debugger_script,
            collect_coverage=collect_coverage,
        )

    @override
    def validate_self(self):
        if not self.module_path.is_dir():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(self.module_path))
        if not self.full_module_path().is_file():
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(self.full_module_path()))

    @staticmethod
    @override
    def get_type() -> str:
        return "cosmic-ray"

    @override
    def get_default_prompts(self) -> PromptCollection:
        return default_prompts

    def full_module_path(self) -> Path:
        return self.module_path / self.target_path

    def get_description(self) -> CosmicRayProblemDescription:
        return CosmicRayProblemDescription(
            type=self.get_type(),
            module_path=self.module_path,
            target_path=self.target_path,
            mutant_op=self.mutant_op_name,
            occurrence=self.occurrence,
        )

    def compute_mutant_diff(self, reverse: bool = False) -> str:
        correct_code = self.class_under_test().content

        buggy_code = mutate_code(code=correct_code.encode(), operator=self.mutant_op, occurrence=self.occurrence)
        if buggy_code is None:
            raise Exception("Couldn't mutate code.")

        with TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)

            correct_file = temp_path / self.module_name / self.target_path
            correct_file.parent.mkdir(parents=True, exist_ok=True)
            correct_file.write_text(correct_code.strip() + "\n")
            buggy_file = temp_path / "mutant" / self.module_name / self.target_path
            buggy_file.parent.mkdir(parents=True, exist_ok=True)
            buggy_file.write_text(buggy_code.strip() + "\n")

            left_file = buggy_file if reverse else correct_file
            right_file = correct_file if reverse else buggy_file

            # Can't use check=True here, because --no-index implies --exit-code, which exits with 1 if the files differ
            result = run(
                [
                    "git",
                    "diff",
                    "-U5",
                    "--no-index",
                    "--",
                    str(left_file.relative_to(temp_path)),
                    str(right_file.relative_to(temp_path)),
                ],
                cwd=tempdir,
                capture_output=True,
                timeout=2,
            )
            return result.stdout.decode()

    def validate_code(self, code: str) -> ValidationResult:
        try:
            compile(code, "test.py", "exec")
            return ValidationResult(True)
        except SyntaxError:
            pass

        result = self.run_code(code, use_mutant="no", collect_coverage=False)
        return ValidationResult(False, cwd=result.cwd, error=result.output)

    @dataclass
    class CodeDir:
        root_path: Path
        cut_path: Path
        test_path: Path

    @contextmanager
    def prepare_code_dir(self, code: str, use_mutant: Literal["no", "yes", "insert"]):
        with TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            correct_module_path = temp_path / self.module_name
            mutant_module_path = temp_path / "mutant" / self.module_name

            # copy program under test
            shutil.copytree(self.module_path, correct_module_path, dirs_exist_ok=True, symlinks=True)
            if use_mutant == "yes":
                apply_mutation(
                    module_path=correct_module_path / self.target_path,
                    operator=self.mutant_op,
                    occurrence=self.occurrence,
                )

            # create mutant directory if requested
            if use_mutant == "insert":
                mutant_module_path.mkdir(parents=True, exist_ok=True)
                shutil.copytree(self.module_path, mutant_module_path, dirs_exist_ok=True, symlinks=True)
                apply_mutation(
                    module_path=mutant_module_path / self.target_path,
                    operator=self.mutant_op,
                    occurrence=self.occurrence,
                )

            # write test
            test_path = temp_path / "test.py"
            test_path.write_text(code)

            cut_path = correct_module_path / self.target_path
            yield CosmicRayProblem.CodeDir(root_path=temp_path, cut_path=cut_path, test_path=test_path)


@dataclass
class MutantSpec:
    target_path: str
    mutant_op: str
    occurrence: int
    line_start: int
    line_end: int


def list_mutants(session_file: Path) -> List[MutantSpec]:
    conn = sqlite3.connect(session_file)
    cursor = conn.cursor()
    cursor.execute("select module_path, operator_name, occurrence, start_pos_row, end_pos_row from mutation_specs;")
    return [MutantSpec(*args) for args in cursor.fetchall()]


@dataclass
class KilledMutant:
    spec: MutantSpec
    test_result: TestResult | None


@dataclass
class MultipleMutantsResult:
    mutants: List[MutantSpec]
    alive_mutants: List[MutantSpec]
    killed_mutants: List[KilledMutant]
    tests: List[Tuple[str, Test]]
