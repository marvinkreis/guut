import inspect
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, TimeoutExpired

import guut.debugger_wrapper as debugger_wrapper
from guut.problem import ExecutionResult


def run_debugger(target: Path, debugger_script: str, cwd: Path | None = None, timeout_secs: int = 2) -> ExecutionResult:
    process_input = debugger_script if debugger_script.endswith("\n") else debugger_script + "\n"
    # run python with unbuffered output, so it can be reliably captured on timeout
    process_command = ["python", "-u", inspect.getfile(debugger_wrapper), str(target)]
    process_cwd = cwd or target.parent

    process = Popen(process_command, cwd=process_cwd, stderr=STDOUT, stdout=PIPE, stdin=PIPE)
    try:
        output, _ = process.communicate(input=process_input.encode(), timeout=timeout_secs)
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
            exitcode=1,
            timeout=True,
        )
    finally:
        process.terminate()


def run_script(
    script: Path, stdin: str | None = None, cwd: Path | None = None, timeout_secs: int = 2
) -> ExecutionResult:
    if stdin:
        if stdin.endswith("\n"):
            process_input = stdin
        else:
            process_input = stdin + "\n"
    else:
        process_input = ""

    # run python with unbuffered output, so it can be reliably captured on timeout
    process_command = ["python", "-u", script]
    process_cwd = cwd or script.parent

    process = Popen(process_command, cwd=process_cwd, stderr=STDOUT, stdout=PIPE, stdin=PIPE)
    try:
        output, _ = process.communicate(input=process_input.encode() if process_input else None, timeout=timeout_secs)
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
            exitcode=1,
            timeout=True,
        )
    finally:
        process.terminate()
