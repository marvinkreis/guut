import itertools
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import copyfile
from subprocess import run
from tempfile import TemporaryDirectory
from typing import List

from execution import run_debugger, run_script, ExecutionResult
from formatting import Snippet, format_code_context, format_code, shorten_paths

QUIXBUGS_PATH = Path(os.environ['QUIXBUGS_PATH'])
NODE_PATH = QUIXBUGS_PATH / 'python_programs' / 'node.py'


@dataclass
class Problem:
    name: str

    def get_correct_file(self) -> Path:
        return QUIXBUGS_PATH / 'correct_python_programs' / f'{self.name}.py'

    def get_buggy_file(self) -> Path:
        return QUIXBUGS_PATH / 'python_programs' / f'{self.name}.py'

    def get_file(self, buggy_version: bool = False) -> Path:
        if buggy_version:
            return self.get_buggy_file()
        else:
            return self.get_correct_file()

    def is_graph_problem(self) -> bool:
        """Check if the QuixBugs program is a graph problem. They depend on node.py but don't import it."""
        return self.name in ['breadth_first_search', 'depth_first_search', 'detect_cycle', 'minimum_spanning_tree',
                             'reverse_linked_list', 'shortest_path_length', 'shortest_path_lengths', 'shortest_paths',
                             'topological_ordering']

    def extract_code(self, buggy_version: bool = False) -> str:
        code = self.get_file(buggy_version=buggy_version).read_text()

        code_lines = itertools.takewhile(
            lambda line: '"""' not in line,
            code.splitlines(keepends=True))

        return ''.join(code_lines).strip() + '\n'

    def extract_comment(self) -> str:
        code = self.get_buggy_file().read_text()

        comment_lines = itertools.dropwhile(
            lambda line: '"""' not in line,
            code.splitlines(keepends=True))

        return ''.join(comment_lines).strip() + '\n'

    def compute_diff(self) -> str:
        correct_code = self.construct_normalized_code(buggy_version=False)
        buggy_code = self.construct_normalized_code(buggy_version=True)

        with TemporaryDirectory() as tempdir:
            correct_file = Path(tempdir) / f'{self.name}.py'
            correct_file.write_text(correct_code.strip() + '\n')
            buggy_file = Path(tempdir) / f'{self.name}_mutant.py'
            buggy_file.write_text(buggy_code.strip() + '\n')

            # Can't use check=True here, because --no-index implies --exit-code, which exits with 1 if the files differ
            result = run(['git', 'diff', '--no-index', '--', correct_file.name, buggy_file.name],
                         cwd=tempdir, capture_output=True, timeout=2)
            return result.stdout.decode()

    def construct_normalized_code(self, buggy_version: bool = False) -> str:
        return self.extract_comment() + self.extract_code(buggy_version)

    def get_dependencies(self) -> List[Path]:
        if self.is_graph_problem():
            return [Path(NODE_PATH)]
        else:
            return []

    def validate(self) -> bool:
        for path in [self.get_correct_file(), self.get_buggy_file(), *self.get_dependencies()]:
            if not path.is_file():
                print(f"Couldn't find file '{path}'.")
                return False
        return True


def list_problems() -> List[Problem]:
    # List all buggy programs
    programs = [f for f in (QUIXBUGS_PATH / 'python_programs').iterdir() if f.is_file()]

    # Exclude tests
    programs = [f for f in programs if 'test' not in f.stem]

    # Exclude dependencies
    programs = [f for f in programs if 'node.py' not in f.name]

    return [Problem(program.stem) for program in programs]


def run_debugger_on_problem(problem, test_code: str, debugger_script: List[str], buggy_version=False) -> ExecutionResult:
    with TemporaryDirectory() as tempdir:
        # write test file
        test_path = Path(tempdir) / 'test.py'
        test_path.write_text(test_code)

        # copy program under test
        put_path = Path(tempdir) / problem.get_file(buggy_version=buggy_version).name
        put_path.write_text(problem.construct_normalized_code(buggy_version=buggy_version))

        # copy dependencies
        for dep in problem.get_dependencies():
            copyfile(dep, Path(tempdir) / dep.name)

        # run
        result = run_debugger(test_path, debugger_script, cwd=Path(tempdir))
        return result


def run_test_on_problem(problem, test_code: str, stdin: str = None, buggy_version=False) -> ExecutionResult:
    with TemporaryDirectory() as tempdir:
        # write test file
        test_path = Path(tempdir) / 'test.py'
        test_path.write_text(test_code)

        # copy program under test
        put_path = Path(tempdir) / problem.get_file(buggy_version=buggy_version).name
        put_path.write_text(problem.construct_normalized_code(buggy_version=buggy_version))

        # copy dependencies
        for dep in problem.get_dependencies():
            copyfile(dep, Path(tempdir) / dep.name)

        # run
        return run_script(test_path, stdin=stdin, cwd=Path(tempdir))


def format_problem_context(problem: Problem) -> str:
    snippets = [Snippet(problem.get_correct_file().name,
                        problem.construct_normalized_code(buggy_version=False),
                        linenos=True)]

    for path in problem.get_dependencies():
        snippets.append(Snippet(path.name, path.read_text()))

    return format_code_context(snippets)


def main() -> None:
    if len(sys.argv) < 2:
        # List available problems
        for problem in list_problems():
            print(problem.name)
    else:
        # Print selected problem
        problem = Problem(sys.argv[1])
        if problem.validate():
            print(format_problem_context(problem))
            print(format_code(Snippet('Bug Diff', problem.compute_diff())))


if __name__ == '__main__':
    main()
