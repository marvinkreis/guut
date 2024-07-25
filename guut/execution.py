import inspect
from dataclasses import dataclass
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, TimeoutExpired
from typing import List

import guut.debugger_wrapper as debugger_wrapper


@dataclass
class ExecutionResult:
    target: Path
    args: List[str]
    cwd: Path
    input: str

    output: str
    exitcode: int = 0
    timeout: bool = False


def run_debugger(target: Path, debugger_script: str, cwd: Path | None = None) -> ExecutionResult:
    process_input = debugger_script if debugger_script.endswith("\n") else debugger_script + "\n"
    process_command = ["python", inspect.getfile(debugger_wrapper), str(target)]
    process_cwd = cwd or target.parent

    process = Popen(process_command, cwd=process_cwd, stderr=STDOUT, stdout=PIPE, stdin=PIPE)
    try:
        output, _ = process.communicate(input=process_input.encode(), timeout=2)
        return ExecutionResult(
            target=target,
            args=[],
            cwd=process_cwd,
            input=process_input,
            output=output.decode(),
            exitcode=process.returncode,
        )
    except TimeoutExpired as timeout:
        output = timeout.stdout or b""
        return ExecutionResult(
            target=target,
            args=[],
            cwd=process_cwd,
            input=process_input,
            output=output.decode(),
            exitcode=process.returncode,
            timeout=True,
        )


def run_script(script: Path, stdin: str | None = None, cwd: Path | None = None) -> ExecutionResult:
    if stdin:
        if stdin.endswith("\n"):
            process_input = stdin
        else:
            process_input = stdin + "\n"
    else:
        process_input = ""

    process_command = ["python", script]
    process_cwd = cwd or script.parent

    process = Popen(process_command, cwd=process_cwd, stderr=STDOUT, stdout=PIPE, stdin=PIPE)
    try:
        output, _ = process.communicate(input=process_input.encode() if process_input else None, timeout=2)
        return ExecutionResult(
            target=script,
            args=[],
            cwd=process_cwd,
            input=process_input,
            output=output.decode(),
            exitcode=process.returncode,
        )
    except TimeoutExpired as timeout:
        output = timeout.stdout or b""
        return ExecutionResult(
            target=script,
            args=[],
            cwd=process_cwd,
            input=process_input,
            output=output.decode(),
            exitcode=process.returncode,
            timeout=True,
        )
