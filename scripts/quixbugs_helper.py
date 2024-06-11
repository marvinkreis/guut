#!/usr/bin/env python

import itertools
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from subprocess import Popen, PIPE
from tempfile import TemporaryDirectory
from typing import List
from shutil import copyfile
import math

from debugger_helper import run_debugger, shorten_paths


QUIXBUGS_PATH = Path(os.environ['QUIXBUGS_PATH'])
NODE_PATH = QUIXBUGS_PATH / 'python_programs' / 'node.py'


@dataclass
class Problem:
    name: str

    def get_correct_file(self) -> Path:
        return QUIXBUGS_PATH / 'correct_python_programs' / f'{self.name}.py'

    def get_buggy_file(self) -> Path:
        return QUIXBUGS_PATH / 'python_programs' / f'{self.name}.py'

    def is_graph_problem(self) -> bool:
        """Check if the QuixBugs program is a graph problem. They depend on node.py but don't import it."""
        return self.name in ['breadth_first_search', 'depth_first_search', 'detect_cycle', 'minimum_spanning_tree',
                             'reverse_linked_list', 'shortest_path_length', 'shortest_path_lengths', 'shortest_paths',
                             'topological_ordering']

    def get_dependencies(self) -> List[Path]:
        if self.is_graph_problem():
            return [Path(NODE_PATH)]
        else:
            return []

    def validate(self) -> bool:
        if not self.get_correct_file().is_file():
            print(f"Couldn't find file '{self.get_correct_file()}'.")
            return False
        if not self.get_buggy_file().is_file():
            print(f"Couldn't find file '{self.get_buggy_file()}'.")
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


def compute_diff(problem) -> str:
    correct_code = extract_code(problem.get_correct_file().read_text())
    buggy_code = extract_code(problem.get_buggy_file().read_text())

    with TemporaryDirectory() as tempdir:
        correct_file = Path(tempdir) / f'{problem.name}.py'
        correct_file.write_text(correct_code.strip() + '\n')
        buggy_file = Path(tempdir) / f'{problem.name}_mutant.py'
        buggy_file.write_text(buggy_code.strip() + '\n')

        process = Popen(['git', 'diff', '--no-index', '--', correct_file.name, buggy_file.name], stdout=PIPE, cwd=tempdir)
        (output, err) = process.communicate()
        exit_code = process.wait()
        return output.decode()


def extract_code(code: str) -> str:
    code_lines = itertools.takewhile(
        lambda line: '"""' not in line,
        code.splitlines(keepends=True))
    return ''.join(code_lines)


def extract_comment(code: str) -> str:
    comment_lines = itertools.dropwhile(
        lambda line: '"""' not in line,
        code.splitlines(keepends=True))
    return ''.join(comment_lines)


def construct_better_correct_file(problem: Problem) -> str:
    code = extract_code(problem.get_correct_file().read_text())

    # Extract comment from the buggy file, since the correct file comments are useless.
    comment = extract_comment(problem.get_buggy_file().read_text())

    return code + comment


def print_code_context(problem: Problem) -> None:
    print_code(problem.get_correct_file().name,
               construct_better_correct_file(problem),
               print_linenumbers=True)

    for path in problem.get_dependencies():
        print_code(path.name, path.read_text())


def print_diff(problem: Problem) -> None:
    diff = compute_diff(problem)
    print_code('Bug Diff', diff, language='diff')


def print_code(display_name, code, language='python', print_linenumbers=False) -> None:
    if print_linenumbers:
        lines = code.splitlines(keepends=True)
        digits = math.floor(math.log10(len(lines))) + 1
        format_str = '{:0' + str(digits) + 'd}'
        code = ''.join(f'{format_str.format(i+1)}|  {line}' for i, line in enumerate(lines))

    print(f'''{display_name}:
```{language}
{code}
```
''')


def run_debugger_on_problem(problem, test_code: str, debugger_script: List[str], use_buggy_version=False):
    with TemporaryDirectory() as tempdir:
        # write test file
        test_path = Path(tempdir) / 'test.py'
        test_path.write_text(test_code)

        # copy program under test
        if use_buggy_version:
            copyfile(problem.get_buggy_file(), Path(tempdir) / problem.get_buggy_file().name)
        else:
            copyfile(problem.get_correct_file(), Path(tempdir) / problem.get_correct_file().name)

        # copy dependencies
        for dep in problem.get_dependencies():
            copyfile(dep, Path(tempdir) / dep.name)

        # run
        output = run_debugger(test_path, debugger_script)
        return shorten_paths(output, tempdir)


# TODO: run_test_on_problem


def main() -> None:
    if len(sys.argv) < 2:
        # List available problems
        for problem in list_problems():
            print(problem.name)
    else:
        # Print selected problem
        problem = Problem(sys.argv[1])
        if problem.validate():
            print_code_context(problem)
            print_diff(problem)


if __name__ == '__main__':
    main()
