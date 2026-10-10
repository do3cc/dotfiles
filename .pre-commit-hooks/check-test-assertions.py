#!/usr/bin/env python3
"""Fail if a test function contains no assertion.

A test that cannot fail is worse than no test. A test counts as asserting when
its body contains an ``assert`` statement, a ``with pytest.raises/warns(...)``
block, ``pytest.fail(...)``, or a call to a function whose name starts with
``assert`` (mock assertions like ``assert_called_once_with`` and helpers such as
``_assert_valid``).

A test that intentionally only checks "does not raise" can opt out with a
comment on its ``def`` line: ``# no-assertion-ok: <reason>``.
"""

import ast
import sys
from pathlib import Path

OPT_OUT = "no-assertion-ok"
CONTEXT_ASSERTIONS = {"raises", "warns", "deprecated_call"}


def _name(node: ast.AST) -> str:
    """The last name of a call target: ``a.b.c(...)`` -> ``c``."""
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def has_assertion(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(function):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, (ast.With, ast.AsyncWith)) and any(
            _name(item.context_expr) in CONTEXT_ASSERTIONS for item in node.items
        ):
            return True
        if isinstance(node, ast.Call):
            name = _name(node).lstrip("_")
            if name.startswith("assert") or name == "fail":
                return True
    return False


def find_tests_without_assertion(path: Path) -> list[tuple[int, str]]:
    source = path.read_text()
    lines = source.splitlines()
    problems: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source, filename=str(path))):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        if OPT_OUT in lines[node.lineno - 1]:
            continue
        if not has_assertion(node):
            problems.append((node.lineno, node.name))
    return sorted(problems)


def main(argv: list[str]) -> int:
    failed = False
    for name in argv:
        for line, test in find_tests_without_assertion(Path(name)):
            print(f"{name}:{line}: {test} has no assertion")
            failed = True
    if failed:
        print(
            "A test needs an assert, pytest.raises, or a mock assertion "
            f"(or '# {OPT_OUT}: <reason>' on its def line)."
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
