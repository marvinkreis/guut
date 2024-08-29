import errno
import itertools
import os
import sys
from functools import partial
from pathlib import Path
from shutil import copyfile
from subprocess import run
from tempfile import TemporaryDirectory
from typing import Iterable, List, Literal, override

from guut.execution import ExecutionResult, run_debugger, run_script
from guut.formatting import format_problem
from guut.problem import Problem, ProblemDescription, TextFile, ValidationResult

QUIXBUGS_PATH = Path(os.environ["QUIXBUGS_PATH"])
NODE_PATH = QUIXBUGS_PATH / "python_programs" / "node.py"


class QuixbugsProblem(Problem):
    _name: str

    def __init__(self, name: str):
        self._name = name

    @override
    def name(self) -> str:
        return self._name

    @override
    def class_under_test(self) -> TextFile:
        return TextFile(
            content=self.construct_normalized_code(use_mutant=False), name=self.filename(), language="python"
        )

    @override
    def dependencies(self) -> Iterable[TextFile]:
        if self.is_graph_problem():
            return [TextFile(content=NODE_PATH.read_text(), name=NODE_PATH.name, language="python")]
        return []

    @override
    def mutant_diff(self, reverse: bool = False) -> str:
        return self.compute_mutant_diff(reverse=reverse)

    @override
    def run_code(self, code: str, use_mutant: Literal["no", "yes", "insert"]) -> ExecutionResult:
        with TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)

            # copy program under test
            put_path = temp_path / self.filename()
            if use_mutant in ["no", "insert"]:
                # copy regular program
                put_path.write_text(self.construct_normalized_code(use_mutant=False))
            elif use_mutant == "yes":
                # copy mutant
                put_path.write_text(self.construct_normalized_code(use_mutant=True))

            # copy dependencies
            for dep in self.dependencies_paths():
                copyfile(dep, temp_path / dep.name)

            # create mutant directory if requested
            if use_mutant == "insert":
                mutant_path = temp_path / "mutant"
                mutant_path.mkdir()

                # copy mutant
                mutant_put_path = mutant_path / self.filename()
                mutant_put_path.write_text(self.construct_normalized_code(use_mutant=True))

                # copy dependencies
                for dep in self.dependencies_paths():
                    copyfile(dep, temp_path / dep.name)

            # write test
            test_path = temp_path / "test.py"
            test_path.write_text(code)

            return run_script(test_path, cwd=temp_path)

    @override
    def run_debugger(
        self, code: str, debugger_script: str, use_mutant: Literal["no", "yes", "insert"]
    ) -> ExecutionResult:
        with TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)

            # copy program under test
            put_path = temp_path / self.filename()
            if use_mutant in ["no", "insert"]:
                # copy regular program
                put_path.write_text(self.construct_normalized_code(use_mutant=False))
            elif use_mutant == "yes":
                # copy mutant
                put_path.write_text(self.construct_normalized_code(use_mutant=True))

            # copy dependencies
            for dep in self.dependencies_paths():
                copyfile(dep, temp_path / dep.name)

            # create mutant directory if requested
            if use_mutant == "insert":
                mutant_path = temp_path / "mutant"
                mutant_path.mkdir()

                # copy mutant
                mutant_put_path = mutant_path / self.filename()
                mutant_put_path.write_text(self.construct_normalized_code(use_mutant=True))

                # copy dependencies
                for dep in self.dependencies_paths():
                    copyfile(dep, temp_path / dep.name)

            # write test
            test_path = temp_path / "test.py"
            test_path.write_text(code)

            return run_debugger(test_path, debugger_script, cwd=Path(tempdir))

    @override
    def validate(self):
        for path in [self.correct_file(), self.buggy_file(), *self.dependencies_paths()]:
            if not path.is_file():
                path.read_text()
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(path))

    @staticmethod
    @override
    def list_problems() -> List[ProblemDescription]:
        # List all buggy programs
        programs = [f for f in (QUIXBUGS_PATH / "python_programs").iterdir() if f.is_file()]

        # Exclude tests
        programs = [f for f in programs if "test" not in f.stem]

        # Exclude dependencies
        programs = [f for f in programs if "node.py" not in f.name]

        return [
            ProblemDescription(name=program.stem, constructor=partial(QuixbugsProblem, program.stem))
            for program in programs
        ]

    def filename(self) -> str:
        return f"{self.name()}.py"

    def correct_file(self) -> Path:
        return QUIXBUGS_PATH / "correct_python_programs" / f"{self.name()}.py"

    def buggy_file(self) -> Path:
        return QUIXBUGS_PATH / "python_programs" / f"{self.name()}.py"

    def dependencies_paths(self) -> List[Path]:
        return [NODE_PATH] if self.is_graph_problem() else []

    def is_graph_problem(self) -> bool:
        """Check if the QuixBugs program is a graph problem. They depend on node.py but don't import it."""
        return self.name() in [
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
            correct_file = Path(tempdir) / f"{self.name()}.py"
            correct_file.write_text(correct_code.strip() + "\n")
            buggy_file = Path(tempdir) / f"{self.name()}_mutant.py"
            buggy_file.write_text(buggy_code.strip() + "\n")

            left_file = buggy_file if reverse else correct_file
            right_file = correct_file if reverse else buggy_file

            # Can't use check=True here, because --no-index implies --exit-code, which exits with 1 if the files differ
            result = run(
                ["git", "diff", "--no-index", "--", left_file.name, right_file.name],
                cwd=tempdir,
                capture_output=True,
                timeout=2,
            )
            return result.stdout.decode().replace(f"{self.name()}_mutant.py", f"{self.name()}.py")

    def validate_code(self, code: str) -> ValidationResult:
        try:
            compile(code, "test.py", "exec")
            return ValidationResult(True)
        except SyntaxError as e:
            return ValidationResult(False, e.msg)


def main() -> None:
    if len(sys.argv) < 2:
        # List available problems
        for description in QuixbugsProblem.list_problems():
            print(description.name)
    else:
        # Print selected problem
        problem = QuixbugsProblem(sys.argv[1])
        problem.validate()
        print(format_problem(problem))


if __name__ == "__main__":
    main()
