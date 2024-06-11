#!/usr/bin/env python

import inspect
import itertools
from pathlib import Path
from subprocess import run, TimeoutExpired
from typing import List

import debugger_wrapper


def run_debugger(target: Path, debugger_commands: List[str], cwd: Path = None) -> str:
    process_input = ''.join(command + '\n' for command in debugger_commands)
    process_command = ['python', inspect.getfile(debugger_wrapper), str(target)]

    try:
        result = run(process_command, input=process_input.encode(), cwd=cwd or target.parent,
                     check=True, capture_output=True, timeout=2)
        output = result.stdout
    except TimeoutExpired as e:
        output = e.stdout
        pass

    return output.decode()


def remove_restarts(log: str) -> str:
    new_lines = itertools.takewhile(
        lambda line: 'The program finished and will be restarted' not in line,
        log.splitlines(keepends=True))
    return ''.join(new_lines)


def shorten_paths(log: str, path_to_omit: str) -> str:
    if not path_to_omit.endswith('/'):
        path_to_omit += '/'
    return log.replace(path_to_omit, '')

# TODO: add functions to doctor file names and remove other unnecessary output
