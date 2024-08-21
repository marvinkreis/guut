from typing import List


def count_names(names: List[str]):
    """Counts the appearances of names in a list."""
    counts = {}
    for name in names:
        count = counts.get(name) or 0
        counts[name] = count + 1
    return counts
