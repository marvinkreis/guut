import json
import re
from pathlib import Path

import click


"""
Collects all final tests (and experiments) from a run,
that passed on the PUT.

Usage: ./script in_dir out_dir
- in_dir: result directory from guut
- out_dir: directory to be populated with the tests
"""


FILENAME_REPLACEMENET_REGEX = r"[^0-9a-zA-Z]+"


def clean_filename(name: str) -> str:
    return re.sub(FILENAME_REPLACEMENET_REGEX, "_", name)


@click.command()
@click.argument("in_dir", nargs=1, type=click.Path(exists=True, file_okay=False), required=True)
@click.argument("out_dir", nargs=1, type=click.Path(exists=False, file_okay=False), required=True)
def collect_all_valid_tests(in_dir: str, out_dir: str):
    out_path = Path(out_dir)
    out_path.mkdir(exist_ok=True)

    for path_str in Path(in_dir).rglob("result.json"):
        with Path(path_str).open("r") as f:
            data = json.load(f)
            for test in reversed(data["tests"]):
                if not test["result"]:
                    continue
                result = test["result"]["correct"]
                exitcode = result["exitcode"]
                if exitcode == 0:
                    filename = clean_filename(f"{data['id']}") + ".py"
                    Path(out_path / filename).write_text(test["code"])
                    break


collect_all_valid_tests()
