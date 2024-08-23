from typing import Any, List


def fill_array(item: Any, count: int, array: List[Any] | None = None) -> List[Any]:
    """Fills an array with items until the item count is reached."""
    array = array or []
    while len(array) < count:
        array.append(item)
    return array
