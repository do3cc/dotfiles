"""The guard that fails tests without assertions (#84)."""

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / ".pre-commit-hooks" / "check-test-assertions.py"

spec = importlib.util.spec_from_file_location("check_test_assertions", SCRIPT)
assert spec is not None and spec.loader is not None
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def problems(tmp_path, source):
    path = tmp_path / "test_sample.py"
    path.write_text(textwrap.dedent(source))
    return [name for _line, name in check.find_tests_without_assertion(path)]


@pytest.mark.parametrize(
    "body",
    [
        "pass  # TODO: Implement",
        "do_something()",
        "x = compute()",
        "with open('f') as f:\n        f.read()",
    ],
    ids=["stub", "call-only", "assignment-only", "with-block"],
)
def test_a_test_without_assertion_is_reported(tmp_path, body):
    source = f"def test_x():\n    {body}\n"
    assert problems(tmp_path, source) == ["test_x"]


@pytest.mark.parametrize(
    "body",
    [
        "assert compute() == 1",
        "mock.assert_called_once_with(1)",
        "obj.method.assert_not_called()",
        "_assert_valid(result)",
        "pytest.fail('boom')",
        "with pytest.raises(ValueError):\n        compute()",
        "with pytest.warns(UserWarning):\n        compute()",
    ],
    ids=[
        "assert",
        "mock-assertion",
        "mock-not-called",
        "assert-helper",
        "fail",
        "raises",
        "warns",
    ],
)
def test_a_test_with_an_assertion_is_accepted(tmp_path, body):
    source = f"def test_x():\n    {body}\n"
    assert problems(tmp_path, source) == []


def test_only_test_functions_are_checked(tmp_path):
    source = """
    def helper():
        pass

    def test_ok():
        assert True

    class TestThing:
        def test_method(self):
            pass
    """
    assert problems(tmp_path, source) == ["test_method"]


def test_the_opt_out_comment_on_the_def_line_is_honoured(tmp_path):
    source = """
    def test_does_not_raise():  # no-assertion-ok: smoke test of the import
        import json
    """
    assert problems(tmp_path, source) == []


def test_an_assertion_in_a_nested_block_counts(tmp_path):
    source = """
    def test_loop():
        for value in (1, 2):
            if value:
                assert value
    """
    assert problems(tmp_path, source) == []


def test_the_script_exits_non_zero_and_names_the_test(tmp_path):
    path = tmp_path / "test_bad.py"
    path.write_text("def test_nothing():\n    pass\n")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "test_bad.py:1: test_nothing has no assertion" in result.stdout


def test_the_whole_suite_passes_the_check():
    tests = sorted(Path(__file__).parent.glob("test_*.py"))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, tests)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
