import itertools
import math
import os
from pathlib import Path

from guut.execution import ExecutionResult


def format_code_block(name: str, content: str, linenos: bool = False, language: str = '') -> str:
    content = add_line_numbers(content) if linenos else content
    return f'''{name}:
```{language}
{content.rstrip()}
```'''


def remove_restarts_from_pdb_output(log: str) -> str:
    new_lines = itertools.takewhile(
        lambda line: 'The program finished and will be restarted' not in line,
        log.splitlines())
    return '\n'.join(new_lines)


def shorten_paths(log: str, path_to_omit: str | Path) -> str:
    if isinstance(path_to_omit, Path):
        path_to_omit = str(path_to_omit)

    if not path_to_omit.endswith(os.sep):
        path_to_omit += os.sep

    return log.replace(path_to_omit, '')


def limit_text(text: str, character_limit: int = 2000) -> str:
    num_chars = 0
    lines = []
    for line in text.splitlines():
        num_chars += len(line)
        if num_chars > character_limit:
            return '\n'.join(lines) + '\n...'
        lines.append(line)
    return text


def indent_block(text: str, width: int = 4):
    def indent_line(line: str):
        if not line or line.isspace():
            return line
        else:
            return (' ' * width) + line

    return '\n'.join(indent_line(line) for line in text.splitlines())


def add_line_numbers(code: str):
    lines = code.splitlines()
    digits = math.floor(math.log10(len(lines))) + 1
    format_str = '{:0' + str(digits) + 'd}'

    def add_line_number(line: str, number: int):
        if not line or line.isspace():
            return format_str.format(number)
        else:
            return f'{format_str.format(number)}  {line}'

    return '\n'.join(add_line_number(line, i+1) for i, line in enumerate(lines))


def extract_code_block(response: str, language: str) -> str:
    taking_lines = False
    code_lines = []

    for line in response.splitlines():
        if line.strip() == f'```{language}':
            taking_lines = True
            continue

        if taking_lines and line.strip() == '```':
            break

        if taking_lines:
            code_lines.append(line)

    return '\n'.join(code_lines)


def format_execution_results(test_result_correct: ExecutionResult,
                             test_result_buggy: ExecutionResult,
                             debugger_result_correct: ExecutionResult = None,
                             debugger_result_buggy: ExecutionResult = None) -> str:
    text = []

    test_correct_out = limit_text(test_result_correct.output, 1500)
    test_correct_out = format_code_block('Test on correct version', test_correct_out)
    text.append(test_correct_out)
    if test_result_correct.timeout:
        text.append('The test was cancelled due to a timeout.')
    elif test_result_correct.exitcode != 0:
        text.append(f'The test exited with exitcode {test_result_correct.exitcode}.')
    text.append('')

    test_buggy_out = limit_text(test_result_buggy.output, 1500)
    test_buggy_out = format_code_block('Test on buggy version', test_buggy_out)
    text.append(test_buggy_out)
    if test_result_buggy.timeout:
        text.append('The test was cancelled due to a timeout.')
    elif test_result_buggy.exitcode != 0:
        text.append(f'The test exited with exitcode {test_result_buggy.exitcode}.')
    text.append('')

    if debugger_result_correct:
        debugger_correct_out = limit_text(debugger_result_correct.output, 1500)
        debugger_correct_out = format_code_block('Debugger on correct version', debugger_correct_out)
        text.append(debugger_correct_out)
        text.append('')

    if debugger_result_buggy:
        debugger_buggy_out = limit_text(debugger_result_buggy.output, 1500)
        debugger_buggy_out = format_code_block('Debugger on buggy version', debugger_buggy_out)
        text.append(debugger_buggy_out)
        text.append('')

    return '\n'.join(text).strip()
