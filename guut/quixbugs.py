import errno
import itertools
import os
import sys
from pathlib import Path
from shutil import copyfile
from subprocess import run
from tempfile import TemporaryDirectory
from typing import List, Iterable, override

from guut.execution import run_debugger, run_script, ExecutionResult
from guut.problem import Problem, CodeSnippet

QUIXBUGS_PATH = Path(os.environ['QUIXBUGS_PATH'])
NODE_PATH = QUIXBUGS_PATH / 'python_programs' / 'node.py'


class QuixbugsProblem(Problem):
    name: str

    def __init__(self, name: str):
        self.name = name

    @override
    def class_under_test(self) -> CodeSnippet:
        return CodeSnippet(
            content=self.construct_normalized_code(use_mutant=False),
            name=self.filename(),
            language='python')

    @override
    def dependencies(self) -> Iterable[CodeSnippet]:
        if self.is_graph_problem():
            return [CodeSnippet(
                content=NODE_PATH.read_text(),
                name=NODE_PATH.name,
                language='python')]
        return []

    @override
    def mutant_diff(self, reverse: bool = False) -> CodeSnippet:
        return CodeSnippet(
            content=self.compute_mutant_diff(reverse=reverse),
            name='Mutant Diff',
            language='diff')

    @override
    def run_test(self, code: str, use_mutant: bool = False) -> ExecutionResult:
        with TemporaryDirectory() as tempdir:
            # copy program under test
            put_path = Path(tempdir) / self.filename()
            put_path.write_text(self.construct_normalized_code(use_mutant=use_mutant))

            # copy dependencies
            for dep in self.dependencies_paths():
                copyfile(dep, Path(tempdir) / dep.name)

            # write test
            test_path = Path(tempdir) / 'test.py'
            test_path.write_text(code)

            return run_script(test_path, cwd=Path(tempdir))

    @override
    def run_debugger(self, code: str, debugger_script: str, use_mutant: bool = False) -> ExecutionResult:
        with TemporaryDirectory() as tempdir:
            # copy program under test
            put_path = Path(tempdir) / self.filename()
            put_path.write_text(self.construct_normalized_code(use_mutant=use_mutant))

            # copy dependencies
            for dep in self.dependencies_paths():
                copyfile(dep, Path(tempdir) / dep.name)

            # write test
            test_path = Path(tempdir) / 'test.py'
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
    def list_problems() -> List[Problem]:
        # List all buggy programs
        programs = [f for f in (QUIXBUGS_PATH / 'python_programs').iterdir() if f.is_file()]

        # Exclude tests
        programs = [f for f in programs if 'test' not in f.stem]

        # Exclude dependencies
        programs = [f for f in programs if 'node.py' not in f.name]

        return [QuixbugsProblem(program.stem) for program in programs]

    def filename(self) -> str:
        return f'{self.name}.py'

    def correct_file(self) -> Path:
        return QUIXBUGS_PATH / 'correct_python_programs' / f'{self.name}.py'

    def buggy_file(self) -> Path:
        return QUIXBUGS_PATH / 'python_programs' / f'{self.name}.py'

    def dependencies_paths(self) -> List[Path]:
        return [NODE_PATH] if self.is_graph_problem() else []

    def is_graph_problem(self) -> bool:
        """Check if the QuixBugs program is a graph problem. They depend on node.py but don't import it."""
        return self.name in ['breadth_first_search', 'depth_first_search', 'detect_cycle', 'minimum_spanning_tree',
                             'reverse_linked_list', 'shortest_path_length', 'shortest_path_lengths', 'shortest_paths',
                             'topological_ordering']

    def extract_code(self, use_mutant: bool = False) -> str:
        path = self.buggy_file() if use_mutant else self.correct_file()

        lines = itertools.takewhile(
            lambda line: '"""' not in line,
            path.read_text().splitlines())

        return '\n'.join(lines).strip() #+ '\n'

    def extract_comment(self) -> str:
        code = self.buggy_file().read_text()

        comment_lines = itertools.dropwhile(
            lambda line: '"""' not in line,
            code.splitlines())

        return '\n'.join(comment_lines).strip() #+ '\n'

    def construct_normalized_code(self, use_mutant: bool = False) -> str:
        return self.extract_comment() + self.extract_code(use_mutant)

    def compute_mutant_diff(self, reverse: bool = False) -> str:
        correct_code = self.construct_normalized_code(use_mutant=False)
        buggy_code = self.construct_normalized_code(use_mutant=True)

        with TemporaryDirectory() as tempdir:
            correct_file = Path(tempdir) / f'{self.name}.py'
            correct_file.write_text(correct_code.strip() + '\n')
            buggy_file = Path(tempdir) / f'{self.name}_mutant.py'
            buggy_file.write_text(buggy_code.strip() + '\n')

            left_file = buggy_file if reverse else correct_file
            right_file = correct_file if reverse else buggy_file

            # Can't use check=True here, because --no-index implies --exit-code, which exits with 1 if the files differ
            result = run(['git', 'diff', '--no-index', '--', left_file.name, right_file.name],
                         cwd=tempdir, capture_output=True, timeout=2)
            return result.stdout.decode().replace(f'{self.name}_mutant.py', f'{self.name}.py')


def main() -> None:
    if len(sys.argv) < 2:
        # List available problems
        for name, constructor in Problem.list_problems():
            print(name)
    else:
        # Print selected problem
        problem = QuixbugsProblem(sys.argv[1])
        problem.validate()
        # print(format_problem(problem))


if __name__ == '__main__':
    main()
