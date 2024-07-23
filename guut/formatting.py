import itertools
import math
import os
import re
from os.path import realpath
from pathlib import Path

from guut.execution import ExecutionResult
from guut.problem import CodeSnippet, Problem


def format_snippet(snippet: CodeSnippet, show_linenos: bool = False) -> str:
    content = add_line_numbers(snippet.content) if show_linenos else snippet.content
    return f"""{snippet.name}:
```{snippet.language or ''}
{content.rstrip()}
```"""


def format_snippet_raw(content: str, name: str, language: str | None = None, show_linenos: bool = False) -> str:
    content = add_line_numbers(content) if show_linenos else content
    return f"""{name}:
```{language or ''}
{content.rstrip()}
```"""


def remove_restarts_from_pdb_output(log: str) -> str:
    new_lines = itertools.takewhile(
        lambda line: "The program finished and will be restarted" not in line, log.splitlines()
    )
    return "\n".join(new_lines)


def shorten_paths(text: str, path_to_omit: str | Path) -> str:
    if isinstance(path_to_omit, Path):
        path_to_omit = str(path_to_omit)

    if not path_to_omit.endswith(os.sep):
        path_to_omit += os.sep

    return text.replace(path_to_omit, "")


def clean_traces(text: str, path_to_include: str | Path) -> str:
    new_lines = []
    in_trace = False  # whether the current line is in a trace
    drop_frame = False  # whether the current frame should be dropped

    for line in text.splitlines():
        ls = line.strip()

        # Start line
        if ls.startswith("Traceback"):
            in_trace = True
            drop_frame = False

        # Start of frame
        if in_trace and (matches := re.findall(r'File "([^"]*)"', ls)):
            drop_frame = str(path_to_include) not in realpath(matches[0])

        # End line
        if in_trace and re.findall(r"(Exception|Error)", ls):
            in_trace = False
            drop_frame = False

        if drop_frame:
            continue

        new_lines.append(line)

    return "\n".join(new_lines)


def limit_text(text: str, character_limit: int = 2000) -> str:
    num_chars = 0
    lines = []
    for line in text.splitlines():
        num_chars += len(line)
        if num_chars > character_limit:
            return "\n".join(lines) + "\n..."
        lines.append(line)
    return text


def indent_block(text: str, width: int = 4):
    def indent_line(line: str):
        if not line or line.isspace():
            return line
        else:
            return (" " * width) + line

    return "\n".join(indent_line(line) for line in text.splitlines())


def add_line_numbers(code: str):
    lines = code.splitlines()
    digits = math.floor(math.log10(len(lines))) + 1
    format_str = "{:0" + str(digits) + "d}"

    def add_line_number(line: str, number: int):
        if not line or line.isspace():
            return format_str.format(number)
        else:
            return f"{format_str.format(number)}  {line}"

    return "\n".join(add_line_number(line, i + 1) for i, line in enumerate(lines))


def extract_code_block(response: str, language: str) -> str:
    taking_lines = False
    code_lines = []

    for line in response.splitlines():
        if line.strip() == f"```{language}":
            taking_lines = True
            continue

        if taking_lines and line.strip() == "```":
            break

        if taking_lines:
            code_lines.append(line)

    return "\n".join(code_lines)


def format_execution_results(
    test_result_correct: ExecutionResult,
    test_result_buggy: ExecutionResult,
    debugger_result_correct: ExecutionResult | None = None,
    debugger_result_buggy: ExecutionResult | None = None,
) -> str:
    text = []

    test_correct_out = shorten_paths(test_result_correct.output, test_result_correct.cwd)
    test_correct_out = limit_text(test_correct_out, 1500)
    test_correct_out = format_snippet_raw("Test on correct version", test_correct_out)
    text.append(test_correct_out)
    if test_result_correct.timeout:
        text.append("The test was cancelled due to a timeout.")
    elif test_result_correct.exitcode != 0:
        text.append(f"The test exited with exitcode {test_result_correct.exitcode}.")
    text.append("")

    test_buggy_out = shorten_paths(test_result_buggy.output, test_result_buggy.cwd)
    test_buggy_out = limit_text(test_buggy_out, 1500)
    test_buggy_out = format_snippet_raw("Test on buggy version", test_buggy_out)
    text.append(test_buggy_out)
    if test_result_buggy.timeout:
        text.append("The test was cancelled due to a timeout.")
    elif test_result_buggy.exitcode != 0:
        text.append(f"The test exited with exitcode {test_result_buggy.exitcode}.")
    text.append("")

    if debugger_result_correct:
        debugger_correct_out = clean_traces(debugger_result_correct.output, debugger_result_correct.cwd)
        debugger_correct_out = shorten_paths(debugger_correct_out, debugger_result_correct.cwd)
        debugger_correct_out = limit_text(debugger_correct_out, 1500)
        debugger_correct_out = format_snippet_raw("Debugger on correct version", debugger_correct_out)
        text.append(debugger_correct_out)
        text.append("")

    if debugger_result_buggy:
        debugger_buggy_out = clean_traces(debugger_result_buggy.output, debugger_result_buggy.cwd)
        debugger_buggy_out = shorten_paths(debugger_buggy_out, debugger_result_buggy.cwd)
        debugger_buggy_out = limit_text(debugger_buggy_out, 1500)
        debugger_buggy_out = format_snippet_raw("debugger on buggy version", debugger_buggy_out)
        text.append(debugger_buggy_out)
        text.append("")

    return "\n".join(text).strip()


def format_problem(problem: Problem) -> str:
    snippets = [format_snippet(problem.class_under_test(), show_linenos=True)]
    snippets += [
        format_snippet(snippet, show_linenos=False) for snippet in [*problem.dependencies(), problem.mutant_diff()]
    ]
    return "\n\n".join(snippets)
