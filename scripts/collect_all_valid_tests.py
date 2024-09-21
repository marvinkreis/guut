import json
import re
from pathlib import Path

import click

FILENAME_REPLACEMENET_REGEX = r"[^0-9a-zA-Z]+"


def clean_filename(name: str) -> str:
    return re.sub(FILENAME_REPLACEMENET_REGEX, "_", name)


@click.command()
@click.argument("in_dir", nargs=1, type=click.Path(exists=True, file_okay=False), required=True)
@click.argument("out_dir", nargs=1, type=click.Path(exists=False, file_okay=False), required=True)
def collect_all_last_valid_tests(in_dir: str, out_dir: str):
    out_path = Path(out_dir)
    out_path.mkdir(exist_ok=True)

    for path_str in Path(in_dir).rglob("result.json"):
        with Path(path_str).open("r") as f:
            data = json.load(f)
            i = 1
            for test in data["tests"]:
                if not test["result"]:
                    continue
                result = test["result"]["correct"]
                exitcode = result["exitcode"]
                if exitcode == 0:
                    filename = clean_filename(f"{data["id"]}_{i:02d}") + ".py"
                    Path(out_path / filename).write_text(test["code"])
                    i += 1


collect_all_last_valid_tests()
