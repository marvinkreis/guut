import shutil
from pathlib import Path

import click


@click.command()
@click.argument("in_dir", nargs=1, type=click.Path(exists=True, file_okay=False), required=True)
@click.argument("out_dir", nargs=1, type=click.Path(exists=False, file_okay=False), required=True)
def collect_tests(in_dir: str, out_dir: str):
    out_path = Path(out_dir)
    out_path.mkdir(exist_ok=True)

    for path_str in Path(in_dir).rglob("test.py"):
        test_path = Path(path_str)
        shutil.copyfile(test_path, out_path / f"{test_path.parent.name}.py")


collect_tests()
