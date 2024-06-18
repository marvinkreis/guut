import itertools
import math
import os
from pathlib import Path


def format_code(name: str, content: str, linenos: bool = False, language: str = '') -> str:
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
