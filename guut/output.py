import dataclasses
import json
import os
import re
from datetime import datetime
from json import JSONEncoder
from pathlib import Path

from guut.formatting import format_timestamp
from guut.llm import Conversation, LLMEndpoint, Message
from guut.loop import Result
from guut.problem import Problem
from guut.prompts import Template

FILENAME_REPLACEMENET_REGEX = r"[^0-9a-zA-Z]+"


def write_result_dir(result: Result, out_dir: Path | str | None = None):
    if not out_dir:
        out_dir = os.getcwd()

    result_dir = Path(out_dir) / clean_filename(result.id)
    result_dir.mkdir(exist_ok=True, parents=True)
    write_result(result, out_dir=result_dir)

    if test := result.get_killing_test():
        write_test(test.description.code, out_dir=result_dir)


def write_result(result: Result, out_dir: Path | str | None = None):
    if not out_dir:
        out_dir = os.getcwd()
    result_path = Path(out_dir) / "result.json"
    with result_path.open("w") as file:
        json.dump(result, file, cls=CustomJSONEncoder)


def write_test(test_code: str, out_dir: Path | str | None = None):
    if not out_dir:
        out_dir = os.getcwd()
    result_path = Path(out_dir) / "test.py"
    result_path.write_text(test_code)


def clean_filename(name: str) -> str:
    return re.sub(FILENAME_REPLACEMENET_REGEX, "_", name)


class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Problem):
            return {"type": o.get_type(), "description": o.description()}
        if isinstance(o, Conversation):
            return o.to_json()
        if isinstance(o, Message):
            return o.to_json()
        if isinstance(o, Template):
            return o.path
        elif isinstance(o, LLMEndpoint):
            return o.get_description()
        elif isinstance(o, datetime):
            return format_timestamp(o)
        elif isinstance(o, Path):
            return str(o)
        elif dataclasses.is_dataclass(o):
            json = {}
            for field in dataclasses.fields(o):
                json[field.name] = getattr(o, field.name)
            return json
        else:
            return super().default(o)
