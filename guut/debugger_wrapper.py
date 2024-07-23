#!/usr/bin/env python

"""
Wraps pdb and echos the entered debugger commands.
This makes them show up in the output when input is from a pipe.
"""

import sys
from pathlib import Path


# unused
def clean_trace(exc: BaseException, directory: Path):
    """Formats the trace of an exception, only including frames that are real files and are within path."""
    from os.path import exists, realpath
    from traceback import extract_tb, format_list

    trace = extract_tb(exc.__traceback__)
    trace = [frame for frame in trace if exists(frame.filename) and str(directory) in realpath(frame.filename)]
    trace = "".join(format_list(trace))

    if exc.args:
        msg = f"{type(exc).__name__}: {exc.args[0]}"
    else:
        msg = type(exc).__name__

    return f"Traceback:\n{trace}{msg}"


def wrapped_debugger(script: Path):
    import sys
    from pdb import Pdb, Restart, _ScriptTarget  # pyright: ignore
    from traceback import print_exception

    class Intercept:
        def __init__(self):
            self.real_stdin = sys.stdin
            self.real_stdout = sys.stdout

        def readline(self):
            line = self.real_stdin.readline()
            self.real_stdout.write(line)
            return line

    sys.stdin = Intercept()

    target = _ScriptTarget(str(script))
    target.check()

    pdb = Pdb()

    try:
        pdb._run(target)  # pyright: ignore
        print("The program exited.")
    except Restart:
        # Don't restart the debugger.
        pass
    except SystemExit as e:
        # Stop on SystemExit.
        print(f"The program exited via sys.exit(). Exit status: {e.code}")
    except BaseException as e:
        print_exception(e)
        sys.exit(1)


if __name__ == "__main__":
    script = Path(sys.argv[1]).resolve()

    if not script.exists():
        print(f"File not found: {script}")
        sys.exit(1)

    wrapped_debugger(script)
