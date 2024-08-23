from typing import Any, List


def fill_array(item: Any, count: int, array: List[Any] = []) -> List[Any]:
    """Fills an array with items until the item count is reached."""
    while len(array) < count:
        array.append(item)
    return array
