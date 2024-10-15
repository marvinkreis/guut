import dataclasses
import json
import os
import re
from datetime import datetime
from json import JSONEncoder
from pathlib import Path
from typing import List

from guut.cosmic_ray import MultipleMutantsResult, MutantSpec
from guut.formatting import format_conversation_pretty
from guut.llm import Conversation, LLMEndpoint, Message
from guut.loop import Result
from guut.problem import Problem
from guut.prompts import Template

FILENAME_REPLACEMENET_REGEX = r"[^0-9a-zA-Z]+"


def write_result_dir(result: Result, out_dir: Path | str | None = None):
    if not out_dir:
        out_dir = os.getcwd()

    result_dir = Path(out_dir) / clean_filename(result.long_id)
    result_dir.mkdir(exist_ok=True, parents=True)
    write_result(result, out_dir=result_dir)

    if test := result.get_killing_test():
        write_test(test.code, out_dir=result_dir)

    write_conversation(result.conversation, out_dir=result_dir)


def write_multiple_mutants_result_dir(result: MultipleMutantsResult, out_dir: Path):
    if not out_dir:
        out_dir = os.getcwd()

    result_path = Path(out_dir) / "result.json"
    with result_path.open("w") as file:
        json.dump(result, file, cls=CustomJSONEncoder)

    tests_path = Path(out_dir) / "tests"
    tests_path.mkdir()
    for name, test in result.tests:
        write_test(test.code, out_dir=tests_path, test_name=f"{clean_filename(name)}.py")


def write_result(result: Result, out_dir: Path | str | None = None):
    if not out_dir:
        out_dir = os.getcwd()

    result_path = Path(out_dir) / "result.json"
    with result_path.open("w") as file:
        json.dump(result, file, cls=CustomJSONEncoder)


def write_test(test_code: str, out_dir: Path | str | None = None, test_name: str = "test.py"):
    if not out_dir:
        out_dir = os.getcwd()

    result_path = Path(out_dir) / test_name
    result_path.write_text(test_code)


def write_conversation(conversation: Conversation, out_dir: Path | str | None = None):
    if not out_dir:
        out_dir = os.getcwd()

    json_path = Path(out_dir) / "conversation.json"
    md_path = Path(out_dir) / "conversation.md"
    txt_path = Path(out_dir) / "conversation.txt"

    with json_path.open("w") as file:
        json.dump(conversation.to_json(), file)
    md_path.write_text("\n\n".join(msg.content for msg in conversation))
    txt_path.write_text(format_conversation_pretty(conversation))


def clean_filename(name: str) -> str:
    return re.sub(FILENAME_REPLACEMENET_REGEX, "_", name)


class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Problem):
            return o.get_description()
        elif isinstance(o, LLMEndpoint):
            return o.get_description()
        if isinstance(o, Conversation):
            return o.to_json()
        if isinstance(o, Message):
            return o.to_json()
        if isinstance(o, Template):
            return o.path
        elif isinstance(o, datetime):
            return o.timestamp()
        elif isinstance(o, Path):
            return str(o)
        elif dataclasses.is_dataclass(o):
            json = {}
            for field in dataclasses.fields(o):
                json[field.name] = getattr(o, field.name)
            return json
        else:
            return super().default(o)


class StatusHelper:
    def __init__(self, name: str):
        self.name = name
        self.dir = Path("/tmp/guut") / name
        self.dir.mkdir(exist_ok=True, parents=True)

    def write_status(self, num_mutants: int, num_queued: int, num_alive: int, num_killed: int):
        (self.dir / "status.txt").write_text(
            f"total: {num_mutants}\nqueued: {num_queued}\nalive: {num_alive}\nkilled: {num_killed}"
        )

    def write_queue(self, queue: List[MutantSpec]):
        with (self.dir / "status.txt").open("w") as f:
            json.dump(queue, f, cls=CustomJSONEncoder)

    def write_problem_info(self, problem: Problem):
        (self.dir / "current_cut.py").write_text(problem.class_under_test().content)
        (self.dir / "current_diff.diff").write_text(problem.mutant_diff())
