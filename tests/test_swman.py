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

import pytest
from unittest.mock import Mock, patch
from subprocess import CalledProcessError, CompletedProcess
from dotfiles.swman import UpdateStatus, UpdateResult, PacmanManager


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
@patch("dotfiles.swman.run_command_with_error_handling")
def test_pacman_check_updates_return_codes(
    mock_run_command, returncode, stdout, expected_has_updates, expected_count
):
    """PacmanManager.check_updates should handle different return codes correctly.

    checkupdates returns:
    - 0: updates available
    - 2: no updates available (this is NOT an error!)
    - other: actual errors (should raise)
    """
    # Setup mocks
    mock_logger = Mock()
    mock_logger.bind.return_value = mock_logger
    mock_output = Mock()

    # Mock the command result
    mock_run_command.return_value = CompletedProcess(
        args=["checkupdates"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )

    # Test
    manager = PacmanManager()
    has_updates, count = manager.check_updates(mock_logger, mock_output)

    # Verify
    assert has_updates == expected_has_updates
    assert count == expected_count
    mock_run_command.assert_called_once()
    # Verify check=False was passed to handle return codes manually
    assert mock_run_command.call_args.kwargs["check"] is False


@patch("dotfiles.swman.run_command_with_error_handling")
def test_pacman_check_updates_error_returncode(mock_run_command):
    """PacmanManager.check_updates should raise on actual errors (non-0, non-2 returncodes)."""
    # Setup mocks
    mock_logger = Mock()
    mock_logger.bind.return_value = mock_logger
    mock_output = Mock()

    # Mock an error result (returncode 1 = actual error)
    mock_run_command.return_value = CompletedProcess(
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
