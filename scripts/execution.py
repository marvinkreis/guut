#!/usr/bin/env python

import inspect
from dataclasses import dataclass
from pathlib import Path
from subprocess import TimeoutExpired, STDOUT, Popen, PIPE
from typing import List

import debugger_wrapper


@dataclass
class Result:
    target: Path
    args: List[str]
    cwd: Path
    input: str

    output: str
    exitcode: int = 0
    timeout: bool = False


def run_debugger(target: Path, debugger_commands: List[str], cwd: Path = None) -> Result:
    process_input = ''.join(command.strip() + '\n' for command in debugger_commands)
    process_command = ['python', inspect.getfile(debugger_wrapper), str(target)]
    process_cwd = cwd or target.parent

    process = Popen(process_command, cwd=process_cwd, stderr=STDOUT, stdout=PIPE, stdin=PIPE, preexec_fn=fun)
    try:
        output, _ = process.communicate(input=process_input.encode(), timeout=2)
        return Result(target=target,
                      args=[],
                      cwd=process_cwd,
                      input=process_input,
                      output=output.decode(),
                      exitcode=process.returncode)
    except TimeoutExpired as timeout:
        return Result(target=target,
                      args=[],
                      cwd=process_cwd,
                      input=process_input,
                      output=timeout.stdout.decode(),
                      exitcode=process.returncode,
                      timeout=True)


def run_script(script: Path, stdin: str = None, cwd: Path = None) -> Result:
    if stdin:
        if stdin.endswith('\n'):
            process_input = stdin
        else:
            process_input = (stdin + '\n')
    else:
        process_input = None

    process_command = ['python', script]
    process_cwd = cwd or script.parent

    process = Popen(process_command, cwd=process_cwd, stderr=STDOUT, stdout=PIPE, stdin=PIPE)
    try:
        output, _ = process.communicate(input=process_input.encode() if process_input else None, timeout=2)
        return Result(target=script,
                      args=[],
                      cwd=process_cwd,
                      input=process_input,
                      output=output.decode(),
                      exitcode=process.returncode)
    except TimeoutExpired as timeout:
        return Result(target=script,
                      args=[],
                      cwd=process_cwd,
                      input=process_input,
                      output=timeout.stdout.decode(),
                      exitcode=process.returncode,
                      timeout=True)
