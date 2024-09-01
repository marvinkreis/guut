from datetime import datetime
from typing import Any

from guut.formatting import format_timestamp
from guut.llm import LLMEndpoint
from guut.loop import Result
from guut.problem import Problem


def print_result(result: Result):
    pass


def write_result(result: Result):
    pass


def json_converter(element: Any):
    if isinstance(element, Problem):
        return f"{element.type}:{element.name()}"
    elif isinstance(element, LLMEndpoint):
        return element.get_description()
    elif isinstance(element, datetime):
        return format_timestamp(element)
