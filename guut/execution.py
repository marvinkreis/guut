import inspect
import json
import signal
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, TimeoutExpired
from typing import List

from loguru import logger

import guut.debugger_wrapper as debugger_wrapper
from guut.problem import Coverage, ExecutionResult


def decode_output(output: bytes):
    try:
        return output.decode()
    except UnicodeDecodeError:
        logger.warning("Process output isn't valid unicode.")
        return "<text encoding error>"


class PythonExecutor:
    def __init__(self, python_interpreter: Path):
        self.python_interpreter = python_interpreter

    def run_script(
        self,
        target: Path,
        cwd: Path | None = None,
        timeout_secs: int = 5,
        python_interpreter: Path | None = None,
    ) -> ExecutionResult:
        if not python_interpreter:
            python_interpreter = self.python_interpreter

        # run python with unbuffered output, so it can be reliably captured on timeout
        command = [str(python_interpreter.absolute()), "-u", str(target)]

        return run(command=command, cwd=cwd or target.parent, target=target, timeout_secs=timeout_secs)

    def run_debugger(
        self,
        target: Path,
        debugger_script: str,
        cwd: Path | None = None,
        timeout_secs: int = 5,
        python_interpreter: Path | None = None,
    ) -> ExecutionResult:
        if not python_interpreter:
            python_interpreter = self.python_interpreter

        # run python with unbuffered output, so it can be reliably captured on timeout
        command = [str(python_interpreter.absolute()), "-u", inspect.getfile(debugger_wrapper), str(target)]
        stdin = debugger_script if debugger_script.endswith("\n") else debugger_script + "\n"

        return run(command=command, cwd=cwd or target.parent, target=target, stdin=stdin, timeout_secs=timeout_secs)

    def run_script_with_coverage(
        self,
        target: Path,
        cut_file: Path,
        include_files: List[Path] | None = None,
        cwd: Path | None = None,
        timeout_secs: int = 5,
        python_interpreter: Path | None = None,
    ) -> ExecutionResult:
        python_interpreter = python_interpreter or self.python_interpreter
        cwd = cwd or target.parent

        # run python with unbuffered output, so it can be reliably captured on timeout
        exec_command = [str(python_interpreter.absolute()), "-u", "-m", "coverage", "run", "--branch", str(target)]
        exec_result = run(command=exec_command, cwd=cwd, target=target, timeout_secs=timeout_secs)

        report_command = [str(python_interpreter.absolute()), "-m", "coverage", "json"] + (
            ["--include", ",".join(map(str, include_files))] if include_files else []
        )
        run(command=report_command, cwd=cwd, target=target)

        coverage_path = cwd / "coverage.json"
        if not coverage_path.is_file():
            logger.error(f"Could't find coverage file: '{coverage_path}'")
            return exec_result

        with coverage_path.open() as coverage_file:
            coverage_json = json.load(coverage_file)

        cut_coverage = coverage_json["files"].get(str(cut_file.relative_to(cwd)))
        if not cut_coverage:
            logger.error(f"Couldn't find CUT coverage in coverage file: '{coverage_path}'")
            return exec_result

        covered_lines = cut_coverage["executed_lines"]
        missing_lines = cut_coverage["missing_lines"]
        exec_result.coverage = Coverage(covered_lines, missing_lines, coverage_json)
        return exec_result


def run(
    command: List[str], cwd: Path, target: Path, stdin: str | None = None, timeout_secs: int | None = None
) -> ExecutionResult:
    if stdin:
        if stdin.endswith("\n"):
            process_input = stdin
        else:
            process_input = stdin + "\n"
    else:
        process_input = ""

    process = Popen(command, cwd=cwd, stderr=STDOUT, stdout=PIPE, stdin=PIPE)
    try:
        output, _ = process.communicate(input=process_input.encode() if process_input else None, timeout=timeout_secs)
        return ExecutionResult(
            command=command[::],
            target=target,
            cwd=cwd,
            input=process_input,
            output=decode_output(output),
            exitcode=process.returncode,
        )
    except TimeoutExpired as timeout:
        output = timeout.stdout or b""
        return ExecutionResult(
            command=command[::],
            target=target,
            cwd=cwd,
            input=process_input,
            output=decode_output(output),
            exitcode=1,
            timeout=True,
        )
    finally:
        if process.poll() is None:
            logger.debug(f"Sending SIGINT to {command}")
            process.send_signal(sig=signal.SIGINT)

        if process.poll() is None:
            try:
                process.wait(2)
            except TimeoutExpired:
                pass

        if process.poll() is None:
            logger.debug(f"Terminating {command}")
            process.terminate()

        if process.poll() is None:
            try:
                process.wait(2)
            except TimeoutExpired:
                pass

        if process.poll() is None:
            logger.debug(f"Killing {command}")
            process.kill()
