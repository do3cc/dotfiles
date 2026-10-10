"""Tests for swman.py - Software Manager Orchestrator.

NOTE ON TEST COVERAGE:
Currently only testing data structures (UpdateResult, UpdateStatus). The actual manager
implementations (PacmanManager, YayManager, etc.) are not unit tested here because they
require real system commands (pacman, yay, apt, etc.).

INTEGRATION TESTING STRATEGY:
The managers are tested via integration tests in Docker containers (see Makefile targets:
test-arch, test-debian, test-ubuntu). Use @pytest.mark.integration for tests that need
real commands.

To run only unit tests: pytest -m "not integration"
To run integration tests: pytest -m integration
"""

from subprocess import CalledProcessError, CompletedProcess
from unittest.mock import Mock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dotfiles import swman
from dotfiles.swman import (
    DebianSystemManager,
    PackageUpdate,
    PacmanManager,
    UpdateResult,
    UpdateStatus,
    UvToolsManager,
    parse_apt_upgradable,
    parse_arrow_updates,
    parse_uv_outdated,
)


@pytest.mark.parametrize(
    "name,status,message,duration,expected_checks",
    [
        # Success status
        (
            "yay",
            UpdateStatus.SUCCESS,
            "All packages up to date",
            2.3,
            {"status": UpdateStatus.SUCCESS, "message_contains": "up to date"},
        ),
        # Failed status
        (
            "apt",
            UpdateStatus.FAILED,
            "Connection timeout",
            30.0,
            {"status": UpdateStatus.FAILED, "message": "Connection timeout"},
        ),
        # Skipped status with small duration
        (
            "lazy.nvim",
            UpdateStatus.SKIPPED,
            "Dry run mode",
            0.1,
            {"status": UpdateStatus.SKIPPED, "duration": 0.1},
        ),
        # Not available status
        (
            "fisher",
            UpdateStatus.NOT_AVAILABLE,
            "Command not found",
            0.0,
            {"status": UpdateStatus.NOT_AVAILABLE, "name": "fisher"},
        ),
        # Zero duration (quick operations)
        (
            "test",
            UpdateStatus.SKIPPED,
            "Skipped",
            0.0,
            {"duration": 0.0},
        ),
        # Long duration (system updates)
        (
            "system-update",
            UpdateStatus.SUCCESS,
            "Updated",
            300.5,
            {"duration": 300.5, "status": UpdateStatus.SUCCESS},
        ),
        # Empty message
        (
            "test",
            UpdateStatus.SUCCESS,
            "",
            0.5,
            {"message": "", "status": UpdateStatus.SUCCESS},
        ),
        # Multiline message
        (
            "pacman",
            UpdateStatus.SUCCESS,
            "Update completed successfully.\nDownloaded 5 packages.\nTotal size: 100MB.",
            60.0,
            {"message_contains": "Downloaded 5 packages", "duration": 60.0},
        ),
    ],
    ids=[
        "success",
        "failed",
        "skipped",
        "not_available",
        "zero_duration",
        "long_duration",
        "empty_message",
        "multiline_message",
    ],
)
def test_update_result_status_handling(
    name, status, message, duration, expected_checks
):
    """UpdateResult should handle different status values correctly."""
    result = UpdateResult(
        name=name,
        status=status,
        message=message,
        duration=duration,
    )

    # Dynamic test assertions based on expected_checks dict
    # This pattern allows different test cases to verify different aspects of UpdateResult
    # without duplicating test logic. Each parametrized case specifies which fields to check.

    if "status" in expected_checks:
        assert result.status == expected_checks["status"]

    if "message" in expected_checks:
        assert result.message == expected_checks["message"]

    if "message_contains" in expected_checks:
        assert expected_checks["message_contains"] in result.message

    if "duration" in expected_checks:
        assert result.duration == expected_checks["duration"]

    if "name" in expected_checks:
        assert result.name == expected_checks["name"]


def test_update_result_fields_are_correct_types():
    """UpdateResult fields should have expected types.

    This test verifies type constraints on dataclass fields.
    Cannot be parametrized with other tests since it checks types, not values.
    """
    result = UpdateResult(
        name="test", status=UpdateStatus.SUCCESS, message="Done", duration=1.0
    )

    assert isinstance(result.name, str)
    assert isinstance(result.status, UpdateStatus)
    assert isinstance(result.message, str)
    assert isinstance(result.duration, (int, float))


@pytest.mark.parametrize(
    "returncode,stdout,expected_has_updates,expected_count",
    [
        # Updates available - returncode 0 with package list
        (0, "package1 1.0-1 -> 1.1-1\npackage2 2.0-1 -> 2.1-1\n", True, 2),
        # No updates - returncode 2 (checkupdates standard behavior)
        (2, "", False, 0),
        # Updates available but empty output edge case
        (0, "", False, 0),
        # Single update available
        (0, "package1 1.0-1 -> 1.1-1\n", True, 1),
    ],
    ids=["updates_available", "no_updates_rc2", "empty_output", "single_update"],
)
@patch("subprocess.run")
def test_pacman_check_updates_return_codes(
    mock_subprocess_run, returncode, stdout, expected_has_updates, expected_count
):
    """PacmanManager.check_updates should handle different return codes correctly.

    checkupdates returns:
    - 0: updates available
    - 2: no updates available (this is NOT an error!)
    - other: actual errors (should raise)

    This test mocks subprocess.run directly (not run_command_with_error_handling)
    to ensure the real code path through process_helper.py is exercised.
    This catches bugs like duplicate keyword arguments in subprocess.run().
    """
    # Setup mocks
    mock_logger = Mock()
    mock_logger.bind.return_value = mock_logger
    mock_logger.log_info.return_value = None
    mock_logger.log_subprocess_result.return_value = None
    mock_output = Mock()

    # Mock the subprocess result
    mock_subprocess_run.return_value = CompletedProcess(
        args=["checkupdates"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )

    # Test
    manager = PacmanManager()
    has_updates, count = manager.check_updates(mock_logger, mock_output)

    # Verify behavior
    assert has_updates == expected_has_updates
    assert count == expected_count

    # Verify subprocess.run was called with check=False
    mock_subprocess_run.assert_called_once()
    assert mock_subprocess_run.call_args.kwargs["check"] is False
    assert mock_subprocess_run.call_args.kwargs["capture_output"] is True
    assert mock_subprocess_run.call_args.kwargs["text"] is True


@patch("subprocess.run")
def test_pacman_check_updates_error_returncode(mock_subprocess_run):
    """PacmanManager.check_updates should raise on actual errors (non-0, non-2 returncodes).

    This test mocks subprocess.run directly to exercise the real code path.
    """
    # Setup mocks
    mock_logger = Mock()
    mock_logger.bind.return_value = mock_logger
    mock_logger.log_info.return_value = None
    mock_logger.log_subprocess_result.return_value = None
    mock_output = Mock()

    # Mock an error result (returncode 1 = actual error)
    mock_subprocess_run.return_value = CompletedProcess(
        args=["checkupdates"],
        returncode=1,
        stdout="",
        stderr="error: database connection failed",
    )

    # Test - should raise CalledProcessError
    manager = PacmanManager()
    with pytest.raises(CalledProcessError) as exc_info:
        manager.check_updates(mock_logger, mock_output)

    # Verify exception details
    assert exc_info.value.returncode == 1
    assert exc_info.value.cmd == ["checkupdates"]

    # Verify subprocess.run was called with check=False
    mock_subprocess_run.assert_called_once()
    assert mock_subprocess_run.call_args.kwargs["check"] is False


# Exit codes of the CLI (click discards main()'s return value, so the code must sys.exit)
def test_swman_cli_without_operation_is_usage_error():
    from click.testing import CliRunner

    from dotfiles import swman

    result = CliRunner().invoke(swman.main, [])
    assert result.exit_code == 2
    assert "Must specify at least one operation" in result.output


def test_swman_cli_exits_1_when_a_manager_fails():
    from click.testing import CliRunner

    from dotfiles import swman

    failed = UpdateResult(
        name="pacman", status=UpdateStatus.FAILED, message="boom", duration=0.0
    )
    with patch.object(
        swman.SoftwareManagerOrchestrator, "update_by_type", return_value=[failed]
    ):
        result = CliRunner().invoke(swman.main, ["--system", "--dry-run", "--quiet"])
    assert result.exit_code == 1


def test_swman_cli_exits_0_when_all_succeed():
    from click.testing import CliRunner

    from dotfiles import swman

    ok = UpdateResult(
        name="pacman", status=UpdateStatus.SUCCESS, message="ok", duration=0.0
    )
    with patch.object(
        swman.SoftwareManagerOrchestrator, "update_by_type", return_value=[ok]
    ):
        result = CliRunner().invoke(swman.main, ["--system", "--dry-run", "--quiet"])
    assert result.exit_code == 0


# Update preview (#33)
_token = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Nd"), whitelist_characters=".-_+:"
    ),
    min_size=1,
    max_size=12,
)


@given(name=_token, old=_token, new=_token)
def test_parse_arrow_updates_roundtrip(name, old, new):
    assert parse_arrow_updates(f"{name} {old} -> {new}\n") == [
        PackageUpdate(name, old, new)
    ]


def test_parse_arrow_updates_keeps_unparseable_lines_for_the_count():
    parsed = parse_arrow_updates("git 1-1 -> 2-1\nweird line\n\n")
    assert parsed == [
        PackageUpdate("git", "1-1", "2-1"),
        PackageUpdate("weird line", "?", "?"),
    ]


def test_parse_apt_upgradable():
    stdout = (
        "Listing... Done\n"
        "git/noble-updates 1:2.43.0-1ubuntu7.3 amd64 [upgradable from: 1:2.43.0-1ubuntu7.1]\n"
        "vim/noble-security 2:9.1.0016-1ubuntu7.9 amd64 [upgradable from: 2:9.1.0016-1ubuntu7.8]\n"
    )
    assert parse_apt_upgradable(stdout) == [
        PackageUpdate("git", "1:2.43.0-1ubuntu7.1", "1:2.43.0-1ubuntu7.3"),
        PackageUpdate("vim", "2:9.1.0016-1ubuntu7.8", "2:9.1.0016-1ubuntu7.9"),
    ]


def test_parse_uv_outdated_ignores_executable_lines():
    # Real output of `uv tool list --outdated` (uv 0.11)
    stdout = "ruff v0.1.0 [latest: 0.16.10]\n- ruff\nblack v23.9.0 [latest: 23.10.0]\n- black\n"
    assert parse_uv_outdated(stdout) == [
        PackageUpdate("ruff", "0.1.0", "0.16.10"),
        PackageUpdate("black", "23.9.0", "23.10.0"),
    ]
    assert parse_uv_outdated("") == []


def _logger_and_output():
    logger = Mock()
    logger.bind.return_value = logger
    return logger, Mock()


@patch("subprocess.run")
def test_pacman_check_updates_records_packages(mock_run):
    mock_run.return_value = CompletedProcess(
        [], 0, "git 1-1 -> 2-1\nvim 3-1 -> 4-1\n", ""
    )
    manager = PacmanManager()
    manager.check_updates(*_logger_and_output())
    assert manager.last_updates == [
        PackageUpdate("git", "1-1", "2-1"),
        PackageUpdate("vim", "3-1", "4-1"),
    ]


@patch("subprocess.run")
def test_pacman_dry_run_result_carries_the_packages_and_does_not_update(mock_run):
    mock_run.return_value = CompletedProcess([], 0, "git 1-1 -> 2-1\n", "")
    result = PacmanManager().update(*_logger_and_output(), dry_run=True)
    assert result.updates == [PackageUpdate("git", "1-1", "2-1")]
    assert result.message == "Would update 1 packages"
    commands = [call.args[0] for call in mock_run.call_args_list]
    assert commands == [["checkupdates"]]  # no sudo pacman -Syu


@patch("subprocess.run")
def test_apt_check_updates_records_packages(mock_run):
    listing = "Listing... Done\ngit/noble 2 amd64 [upgradable from: 1]\n"
    mock_run.side_effect = [
        CompletedProcess([], 0, "", ""),
        CompletedProcess([], 0, listing, ""),
    ]
    manager = DebianSystemManager()
    assert manager.check_updates(*_logger_and_output()) == (True, 1)
    assert manager.last_updates == [PackageUpdate("git", "1", "2")]


@patch("subprocess.run")
def test_uv_check_updates_lists_outdated_tools(mock_run):
    mock_run.return_value = CompletedProcess(
        [], 0, "ruff v0.1.0 [latest: 0.2.0]\n- ruff\n", ""
    )
    manager = UvToolsManager()
    assert manager.check_updates(*_logger_and_output()) == (True, 1)
    assert manager.last_updates == [PackageUpdate("ruff", "0.1.0", "0.2.0")]


@patch("subprocess.run")
def test_uv_check_updates_cannot_determine_on_failure(mock_run):
    mock_run.side_effect = CalledProcessError(1, ["uv"])
    manager = UvToolsManager()
    assert manager.check_updates(*_logger_and_output()) == (False, -1)
    assert manager.last_updates is None


def test_lazy_and_fisher_dry_run_say_preview_not_available():
    for manager in (swman.LazyNvimManager(), swman.FisherManager()):
        result = manager.update(*_logger_and_output(), dry_run=True)
        assert result.updates is None
        assert "preview not available" in result.message


def _invoke(args, results=None, managers=None):
    from click.testing import CliRunner

    patches = []
    if results is not None:
        patches.append(
            patch.object(
                swman.SoftwareManagerOrchestrator,
                "update_by_type",
                return_value=results,
            )
        )
    if managers is not None:
        patches.append(
            patch.object(
                swman.SoftwareManagerOrchestrator,
                "check_all",
                return_value={
                    m.name: (True, len(m.last_updates or [])) for m in managers
                },
            )
        )
    for p in patches:
        p.start()
    try:
        orchestrator_managers = managers
        if orchestrator_managers is not None:
            with patch.object(
                swman.SoftwareManagerOrchestrator,
                "__init__",
                lambda self: setattr(self, "managers", orchestrator_managers),
            ):
                return CliRunner().invoke(swman.main, args)
        return CliRunner().invoke(swman.main, args)
    finally:
        for p in patches:
            p.stop()


def test_dry_run_prints_the_package_preview():
    result = UpdateResult(
        "pacman",
        UpdateStatus.SUCCESS,
        "Would update 2 packages",
        0.0,
        updates=[
            PackageUpdate("git", "2.42.0", "2.43.0"),
            PackageUpdate("vim", "9.0.1", "9.0.2"),
        ],
    )
    skipped = UpdateResult(
        "fisher",
        UpdateStatus.SUCCESS,
        "Would update Fish plugins (preview not available)",
        0.0,
    )
    out = _invoke(["--all", "--dry-run"], results=[result, skipped])
    assert out.exit_code == 0
    assert "git" in out.output and "2.43.0" in out.output and "vim" in out.output
    assert "fisher: preview not available" in out.output
    assert "Would update 2 packages across 1 managers" in out.output


def test_check_lists_the_packages_too():
    manager = PacmanManager()
    manager.last_updates = [PackageUpdate("git", "2.42.0", "2.43.0")]
    out = _invoke(["--check"], managers=[manager])
    assert out.exit_code == 0
    assert "git" in out.output and "2.43.0" in out.output
    assert "Updates available: 1 packages across 1 managers" in out.output


# Orchestrator error handling (#80)
def _orchestrator_with(*managers):
    orchestrator = swman.SoftwareManagerOrchestrator()
    orchestrator.managers = list(managers)
    return orchestrator


def _mock_manager(name, manager_type=swman.ManagerType.SYSTEM):
    manager = Mock()
    manager.name = name
    manager.type = manager_type
    manager.is_available.return_value = True
    return manager


def test_check_all_logs_and_continues_when_a_manager_raises():
    broken = _mock_manager("broken")
    broken.check_updates.side_effect = RuntimeError("boom")
    working = _mock_manager("working")
    working.check_updates.return_value = (True, 2)
    logger, output = _logger_and_output()

    results = _orchestrator_with(broken, working).check_all(logger, output)

    assert results == {"broken": (False, 0), "working": (True, 2)}
    logger.log_exception.assert_called_once()
    assert logger.log_exception.call_args.args[1] == "update_check_failed"


def test_update_by_type_logs_and_continues_when_a_manager_raises():
    broken = _mock_manager("broken")
    broken.update.side_effect = RuntimeError("boom")
    ok_result = UpdateResult("working", UpdateStatus.SUCCESS, "ok", 0.0)
    working = _mock_manager("working")
    working.update.return_value = ok_result
    logger, output = _logger_and_output()

    results = _orchestrator_with(broken, working).update_by_type(
        swman.ManagerType.SYSTEM, logger, output
    )

    assert [r.name for r in results] == ["broken", "working"]
    assert results[0].status == UpdateStatus.FAILED
    assert "boom" in results[0].message
    assert results[1] is ok_result
    logger.log_exception.assert_called_once()
    assert logger.log_exception.call_args.args[1] == "unexpected_exception"


def test_orchestrator_has_no_unused_update_all():
    assert not hasattr(swman.SoftwareManagerOrchestrator, "update_all")
