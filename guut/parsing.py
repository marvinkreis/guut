import ast
import re
from dataclasses import dataclass
from typing import List, Tuple


def parse_python_test_name(code: str) -> str | None:
    module = ast.parse(code, "test.py", "exec")

    funs = [node for node in module.body if isinstance(node, ast.FunctionDef)]
    tests = [fun for fun in funs if fun.name.startswith("test")]

    if tests:
        return tests[0].name
    elif funs:
        return funs[0].name
    else:
        return None


@dataclass
class MarkdownBlock:
    language: str | None
    code: str


MARKDOWN_CODE_BLOCK_REGEX = re.compile(r"^```([A-Za-z]+)?\s*$")


def extract_markdown_code_blocks(response: str) -> List[MarkdownBlock]:
    blocks = []

    in_code_block = False
    current_language = None
    current_lines = []

    for line in response.splitlines():
        if match := re.match(MARKDOWN_CODE_BLOCK_REGEX, line):
            if in_code_block:
                blocks.append(MarkdownBlock(current_language, "\n".join(current_lines)))
                in_code_block = False
                current_language = None
                current_lines = []

                # if a language name is detected, start a new markdown block from the closing delimiters
                if language := match.group(1):
                    in_code_block = True
                    current_language = language
            else:
                in_code_block = True
                current_language = match.group(1)
        elif in_code_block:
            current_lines.append(line)

    return blocks


def detect_markdown_code_blocks(response: str) -> List[Tuple[str, bool]]:
    in_code_block = False
    lines = []
    for line in response.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            lines.append((line, True))
        else:
            lines.append((line, in_code_block))
    return lines
