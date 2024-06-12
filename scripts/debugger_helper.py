#!/usr/bin/env python

import inspect
import itertools
from pathlib import Path
from subprocess import run, TimeoutExpired, STDOUT, Popen, PIPE
from typing import List

import debugger_wrapper


def run_debugger(target: Path, debugger_commands: List[str], cwd: Path = None) -> str:
    process_input = ''.join(command.strip() + '\n' for command in debugger_commands)
    process_command = ['python', inspect.getfile(debugger_wrapper), str(target)]
    process_cwd = cwd or target.parent

    try:
        # TODO: try preexec_fun
        # TODO: give encoding here
        process = Popen(process_command, cwd=process_cwd, stderr=STDOUT, stdout=PIPE, stdin=PIPE)
        output, _ = process.communicate(input=process_input.encode(), timeout=2)
        returncode = process.returncode
    except TimeoutExpired as e:
        output = e.stdout
        returncode = 1
        pass

    return output.decode()


def run_script(script: Path, stdin: str = None, cwd: Path = None) -> str:
    if stdin:
        if stdin.endswith('\n'):
            process_input = stdin.encode()
        else:
            process_input = (stdin + '\n').encode()
    else:
        process_input = None

    process_command = ['python', script]
    process_cwd = cwd or script.parent

    try:
        process = Popen(process_command, cwd=process_cwd, stderr=STDOUT, stdout=PIPE, stdin=PIPE)
        output, _ = process.communicate(input=process_input, timeout=2)
        returncode = process.returncode
    except TimeoutExpired as e:
        output = e.stdout
        returncode = 1
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
