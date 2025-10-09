"""Tests for process_helper.py - subprocess command execution with error handling."""

from dotfiles import process_helper
from dotfiles.output_formatting import ConsoleOutput
import pytest
import subprocess
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_output():
    """Mock ConsoleOutput for testing."""
    return MagicMock(spec=ConsoleOutput)


# ==============================================================================
# Tests for run_command_with_error_handling()
# ==============================================================================


def test_successful_command_execution(mock_logging_helpers, mock_output):
    """run_command_with_error_handling() should execute successful commands."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hello"],
            returncode=0,
            stdout="hello\n",
            stderr="",
        )

        result = process_helper.run_command_with_error_handling(
            ["echo", "hello"],
            mock_logging_helpers,
            mock_output,
            description="Echo test",
        )

        assert result.returncode == 0
        assert result.stdout == "hello\n"
        mock_run.assert_called_once()


def test_binds_context_before_execution(mock_logging_helpers, mock_output):
    """Should bind command context to logger before execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["test"], returncode=0, stdout="", stderr=""
        )

        process_helper.run_command_with_error_handling(
            ["test", "arg"],
            mock_logging_helpers,
            mock_output,
            description="Test command",
            timeout=60,
        )

        mock_logging_helpers.bind.assert_called_once_with(
            description="Test command", command=["test", "arg"], timeout=60
        )


def test_logs_command_starting(mock_logging_helpers, mock_output):
    """Should log command_starting event."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["test"], returncode=0, stdout="", stderr=""
        )

        process_helper.run_command_with_error_handling(
            ["test"], mock_logging_helpers, mock_output
        )

        mock_logging_helpers.log_info.assert_called_with("command_starting")


def test_logs_subprocess_result_on_success(mock_logging_helpers, mock_output):
    """Should call log_subprocess_result() on successful execution."""
    with patch("subprocess.run") as mock_run:
        result = subprocess.CompletedProcess(
            args=["echo", "test"], returncode=0, stdout="test\n", stderr=""
        )
        mock_run.return_value = result

        process_helper.run_command_with_error_handling(
            ["echo", "test"], mock_logging_helpers, mock_output, description="Echo test"
        )

        mock_logging_helpers.log_subprocess_result.assert_called_once_with(
            "Echo test", ["echo", "test"], result
        )


def test_timeout_expired_handling(mock_logging_helpers, mock_output):
    """Should handle TimeoutExpired exceptions with logging and output."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="slow", timeout=5)

        with pytest.raises(subprocess.TimeoutExpired):
            process_helper.run_command_with_error_handling(
                ["slow", "command"],
                mock_logging_helpers,
                mock_output,
                description="Slow command",
                timeout=5,
            )

        # Should log exception
        assert mock_logging_helpers.log_exception.called
        exception_call = mock_logging_helpers.log_exception.call_args
        assert isinstance(exception_call.args[0], subprocess.TimeoutExpired)
        assert exception_call.args[1] == "command timed out"

        # Should display error to user
        mock_output.error.assert_called()
        error_msg = mock_output.error.call_args.args[0]
        assert "timed out" in error_msg.lower()
        assert "5" in error_msg


def test_timeout_shows_command_in_output(mock_logging_helpers, mock_output):
    """Timeout error should show the command that timed out."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=10)

        with pytest.raises(subprocess.TimeoutExpired):
            process_helper.run_command_with_error_handling(
                ["test", "arg"], mock_logging_helpers, mock_output
            )

        # Should show command in status
        mock_output.status.assert_called()
        status_msg = mock_output.status.call_args.args[0]
        assert "test" in status_msg
        assert "arg" in status_msg


def test_called_process_error_handling(mock_logging_helpers, mock_output):
    """Should handle CalledProcessError with comprehensive logging."""
    with patch("subprocess.run") as mock_run:
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "invalid"],
            output="",
            stderr="error: unknown command\n",
        )
        error.stdout = ""
        error.stderr = "error: unknown command\n"
        mock_run.side_effect = error

        with pytest.raises(subprocess.CalledProcessError):
            process_helper.run_command_with_error_handling(
                ["git", "invalid"],
                mock_logging_helpers,
                mock_output,
                description="Invalid git command",
            )

        # Should log exception with context
        mock_logging_helpers.log_exception.assert_called()
        exception_call = mock_logging_helpers.log_exception.call_args
        assert isinstance(exception_call.args[0], subprocess.CalledProcessError)
        assert exception_call.args[1] == "command_failed"
        assert exception_call.kwargs["returncode"] == 1
        assert exception_call.kwargs["stderr"] == "error: unknown command\n"


def test_shows_stdout_stderr_on_failure(mock_logging_helpers, mock_output):
    """Should display stdout and stderr when command fails."""
    with patch("subprocess.run") as mock_run:
        error = subprocess.CalledProcessError(
            returncode=127, cmd=["missing"], output="", stderr=""
        )
        error.stdout = "some output\n"
        error.stderr = "command not found\n"
        mock_run.side_effect = error

        with pytest.raises(subprocess.CalledProcessError):
            process_helper.run_command_with_error_handling(
                ["missing"], mock_logging_helpers, mock_output
            )

        # Should show stdout
        info_calls = [call.args[0] for call in mock_output.info.call_args_list]
        assert any("some output" in msg for msg in info_calls)
        assert any("command not found" in msg for msg in info_calls)


def test_unexpected_exception_handling(mock_logging_helpers, mock_output):
    """Should handle unexpected exceptions during command execution."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(RuntimeError):
            process_helper.run_command_with_error_handling(
                ["test"], mock_logging_helpers, mock_output, description="Test command"
            )

        # Should log exception
        mock_logging_helpers.log_exception.assert_called()
        exception_call = mock_logging_helpers.log_exception.call_args
        assert isinstance(exception_call.args[0], RuntimeError)
        assert "Unexpected error running" in exception_call.args[1]

        # Should display error to user
        mock_output.error.assert_called()


def test_passes_kwargs_to_subprocess_run(mock_logging_helpers, mock_output):
    """Should pass additional kwargs to subprocess.run()."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["test"], returncode=0, stdout="", stderr=""
        )

        process_helper.run_command_with_error_handling(
            ["test"],
            mock_logging_helpers,
            mock_output,
            env={"VAR": "value"},
            cwd="/tmp",
        )

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["env"] == {"VAR": "value"}
        assert call_kwargs["cwd"] == "/tmp"


@pytest.mark.parametrize(
    "kwargs,expected_subprocess_kwargs",
    [
        # Default timeout is 300 seconds
        ({}, {"timeout": 300, "capture_output": True, "text": True, "check": True}),
        # Custom timeout
        (
            {"timeout": 60},
            {"timeout": 60, "capture_output": True, "text": True, "check": True},
        ),
        # Custom timeout with other kwargs
        (
            {"timeout": 120, "env": {"VAR": "val"}},
            {
                "timeout": 120,
                "capture_output": True,
                "text": True,
                "check": True,
                "env": {"VAR": "val"},
            },
        ),
    ],
    ids=["default_timeout", "custom_timeout", "timeout_with_env"],
)
def test_subprocess_run_kwargs(
    mock_logging_helpers, mock_output, kwargs, expected_subprocess_kwargs
):
    """Should pass correct kwargs to subprocess.run() including defaults."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["test"], returncode=0, stdout="", stderr=""
        )

        process_helper.run_command_with_error_handling(
            ["test"], mock_logging_helpers, mock_output, **kwargs
        )

        call_kwargs = mock_run.call_args.kwargs
        for key, expected_value in expected_subprocess_kwargs.items():
            assert call_kwargs[key] == expected_value


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.integration
def test_real_command_execution(mock_logging_helpers, mock_output):
    """Should execute real commands and return actual results."""
    result = process_helper.run_command_with_error_handling(
        ["echo", "integration test"],
        mock_logging_helpers,
        mock_output,
        description="Echo test",
    )

    assert result.returncode == 0
    assert "integration test" in result.stdout
    assert result.stderr == ""
    mock_logging_helpers.log_info.assert_called_with("command_starting")
    mock_logging_helpers.log_subprocess_result.assert_called_once()


@pytest.mark.integration
def test_command_with_stderr(mock_logging_helpers, mock_output):
    """Should capture stderr from real commands."""
    # Use python to write to stderr
    result = process_helper.run_command_with_error_handling(
        ["python3", "-c", "import sys; sys.stderr.write('error message\\n')"],
        mock_logging_helpers,
        mock_output,
    )

    assert result.returncode == 0
    assert "error message" in result.stderr


@pytest.mark.integration
def test_failing_command_raises_error(mock_logging_helpers, mock_output):
    """Should raise CalledProcessError for failing commands."""
    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        process_helper.run_command_with_error_handling(
            ["false"],  # Command that always fails
            mock_logging_helpers,
            mock_output,
            description="Failing command",
        )

    assert exc_info.value.returncode != 0
    mock_logging_helpers.log_exception.assert_called()


@pytest.mark.integration
def test_real_timeout(mock_logging_helpers, mock_output):
    """Should timeout on slow commands."""
    with pytest.raises(subprocess.TimeoutExpired):
        process_helper.run_command_with_error_handling(
            ["sleep", "10"],
            mock_logging_helpers,
            mock_output,
            description="Slow command",
            timeout=1,  # Very short timeout (1 second)
        )

    mock_logging_helpers.log_exception.assert_called()
    mock_output.error.assert_called()
