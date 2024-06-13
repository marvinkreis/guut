#!/usr/bin/env python

"""
Wraps pdb and echos the entered debugger commands.
This makes them show up in the output when input is from a pipe.
"""


def wrapped_debugger():
    import pdb
    import sys

    class Intercept:
        def __init__(self):
            self.real_stdin = sys.stdin
            self.real_stdout = sys.stdout

        def readline(self):
            line = self.real_stdin.readline()
            self.real_stdout.write(line)
            return line

    sys.stdin = Intercept()
    pdb.main()


if __name__ == '__main__':
    wrapped_debugger()
