import itertools
import math
from dataclasses import dataclass
from typing import List


@dataclass
class Snippet:
    name: str
    content: str
    linenos: bool = False


def format_code(snippet: Snippet, language='python') -> str:
    if snippet.linenos:
        lines = snippet.content.splitlines(keepends=True)
        digits = math.floor(math.log10(len(lines))) + 1
        format_str = '{:0' + str(digits) + 'd}'
        content = ''.join(f'{format_str.format(i+1)}   {line}' for i, line in enumerate(lines))
    else:
        content = snippet.content

    return f'''{snippet.name}:
```{language}
{content}
```
'''


def format_code_context(snippets: List[Snippet]) -> str:
    return '\n'.join(format_code(snippet) for snippet in snippets)


def remove_restarts_from_pdb_output(log: str) -> str:
    new_lines = itertools.takewhile(
        lambda line: 'The program finished and will be restarted' not in line,
        log.splitlines(keepends=True))
    return ''.join(new_lines)


def shorten_paths(log: str, path_to_omit: str) -> str:
    if not path_to_omit.endswith('/'):
        path_to_omit += '/'
    return log.replace(path_to_omit, '')
