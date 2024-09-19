#!/usr/bin/env python

"""
Wraps pdb and echos the entered debugger commands.
This makes them show up in the output when input is from a pipe.
"""

import os
import pdb
import sys
from pathlib import Path
from traceback import print_exception


def wrapped_debugger(script: Path) -> None:
    class Intercept:
        def __init__(self):
            self.real_stdin = sys.stdin
            self.real_stdout = sys.stdout

        def readline(self):
            line = self.real_stdin.readline()
            self.real_stdout.write(line)
            return line

    sys.stdin = Intercept()
    debugger = pdb.Pdb()

    try:
        if hasattr(pdb, "_ScriptTarget"):  # for python 3.11
            target = pdb._ScriptTarget(str(script))  # pyright: ignore (private member)
            target.check()
            debugger._run(target)  # pyright: ignore (private member)
        elif hasattr(debugger, "_runscript"):  # for python 3.8
            mainpyfile = os.path.realpath(script)
            sys.path[0] = os.path.dirname(mainpyfile)
            debugger._runscript(mainpyfile)  # pyright: ignore (private member)
        else:
            print("Failed to run debugger.")
            return
        print("The program exited.")
    except pdb.Restart:
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
