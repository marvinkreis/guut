import math
import os
import re
from datetime import datetime
from enum import Enum
from os.path import realpath
from pathlib import Path
from typing import List

from guut.llm import AssistantMessage, Conversation, Message
from guut.problem import ExecutionResult, Problem, TextFile, ValidationResult


def format_problem(problem: Problem) -> str:
    cut = problem.class_under_test()
    limited_numbered_cut = format_cut(problem)
    cut_formatted = format_markdown_code_block(
        limited_numbered_cut, language=cut.language, name=cut.name, show_linenos=False
    )
    deps_formatted = [
        format_markdown_code_block(snippet.content, language=snippet.language, name=snippet.name, show_linenos=False)
        for snippet in problem.dependencies()
    ]
    diff_formatted = format_markdown_code_block(
        problem.mutant_diff(), language="diff", name="mutant.diff", show_linenos=False
    )
    return f"{cut_formatted}\n\n{''.join(dep + '\n\n' for dep in deps_formatted)}{diff_formatted}".strip()


def format_markdown_code_block(
    content: str, language: str | None = None, name: str | None = None, show_linenos: bool = False
) -> str:
    header = " ".join([language or "", name or ""]).strip()
    content = add_line_numbers(content) if show_linenos else content
    return f"""```{header}
{content.rstrip()}
```"""


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
        sline = line.strip()

        # Start line
        if sline.startswith("Traceback") or sline.startswith("(Pdb) Traceback"):
            in_trace = True
            drop_frame = False

        # Start of frame
        if in_trace and (matches := re.findall(r'File "([^"]*)"', sline)):
            drop_frame = path_to_include not in realpath(matches[0])

        # End line
        if in_trace and re.findall(r"(Exception|Error)", sline):
            in_trace = False
            drop_frame = False

        if drop_frame:
            continue

        new_lines.append(line)

    return "\n".join(new_lines)


def limit_text(text: str, char_limit: int = 2000) -> str:
    if len(text) > char_limit:
        return text[:2000] + "<truncated>"
    else:
        return text


def limit_text_by_line(text: str, char_limit: int = 2000) -> str:
    num_chars = 0
    lines = []
    for line in text.splitlines():
        num_chars += len(line) + 1
        if num_chars > char_limit:
            return "\n".join(lines) + "\n<truncated>"
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


def wrap_text_in_box(text: str, width: int = 100, title: str = ""):
    if title:
        title = f" {title} "
    wrapped_text = wrap_text(text, width)
    boxed_text = "\n".join(f"│ {line.ljust(width)} │" for line in wrapped_text)
    return f"""┌─{title}{"─" * (width + 1 - len(title))}┐
{boxed_text}
└{"─" * (width + 2)}┘"""


def format_conversation_pretty(conversastion: Conversation) -> str:
    return "\n".join(format_message_pretty(msg) for msg in conversastion)


def format_message_pretty(message: Message) -> str:
    title = []
    title.append(message.role.value)
    title.append(message.tag.value if isinstance(message.tag, Enum) else str(message.tag))
    if isinstance(message, AssistantMessage):
        if message.usage:
            title.append(f"({message.usage.prompt_tokens}, {message.usage.completion_tokens})")
        else:
            title.append("None")
    return wrap_text_in_box(message.content, title=", ".join(title))


def format_execution_result(result: ExecutionResult, char_limit: int = 2500):
    text = result.output.rstrip()
    text = shorten_stack_trace(text, result.cwd)
    text = shorten_paths(text, result.cwd)
    text = limit_text(text, char_limit)
    if result.timeout:
        text = f"{text}\n<timeout>" if text else "<timeout>"
    return text


def format_validation_result(result: ValidationResult, char_limit: int = 2500):
    text = (result.error or "").rstrip()
    if result.cwd is not None:
        text = shorten_paths(text, result.cwd)
    text = limit_text(text, char_limit)
    return text


def format_timestamp(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def get_import_path(cut: TextFile) -> str:
    path = Path(cut.name)
    if path.name in ["__init__.py", "__main__.py"] and path.parent.name:
        return str(path.parent).replace(os.sep, ".")
    return str(path.parent / path.stem).replace(os.sep, ".")


def get_module_name(cut: TextFile) -> str:
    path = Path(cut.name)
    if path.name in ["__init__.py", "__main__.py"] and path.parent.name:
        return path.parent.name
    return path.stem


def format_cut(problem: Problem) -> str:
    cut = problem.class_under_test()
    numbered_cut = add_line_numbers(cut.content)
    mutant_line = problem.get_mutant_line()
    return limit_cut(numbered_cut, mutant_line or 0)


def limit_cut(content: str, around_line: int) -> str:
    """
    first 100 lines
    ...
    450 lines before the mutant
    mutant line
    449 lines after the mutant
    ...
    """
    lines = content.splitlines()
    num_lines = len(lines)

    if num_lines <= 1000:
        return content

    if around_line <= 551:
        return "\n".join(lines[:1000] + ["<truncated>"])

    elif around_line > num_lines - 450:
        return "\n".join(lines[:100] + ["<truncated>"] + lines[-900:])
    else:
        start_line = around_line - 450
        end_line = around_line + 449
        return "\n".join(lines[:100] + ["<truncated>"] + lines[(start_line - 1) : end_line] + ["<truncated>"])
