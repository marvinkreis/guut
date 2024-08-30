import ast

# TODO: move some stuff here


def get_test_name(code: str) -> str | None:
    module = ast.parse(code, "test.py", "exec")

    funs = [node for node in module.body if isinstance(node, ast.FunctionDef)]
    tests = [fun for fun in funs if fun.name.startswith("test")]

    if tests:
        return tests[0].name
    elif funs:
        return funs[0].name
    else:
        return None


def maybe_add_test_call(code: str) -> str:
    test_name = get_test_name(code)
    if test_name:
        return f"{code}\n\n{test_name}()\n"
    else:
        return code
