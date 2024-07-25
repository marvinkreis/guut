#!/usr/bin/env python

"""
Wraps pdb and echos the entered debugger commands.
This makes them show up in the output when input is from a pipe.
"""

import sys
from pathlib import Path


def wrapped_debugger(script: Path) -> None:
    import sys
    from pdb import Pdb, Restart, _ScriptTarget  # pyright: ignore (private memeber)
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
        pdb._run(target)  # pyright: ignore (private member)
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
