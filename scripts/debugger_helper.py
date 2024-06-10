#!/usr/bin/env python

import inspect
import itertools
from pathlib import Path
from subprocess import Popen, PIPE, CalledProcessError
from typing import List

import debugger_wrapper


def run_debugger(target: Path, debugger_commands: List[str], cwd: Path = None) -> str:
    process_input = ''.join(command + '\n' for command in debugger_commands)
    process_command = ['python', inspect.getfile(debugger_wrapper), str(target)]

    process = Popen(process_command, stdout=PIPE, stdin=PIPE, cwd=cwd or target.parent)
    (output, err) = process.communicate(input=process_input.encode('UTF-8'))
    exit_code = process.wait()

    if exit_code != 0:
        raise CalledProcessError(exit_code, process_command)

    return output.decode()


def remove_restarts(log: str) -> str:
    new_lines = itertools.takewhile(
        lambda line: 'The program finished and will be restarted' not in line,
        log.splitlines(keepends=True))
    return ''.join(new_lines)
