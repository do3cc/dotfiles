"""--verbose sets debug logging and tells the user where the log file is (#46)."""

import logging
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from dotfiles import init, pkgstatus, project_status, swman
from dotfiles.logging_config import setup_logging
from dotfiles.output_formatting import ConsoleOutput


def test_setup_logging_default_level_is_info(tmp_path):
    helpers = setup_logging("test", log_dir=tmp_path)
    assert logging.getLogger().level == logging.INFO
    assert helpers.log_file == tmp_path / "dotfiles.log"


def test_setup_logging_verbose_uses_debug_level(tmp_path):
    setup_logging("test", verbose=True, log_dir=tmp_path)
    assert logging.getLogger().level == logging.DEBUG


def test_debug_records_are_written_only_in_verbose_mode(tmp_path):
    quiet = setup_logging("test", log_dir=tmp_path / "info")
    quiet.log_debug("debug_event_info_mode")
    verbose = setup_logging("test", verbose=True, log_dir=tmp_path / "debug")
    verbose.log_debug("debug_event_verbose_mode")

    assert "debug_event_info_mode" not in (tmp_path / "info/dotfiles.log").read_text()
    assert "debug_event_verbose_mode" in (tmp_path / "debug/dotfiles.log").read_text()


def test_bind_keeps_the_log_file(tmp_path):
    helpers = setup_logging("test", log_dir=tmp_path).bind(a=1)
    assert helpers.log_file == tmp_path / "dotfiles.log"


def test_log_file_hint_is_a_copy_and_paste_tail_command(tmp_path, capsys):
    helpers = setup_logging("test", log_dir=tmp_path)
    ConsoleOutput(verbose=True).log_file_hint(helpers)
    out = capsys.readouterr().out
    assert f"tail -f {tmp_path / 'dotfiles.log'}" in out


@pytest.mark.parametrize(
    "output",
    [ConsoleOutput(verbose=False), ConsoleOutput(verbose=True, quiet=True)],
    ids=["not-verbose", "quiet"],
)
def test_log_file_hint_is_silent_unless_verbose(output, tmp_path, capsys):
    output.log_file_hint(setup_logging("test", log_dir=tmp_path))
    assert capsys.readouterr().out == ""


def test_log_file_hint_without_a_log_file_prints_nothing(capsys):
    ConsoleOutput(verbose=True).log_file_hint(MagicMock(log_file=None))
    assert capsys.readouterr().out == ""


def _init_fails_early(monkeypatch):
    def no_os(*args, **kwargs):
        raise FileNotFoundError("/etc/os-release")

    monkeypatch.setattr(init, "detect_operating_system", no_os)


def _pkgstatus_fails(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(pkgstatus, "StatusChecker", boom)


def _nothing(monkeypatch):
    pass


# (command, arguments without --verbose, prepare, exit code of the run)
TOOLS = [
    pytest.param(init.main, [], _init_fails_early, 1, id="init"),
    pytest.param(swman.main, [], _nothing, 2, id="swman"),
    pytest.param(pkgstatus.main, [], _pkgstatus_fails, 1, id="pkgstatus"),
    pytest.param(project_status.main, ["--no-github"], _nothing, 0, id="status"),
]


@pytest.mark.parametrize("command,args,prepare,exit_code", TOOLS)
def test_verbose_prints_the_log_file_hint(
    command, args, prepare, exit_code, monkeypatch, tmp_path
):
    prepare(monkeypatch)
    result = CliRunner().invoke(
        command, [*args, "--verbose"], env={"HOME": str(tmp_path)}
    )
    assert result.exit_code == exit_code, result.output
    assert f"tail -f {tmp_path}/.cache/dotfiles/logs/dotfiles.log" in result.output


@pytest.mark.parametrize("command,args,prepare,exit_code", TOOLS)
def test_without_verbose_there_is_no_log_file_hint(
    command, args, prepare, exit_code, monkeypatch, tmp_path
):
    prepare(monkeypatch)
    result = CliRunner().invoke(command, args, env={"HOME": str(tmp_path)})
    assert result.exit_code == exit_code, result.output
    assert "tail -f" not in result.output


@pytest.mark.parametrize("command,args,prepare,exit_code", TOOLS)
def test_verbose_together_with_quiet_is_a_usage_error(
    command, args, prepare, exit_code, monkeypatch, tmp_path
):
    prepare(monkeypatch)
    result = CliRunner().invoke(
        command, [*args, "--verbose", "--quiet"], env={"HOME": str(tmp_path)}
    )
    assert result.exit_code == 2
    assert "--verbose and --quiet cannot be used together" in result.output
