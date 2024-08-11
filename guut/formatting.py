import math
import os
import re
from os.path import realpath
from pathlib import Path

from guut.execution import ExecutionResult
from guut.problem import Problem
from guut.utils.pipe import p


def format_markdown_code_block(content: str, language: str | None = None, show_linenos: bool = False) -> str:
    content = add_line_numbers(content) if show_linenos else content
    return f"""```{language or ''}
{content.rstrip()}
```"""


def shorten_paths(text: str, path_to_omit: str | Path) -> str:
    if isinstance(path_to_omit, Path):
        path_to_omit = str(path_to_omit)

    if not path_to_omit.endswith(os.sep):
        path_to_omit += os.sep

    return text.replace(path_to_omit, "")


def shorten_stack_trace(stack_trace: str, path_to_include: str | Path) -> str:
    if isinstance(path_to_include, Path):
        path_to_include = str(path_to_include)

    new_lines = []
    in_trace = False  # whether the current line is in a trace
    drop_frame = False  # whether the current frame should be dropped

    for line in stack_trace.splitlines():
        line = line.strip()

        # Start line
        if line.startswith("Traceback"):
            in_trace = True
            drop_frame = False

        # Start of frame
        if in_trace and (matches := re.findall(r'File "([^"]*)"', line)):
            drop_frame = path_to_include not in realpath(matches[0])

        # End line
        if in_trace and re.findall(r"(Exception|Error)", line):
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
        num_chars += len(line) + 1
        if num_chars > character_limit:
            return "\n".join(lines) + "\n..."
        lines.append(line)
    return text


def indent_text(text: str, width: int = 4):
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
    code_block_started = False
    code_lines = []

    for line in response.splitlines():
        if line.strip() == f"```{language}":
            code_block_started = True
            continue

        if code_block_started and line.strip() == "```":
            break

        if code_block_started:
            code_lines.append(line)

    return "\n".join(code_lines)


def format_task(problem: Problem) -> str:
    cut = problem.class_under_test()
    cut_formatted = f"{cut.name}:\n{format_markdown_code_block(cut.content, show_linenos=True)}"
    deps_formatted = [
        f"{snippet.name}:\n{format_markdown_code_block(snippet.content, show_linenos=False)}"
        for snippet in problem.dependencies()
    ]
    diff_formatted = f"Mutant Diff:\n{format_markdown_code_block(problem.mutant_diff().content, show_linenos=False)}"
    return f"{cut_formatted}\n\n{''.join(dep + '\n\n' for dep in deps_formatted)}{diff_formatted}\n\n"


def format_execution_results(
    test_result_correct: ExecutionResult,
    test_result_buggy: ExecutionResult,
    debugger_result_correct: ExecutionResult | None = None,
    debugger_result_buggy: ExecutionResult | None = None,
) -> str:
    text = []

    text.append(
        p(test_result_correct.output)
        | (shorten_paths, test_result_correct.cwd)
        | (limit_text, 1500)
        | format_markdown_code_block
        | p.format("Test on correct code:\n{p}")
        | p.when(test_result_correct.timeout, p.format("{p}\nThe test was cancelled due to a timeout."))
        | p.when(
            test_result_correct.exitcode != 0,
            p.format("{p}\nThe test exited with exitcode {}.", test_result_correct.exitcode),
        )
        | p.format("{p}\n")
        | p
    )

    text.append(
        p(test_result_buggy.output)
        | (shorten_paths, test_result_buggy.cwd)
        | (limit_text, 1500)
        | format_markdown_code_block
        | p.format("Test on mutant:\n{p}")
        | p.when(test_result_buggy.timeout, p.format("{p}\nThe test was cancelled due to a timeout."))
        | p.when(
            test_result_buggy.exitcode != 0,
            p.format("{p}\nThe test exited with exitcode {}.", test_result_buggy.exitcode),
        )
        | p.format("{p}\n")
        | p
    )

    if debugger_result_correct:
        text.append(
            p(debugger_result_correct.output)
            | (shorten_stack_trace, debugger_result_correct.cwd)
            | (shorten_paths, debugger_result_correct.cwd)
            | (limit_text, 1500)
            | format_markdown_code_block
            | "Debugger on correct code:\n{}\n".format
            | p
        )

    if debugger_result_buggy:
        text.append(
            p(debugger_result_buggy.output)
            | (shorten_stack_trace, debugger_result_buggy.cwd)
            | (shorten_paths, debugger_result_buggy.cwd)
            | (limit_text, 1500)
            | format_markdown_code_block
            | "Debugger on mutant:\n{}\n".format
            | p
        )

    return "\n".join(text).strip()
