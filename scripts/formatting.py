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


def format_diff(diff: str) -> str:
    return format_code(Snippet('Bug Diff', diff), language='diff')
