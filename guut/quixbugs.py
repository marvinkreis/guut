import errno
import itertools
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from shutil import copyfile
from subprocess import run
from tempfile import TemporaryDirectory
from typing import Iterable, List, Literal, override

from guut.config import config
from guut.execution import PythonExecutor
from guut.parsing import parse_uncalled_python_tests
from guut.problem import (
    ExecutionResult,
    ExperimentResult,
    Problem,
    ProblemDescription,
    TestResult,
    TextFile,
    ValidationResult,
)
from guut.prompts import PromptCollection, default_prompts


@dataclass
class QuixbugsProblemDescription(ProblemDescription):
    name: str

    def format(self) -> str:
        return f"{self.type}_{self.name}"


class QuixbugsProblem(Problem):
    def __init__(
        self,
        name: str,
        quixbugs_path: Path | None = None,
        python_interpreter: Path | None = None,
    ):
        self.name = name
        if quixbugs_path is None:
            quixbugs_path = Path(config.quixbugs_path)
        if python_interpreter is None:
            python_interpreter = Path(config.python_interpreter)
        self.quixbugs_path = quixbugs_path
        self.executor = PythonExecutor(python_interpreter=python_interpreter)

    @override
    def class_under_test(self) -> TextFile:
        return TextFile(
            content=self.construct_normalized_code(use_mutant=False), name=self.filename(), language="python"
        )

    @override
    def dependencies(self) -> Iterable[TextFile]:
        node_path = self.quixbugs_path / "python_programs" / "node.py"
        if self.is_graph_problem():
            return [TextFile(content=node_path.read_text(), name=node_path.name, language="python")]
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
                    include_files=code_dir.relevant_paths,
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
        for path in [self.correct_file(), self.buggy_file(), *self.dependencies_paths()]:
            if not path.is_file():
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(path))

    @staticmethod
    @override
    def get_type() -> str:
        return "quixbugs"

    @override
    def get_default_prompts(self) -> PromptCollection:
        return default_prompts

    def get_description(self) -> QuixbugsProblemDescription:
        return QuixbugsProblemDescription(type=self.get_type(), name=self.name)

    def filename(self) -> str:
        return f"{self.name}.py"

    def correct_file(self) -> Path:
        return self.quixbugs_path / "correct_python_programs" / self.filename()

    def buggy_file(self) -> Path:
        return self.quixbugs_path / "python_programs" / self.filename()

    def dependencies_paths(self) -> List[Path]:
        node_path = self.quixbugs_path / "python_programs" / "node.py"
        return [node_path] if self.is_graph_problem() else []

    def is_graph_problem(self) -> bool:
        """Check if the QuixBugs program is a graph problem. They depend on node.py but don't import it."""
        return self.name in [
            "breadth_first_search",
            "depth_first_search",
            "detect_cycle",
            "minimum_spanning_tree",
            "reverse_linked_list",
            "shortest_path_length",
            "shortest_path_lengths",
            "shortest_paths",
            "topological_ordering",
        ]

    def extract_code(self, use_mutant: bool = False) -> str:
        path = self.buggy_file() if use_mutant else self.correct_file()

        lines = itertools.takewhile(lambda line: '"""' not in line, path.read_text().splitlines())

        return "\n".join(lines).strip()

    def extract_comment(self) -> str:
        code = self.buggy_file().read_text()

        comment_lines = itertools.dropwhile(lambda line: '"""' not in line, code.splitlines())

        return "\n".join(comment_lines).strip()

    def construct_normalized_code(self, use_mutant: bool = False) -> str:
        # return f"{self.extract_code(use_mutant)}"
        return f"{self.extract_comment()}\n\n{self.extract_code(use_mutant)}"

    def compute_mutant_diff(self, reverse: bool = False) -> str:
        correct_code = self.construct_normalized_code(use_mutant=False)
        buggy_code = self.construct_normalized_code(use_mutant=True)

        with TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)

            correct_file = temp_path / f"{self.name}.py"
            correct_file.write_text(correct_code.strip() + "\n")
            buggy_file = temp_path / "mutant" / f"{self.name}_mutant.py"
            buggy_file.parent.mkdir()
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
        relevant_paths: List[Path]

    @contextmanager
    def prepare_code_dir(self, code: str, use_mutant: Literal["no", "yes", "insert"]):
        with TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            relevant_paths = []

            # copy program under test
            put_path = temp_path / self.filename()
            relevant_paths.append(put_path)
            if use_mutant in ["no", "insert"]:
                # copy regular program
                put_path.write_text(self.construct_normalized_code(use_mutant=False))
            elif use_mutant == "yes":
                # copy mutant
                put_path.write_text(self.construct_normalized_code(use_mutant=True))

            # copy dependencies
            for dep in self.dependencies_paths():
                dep_path = temp_path / dep.name
                relevant_paths.append(dep_path)
                copyfile(dep, dep_path)

            # create mutant directory if requested
            if use_mutant == "insert":
                mutant_path = temp_path / "mutant"
                mutant_path.mkdir()

                # copy mutant
                mutant_put_path = mutant_path / self.filename()
                mutant_put_path.write_text(self.construct_normalized_code(use_mutant=True))
                relevant_paths.append(mutant_put_path)

                # copy dependencies
                for dep in self.dependencies_paths():
                    dep_path = mutant_path / dep.name
                    relevant_paths.append(dep_path)
                    copyfile(dep, dep_path)

            # write test
            test_path = temp_path / "test.py"
            relevant_paths.append(test_path)
            test_path.write_text(code)

            yield QuixbugsProblem.CodeDir(
                root_path=temp_path, cut_path=put_path, test_path=test_path, relevant_paths=relevant_paths
            )


def list_problems(quixbugs_path: Path | None = None) -> List[str]:
    if quixbugs_path is None:
        quixbugs_path = Path(config.quixbugs_path)

    # List all buggy programs
    programs = [f for f in (quixbugs_path / "python_programs").iterdir() if f.is_file()]

    # Exclude tests
    programs = [f for f in programs if "test" not in f.stem]

    # Exclude dependencies
    programs = [f for f in programs if "node.py" not in f.name]

    return [program.stem for program in programs]
