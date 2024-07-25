from pathlib import Path


def clean_trace(exc: BaseException, directory: Path) -> str:
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
