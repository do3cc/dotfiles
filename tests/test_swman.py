"""Tests for swman.py - Software Manager Orchestrator."""

import pytest
from dotfiles.swman import UpdateStatus, UpdateResult

# XXX This is terrible test coverage, none of the methods that actually do something are tested!
# XXX Is there an easy way to mark tests so that they are not executed during a normal pytest run, but are run when a specific flag is set? I think we should do integration tests, but in the docker containers only.


# TODO: REVIEW
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
        # Skipped status
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
    ],
    ids=["success", "failed", "skipped", "not_available"],
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

    # Check expected status
    # XXX what type of test is this? a small mistake would make this test not test anything, how do you even come up with this idea?
    if "status" in expected_checks:
        assert result.status == expected_checks["status"]

    # Check exact message match
    if "message" in expected_checks:
        assert result.message == expected_checks["message"]

    # Check message contains substring
    if "message_contains" in expected_checks:
        assert expected_checks["message_contains"] in result.message

    # Check duration
    if "duration" in expected_checks:
        assert result.duration == expected_checks["duration"]

    # Check name
    if "name" in expected_checks:
        assert result.name == expected_checks["name"]


# TODO: REVIEW
# XXX: Consolidate these simple UpdateResult tests into a single test parametrized with parametrize
def test_update_result_with_zero_duration():
    """UpdateResult should allow zero duration for quick operations."""
    result = UpdateResult(
        name="test", status=UpdateStatus.SKIPPED, message="Skipped", duration=0.0
    )

    assert result.duration == 0.0


# TODO: REVIEW
def test_update_result_with_long_duration():
    """UpdateResult should handle long-running operations."""
    result = UpdateResult(
        name="system-update",
        status=UpdateStatus.SUCCESS,
        message="Updated",
        duration=300.5,
    )

    assert result.duration == 300.5


# TODO: REVIEW
def test_update_result_fields_are_correct_types():
    """UpdateResult fields should have expected types."""
    result = UpdateResult(
        name="test", status=UpdateStatus.SUCCESS, message="Done", duration=1.0
    )

    assert isinstance(result.name, str)
    assert isinstance(result.status, UpdateStatus)
    assert isinstance(result.message, str)
    assert isinstance(result.duration, (int, float))


# TODO: REVIEW
def test_update_result_with_empty_message():
    """UpdateResult should handle empty message strings."""
    result = UpdateResult(
        name="test", status=UpdateStatus.SUCCESS, message="", duration=0.5
    )

    assert result.message == ""


# TODO: REVIEW
def test_update_result_with_multiline_message():
    """UpdateResult should handle multiline messages."""
    message = """Update completed successfully.
Downloaded 5 packages.
Total size: 100MB."""

    result = UpdateResult(
        name="pacman", status=UpdateStatus.SUCCESS, message=message, duration=60.0
    )

    assert "\n" in result.message
    assert "Downloaded 5 packages" in result.message
