import math
import os
import re
from enum import Enum
from os.path import realpath
from pathlib import Path
from typing import List

from guut.execution import ExecutionResult
from guut.llm import AssistantMessage, Conversation, Message
from guut.problem import Problem


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


def limit_text(text: str, char_limit: int = 2000) -> str:
    num_chars = 0
    lines = []
    for line in text.splitlines():
        num_chars += len(line) + 1
        if num_chars > char_limit:
            return "\n".join(lines) + "\n<truncated>\n..."
        lines.append(line)
    return text


def wrap_text(text: str, width: int = 100) -> List[str]:
    lines = []
    for line in text.splitlines():
        if len(line) <= width:
            lines.append(line)
        else:
            num_chars = 0
            words = []
            for word in line.split(" "):
                if num_chars + len(word) > width:
                    if words:
                        lines.append(" ".join(words))
                        words = [word]
                        num_chars = len(word) + 1
                    else:
                        lines.append(word[:width])
                        words = [word[width:]]
                        num_chars = len(word[width:]) + 1
                else:
                    words.append(word)
                    num_chars += len(word) + 1
            if words:
                lines.append(" ".join(words))
    return lines


def wrap_in_box(text: str, width: int = 100, title: str = ""):
    if title:
        title = f" {title} "
    wrapped_text = wrap_text(text, width)
    boxed_text = "\n".join(f"│ {line.ljust(width)} │" for line in wrapped_text)
    return f"""╭─{title}{"─" * (width + 1 - len(title))}╮
{boxed_text}
╰{"─" * (width + 2)}╯"""


def pretty_conversation(conversastion: Conversation) -> str:
    return "\n".join(pretty_message(msg) for msg in conversastion)


def pretty_message(message: Message) -> str:
    title = []
    title.append(message.role.value)
    title.append(message.tag.value if isinstance(message.tag, Enum) else str(message.tag))
    if isinstance(message, AssistantMessage):
        if message.usage:
            title.append(f"({message.usage.prompt_tokens}, {message.usage.completion_tokens})")
        else:
            title.append("None")
    return wrap_in_box(message.content, title=", ".join(title))


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


def extract_code_block(response: str, language: str) -> str | None:
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

    return "\n".join(code_lines) if code_lines else None


def format_problem(problem: Problem) -> str:
    cut = problem.class_under_test()
    cut_formatted = f"{cut.name}:\n{format_markdown_code_block(cut.content, show_linenos=True)}"
    deps_formatted = [
        f"{snippet.name}:\n{format_markdown_code_block(snippet.content, show_linenos=False)}"
        for snippet in problem.dependencies()
    ]
    diff_formatted = f"Mutant Diff:\n{format_markdown_code_block(problem.mutant_diff(), show_linenos=False)}"
    return f"{cut_formatted}\n\n{''.join(dep + '\n\n' for dep in deps_formatted)}{diff_formatted}".strip()


def format_test_result(test_result: ExecutionResult, char_limit: int = 1500):
    text = test_result.output.rstrip()
    text = shorten_paths(text, test_result.cwd)
    text = limit_text(text, char_limit)
    return text


def format_debugger_result(debugger_result: ExecutionResult, char_limit: int = 1500):
    text = debugger_result.output.rstrip()
    text = shorten_stack_trace(text, debugger_result.cwd)
    text = shorten_paths(text, debugger_result.cwd)
    text = limit_text(text, char_limit)
    return text
