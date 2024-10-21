import re

import pytest

from guut.formatting import limit_cut


@pytest.mark.parametrize(
    argnames=["line", "ellipses", "contains_lines", "doesnt_contain_lines"],
    argvalues=[
        (1, 1, [1, 101, 1000], [1001]),
        (550, 1, [1, 101, 1000], [1001]),
        (551, 1, [1, 101, 1000], [1001]),
        (552, 2, [1, 100, 1000, 1001], [101]),
        (900, 2, [1, 100, 450, 1349], [101, 449, 1350]),
        (1900, 1, [1, 100, 1101, 2000], [101, 1100]),
        (1551, 1, [1, 100, 1101, 2000], [101, 1100]),
        (1550, 2, [1, 100, 1100, 1999], [1099, 2000]),
    ],
)
def test_limit_cut(line, ellipses, contains_lines, doesnt_contain_lines):
    text = "\n".join(f"{[n]}" for n in range(1, 2001))
    limited_text = limit_cut(text, line)

    print(limited_text)
    assert len(re.findall(r"<truncated>", limited_text, re.MULTILINE)) == ellipses
    assert len(limited_text.splitlines()) == (1000 + ellipses)

    for l in contains_lines:
        assert f"[{l}]" in limited_text
    for l in doesnt_contain_lines:
        assert f"[{l}]" not in limited_text
