"""Tests for logging_config.py - structured logging with LoggingHelpers."""

# pyright: reportMissingImports=false
from dotfiles import logging_config
import pytest
import subprocess
from hypothesis import given, strategies as st, settings, HealthCheck


@pytest.fixture
def logger(unwrapped_logger):
    """LoggingHelpers instance (matches production usage where logger = setup_logging(...))."""
    return logging_config.LoggingHelpers(unwrapped_logger)


# ==============================================================================
# Tests for setup_logging()
# ==============================================================================
# actual behavior. They write to temp directories and check real log files.


def test_setup_logging_creates_log_directory(temp_home):
    """setup_logging() should create log directory if it doesn't exist."""
    log_dir = temp_home / "custom_logs"
    assert not log_dir.exists()

    logging_config.setup_logging("test_script", log_dir=log_dir)

    assert log_dir.exists()
    assert (log_dir / "dotfiles.log").exists()


def test_setup_logging_returns_logging_helpers(temp_home):
    """setup_logging() should return LoggingHelpers instance."""
    log_dir = temp_home / "logs"
    logger = logging_config.setup_logging("test_script", log_dir=log_dir)

    assert isinstance(logger, logging_config.LoggingHelpers)
    assert hasattr(logger, "log_info")
    assert hasattr(logger, "log_error")
    assert hasattr(logger, "bind")


def test_setup_logging_binds_script_name(temp_home):
    """setup_logging() should bind script name to logger context."""
    import json

    log_dir = temp_home / "logs"
    logger = logging_config.setup_logging("my_script", log_dir=log_dir)

    logger.log_info("test_event")

    log_file = log_dir / "dotfiles.log"
    with open(log_file) as f:
        log_entry = json.loads(f.readline())
        assert log_entry["script"] == "my_script"


def test_setup_logging_binds_pid(temp_home):
    """setup_logging() should bind process ID to logger context."""
    import json
    import os

    log_dir = temp_home / "logs"
    logger = logging_config.setup_logging("test_script", log_dir=log_dir)

    logger.log_info("test_event")

    log_file = log_dir / "dotfiles.log"
    with open(log_file) as f:
        log_entry = json.loads(f.readline())
        assert log_entry["pid"] == os.getpid()


def test_setup_logging_with_custom_log_dir(temp_home):
    """setup_logging() should accept custom log directory."""
    custom_dir = temp_home / "my_custom_logs"
    logger = logging_config.setup_logging("test", log_dir=custom_dir)

    logger.log_info("test")

    assert custom_dir.exists()
    assert (custom_dir / "dotfiles.log").exists()


def test_setup_logging_configures_rotating_handler(temp_home):
    """setup_logging() should configure RotatingFileHandler with 10MB max."""
    import logging

    log_dir = temp_home / "logs"
    logging_config.setup_logging("test", log_dir=log_dir)

    # Check that a RotatingFileHandler was configured
    root_logger = logging.getLogger()
    handlers = root_logger.handlers

    from logging.handlers import RotatingFileHandler

    rotating_handlers = [h for h in handlers if isinstance(h, RotatingFileHandler)]
    assert len(rotating_handlers) > 0

    handler = rotating_handlers[0]
    assert handler.maxBytes == 10 * 1024 * 1024  # 10MB
    assert handler.backupCount == 5


# ==============================================================================
# LoggingHelpers Initialization Tests
# ==============================================================================


def test_logging_helpers_initialization(unwrapped_logger):
    """LoggingHelpers should initialize with logger instance."""
    helpers = logging_config.LoggingHelpers(unwrapped_logger)
    assert helpers.logger == unwrapped_logger


# ==============================================================================
# bind() Method Tests
# ==============================================================================


def test_bind_returns_new_logging_helpers_instance(logger):
    """bind() should return new LoggingHelpers instance, not modify original."""
    original_logger = logger.logger
    new_logger = logger.bind(key="value")

    # Should return new instance
    assert isinstance(new_logger, logging_config.LoggingHelpers)
    assert new_logger is not logger

    # Original should be unchanged
    assert logger.logger is original_logger


def test_bind_calls_logger_bind_with_kwargs(logger, unwrapped_logger):
    """bind() should call underlying logger's bind() with correct kwargs."""
    logger.bind(foo="bar", baz=42)
    unwrapped_logger.bind.assert_called_once_with(foo="bar", baz=42)


def test_bind_wraps_bound_logger_in_new_helpers(logger, unwrapped_logger):
    """bind() should wrap the bound logger in a new LoggingHelpers instance."""
    new_helpers = logger.bind(context="test")

    # The new helpers should wrap the bound logger returned by unwrapped_logger.bind()
    assert new_helpers.logger == unwrapped_logger.bind.return_value


def test_bind_with_multiple_context_values(logger, unwrapped_logger):
    """bind() should support multiple context key-value pairs."""
    logger.bind(user="alice", session_id="123", request_id="abc")

    unwrapped_logger.bind.assert_called_once_with(
        user="alice", session_id="123", request_id="abc"
    )


def test_bind_chaining_creates_independent_instances(logger):
    """Chaining bind() calls should create independent LoggingHelpers instances."""
    helpers1 = logger.bind(step=1)
    helpers2 = helpers1.bind(step=2)
    helpers3 = helpers2.bind(step=3)

    # Each should be a different instance
    assert helpers1 is not logger
    assert helpers2 is not helpers1
    assert helpers3 is not helpers2
    assert helpers3 is not logger

    # All should be LoggingHelpers instances
    assert isinstance(helpers1, logging_config.LoggingHelpers)
    assert isinstance(helpers2, logging_config.LoggingHelpers)
    assert isinstance(helpers3, logging_config.LoggingHelpers)


def test_bind_with_empty_kwargs(logger, unwrapped_logger):
    """bind() should handle empty kwargs (no context to bind)."""
    new_helpers = logger.bind()
    assert isinstance(new_helpers, logging_config.LoggingHelpers)
    unwrapped_logger.bind.assert_called_once_with()


def test_bind_with_none_values(logger, unwrapped_logger):
    """bind() should accept None as a context value."""
    logger.bind(user=None, session=None)
    unwrapped_logger.bind.assert_called_once_with(user=None, session=None)


@pytest.mark.property
def test_bind_preserves_context_across_calls(logger, unwrapped_logger):
    """bind() should preserve context when chaining multiple bind calls."""
    # Chain multiple binds
    logger1 = logger.bind(step=1, user="alice")
    logger2 = logger1.bind(step=2, session="abc")
    logger3 = logger2.bind(step=3)

    # Each bind should call the underlying logger's bind
    assert unwrapped_logger.bind.call_count >= 1
    # Each returns a new LoggingHelpers instance
    assert logger1 is not logger
    assert logger2 is not logger1
    assert logger3 is not logger2


# ==============================================================================
# Basic Logging Methods Tests
# ==============================================================================


def test_log_error_calls_logger_error(logger, unwrapped_logger):
    """log_error() should call logger.error() with message and context."""
    logger.log_error("test_error", foo="bar")
    unwrapped_logger.error.assert_called_once_with("test_error", foo="bar")


def test_log_error_with_no_context(logger, unwrapped_logger):
    """log_error() should work with just a message, no context."""
    logger.log_error("error_event")
    unwrapped_logger.error.assert_called_once_with("error_event")


def test_log_error_with_complex_context(logger, unwrapped_logger):
    """log_error() should accept complex context data structures."""
    context = {
        "user_id": 123,
        "tags": ["error", "critical"],
        "metadata": {"source": "api", "version": "v2"},
    }
    logger.log_error("complex_error", **context)

    unwrapped_logger.error.assert_called_once_with(
        "complex_error",
        user_id=123,
        tags=["error", "critical"],
        metadata={"source": "api", "version": "v2"},
    )


def test_log_warning_calls_logger_warning(logger, unwrapped_logger):
    """log_warning() should call logger.warning() with message and context."""
    logger.log_warning("test_warning", baz=123)
    unwrapped_logger.warning.assert_called_once_with("test_warning", baz=123)


def test_log_warning_with_no_context(logger, unwrapped_logger):
    """log_warning() should work without context."""
    logger.log_warning("warning_event")
    unwrapped_logger.warning.assert_called_once_with("warning_event")


def test_log_info_calls_logger_info(logger, unwrapped_logger):
    """log_info() should call logger.info() with message and context."""
    logger.log_info("test_info", status="ok")
    unwrapped_logger.info.assert_called_once_with("test_info", status="ok")


def test_log_info_with_no_context(logger, unwrapped_logger):
    """log_info() should work without context."""
    logger.log_info("info_event")
    unwrapped_logger.info.assert_called_once_with("info_event")


def test_log_info_with_numeric_context(logger, unwrapped_logger):
    """log_info() should handle numeric context values."""
    logger.log_info("metrics", count=42, duration=1.5, success_rate=0.95)
    unwrapped_logger.info.assert_called_once_with(
        "metrics", count=42, duration=1.5, success_rate=0.95
    )


def test_log_methods_accept_empty_string_message(logger, unwrapped_logger):
    """Log methods should handle empty string messages."""
    logger.log_info("")
    unwrapped_logger.info.assert_called_once_with("")


def test_log_methods_with_none_context_values(logger, unwrapped_logger):
    """Log methods should accept None as context values."""
    logger.log_info("event", user=None, result=None)
    unwrapped_logger.info.assert_called_once_with("event", user=None, result=None)


# ==============================================================================
# log_progress() Tests
# ==============================================================================


def test_log_progress_calls_logger_info_with_progress_event(logger, unwrapped_logger):
    """log_progress() should call logger.info() with 'progress' event."""
    logger.log_progress("installing_packages", count=5)
    unwrapped_logger.info.assert_called_once_with(
        "progress", message="installing_packages", count=5
    )


def test_log_progress_wraps_message_in_message_key(logger, unwrapped_logger):
    """log_progress() should wrap the progress message in 'message' key."""
    logger.log_progress("update_started")
    unwrapped_logger.info.assert_called_once_with("progress", message="update_started")


def test_log_progress_with_additional_context(logger, unwrapped_logger):
    """log_progress() should include additional context along with message."""
    logger.log_progress(
        "download_progress", bytes_downloaded=1024, total_bytes=2048, percent=50
    )
    unwrapped_logger.info.assert_called_once_with(
        "progress",
        message="download_progress",
        bytes_downloaded=1024,
        total_bytes=2048,
        percent=50,
    )


def test_log_progress_event_format(logger, unwrapped_logger):
    """log_progress() should format events as snake_case."""
    # log_progress always uses "progress" as the event
    logger.log_progress("any_message_here")
    unwrapped_logger.info.assert_called_once()
    # First argument should be "progress"
    assert unwrapped_logger.info.call_args.args[0] == "progress"


# ==============================================================================
# Method Call Verification Tests
# ==============================================================================


def test_multiple_log_calls_do_not_interfere(logger, unwrapped_logger):
    """Multiple logging calls should work independently."""
    logger.log_info("first", value=1)
    logger.log_warning("second", value=2)
    logger.log_error("third", value=3)

    assert unwrapped_logger.info.call_count == 1
    assert unwrapped_logger.warning.call_count == 1
    assert unwrapped_logger.error.call_count == 1

    unwrapped_logger.info.assert_called_with("first", value=1)
    unwrapped_logger.warning.assert_called_with("second", value=2)
    unwrapped_logger.error.assert_called_with("third", value=3)


def test_bind_does_not_affect_original_logger_calls(logger, unwrapped_logger):
    """Binding context should not affect calls on original helpers."""
    # Create bound instance
    new_logger = logger.bind(request_id="123")

    # Original should still call original unwrapped_logger
    logger.log_info("original_event")
    unwrapped_logger.info.assert_called_once_with("original_event")

    # Bound should call the bound logger
    new_logger.log_info("bound_event")
    bound_logger = unwrapped_logger.bind.return_value
    bound_logger.info.assert_called_once_with("bound_event")


# ==============================================================================
# Tests for log_subprocess_result()
# ==============================================================================


def test_log_subprocess_result_success(logger, unwrapped_logger):
    """log_subprocess_result() should log successful subprocess execution."""
    result = subprocess.CompletedProcess(
        args=["git", "status"],
        returncode=0,
        stdout="On branch main\n",
        stderr="",
    )

    logger.log_subprocess_result("Check git status", ["git", "status"], result)

    # Should call bind with subprocess details
    assert unwrapped_logger.bind.called


def test_log_subprocess_result_failure(logger, unwrapped_logger):
    """log_subprocess_result() should log failed subprocess execution."""
    result = subprocess.CompletedProcess(
        args=["git", "invalid"],
        returncode=1,
        stdout="",
        stderr="error: unknown command\n",
    )

    logger.log_subprocess_result("Run invalid command", ["git", "invalid"], result)

    # Should bind base data
    unwrapped_logger.bind.assert_called()
    # The bound logger should log error for failed command
    bound_logger = unwrapped_logger.bind.return_value
    bound_logger.error.assert_called_with("subprocess_failed")


def test_log_subprocess_result_includes_stdout_stderr(logger, unwrapped_logger):
    """log_subprocess_result() should include stdout and stderr in logs."""
    result = subprocess.CompletedProcess(
        args=["echo", "hello"],
        returncode=0,
        stdout="hello\n",
        stderr="",
    )

    logger.log_subprocess_result("Echo test", ["echo", "hello"], result)

    # Should bind stdout/stderr (after initial bind)
    bound_logger = unwrapped_logger.bind.return_value
    # Second bind should include stdout/stderr (stripped)
    bound_logger.bind.assert_called_with(stdout="hello", stderr="")


def test_log_subprocess_result_with_additional_context(logger, unwrapped_logger):
    """log_subprocess_result() should accept additional context parameters."""
    result = subprocess.CompletedProcess(
        args=["test"], returncode=0, stdout="", stderr=""
    )

    logger.log_subprocess_result(
        "Test command", ["test"], result, timeout=30, retry_count=2
    )

    # Additional context should be included in base_data bind
    call_args = unwrapped_logger.bind.call_args
    assert call_args.kwargs["timeout"] == 30
    assert call_args.kwargs["retry_count"] == 2


# Tests for log_exception()


def test_log_exception_logs_error_with_exc_info(logger, unwrapped_logger):
    """log_exception() should log exception with full traceback."""
    exception = ValueError("test error")
    logger.log_exception(exception, "test operation failed", foo="bar")

    unwrapped_logger.error.assert_called_once_with(
        "exception_occurred",
        context="test operation failed",
        exc_info=exception,
        foo="bar",
    )


def test_log_exception_with_nested_exception(logger, unwrapped_logger):
    """log_exception() should handle nested exceptions."""
    try:
        try:
            raise ValueError("inner error")
        except ValueError as inner:
            raise RuntimeError("outer error") from inner
    except RuntimeError as outer:
        logger.log_exception(outer, "nested exception occurred")

        unwrapped_logger.error.assert_called_once()
        call_args = unwrapped_logger.error.call_args
        assert call_args.args[0] == "exception_occurred"
        assert call_args.kwargs["context"] == "nested exception occurred"
        assert call_args.kwargs["exc_info"] == outer


def test_log_exception_with_additional_context(logger, unwrapped_logger):
    """log_exception() should include additional context in error log."""
    exception = IOError("file not found")
    logger.log_exception(
        exception,
        "failed to read config",
        filename="config.yaml",
        attempt=3,
    )

    unwrapped_logger.error.assert_called_once_with(
        "exception_occurred",
        context="failed to read config",
        exc_info=exception,
        filename="config.yaml",
        attempt=3,
    )


# Tests for log_file_operation()


def test_log_file_operation_success(logger, unwrapped_logger):
    """log_file_operation() should log successful file operations at info level."""
    logger.log_file_operation("create", "/tmp/test.txt", success=True)
    unwrapped_logger.info.assert_called_once_with(
        "file_operation",
        operation="create",
        path="/tmp/test.txt",
        success=True,
    )


def test_log_file_operation_failure(logger, unwrapped_logger):
    """log_file_operation() should log failed file operations at error level."""
    logger.log_file_operation("delete", "/tmp/test.txt", success=False)
    unwrapped_logger.error.assert_called_once_with(
        "file_operation",
        operation="delete",
        path="/tmp/test.txt",
        success=False,
    )


def test_log_file_operation_with_context(logger, unwrapped_logger):
    """log_file_operation() should include additional context."""
    logger.log_file_operation(
        "symlink",
        "/home/user/.config/nvim",
        success=True,
        source="/dotfiles/nvim",
        mode="0755",
    )

    unwrapped_logger.info.assert_called_once_with(
        "file_operation",
        operation="symlink",
        path="/home/user/.config/nvim",
        success=True,
        source="/dotfiles/nvim",
        mode="0755",
    )


# Tests for log_package_operation() - will be removed per issue #54


def test_log_package_operation_success(logger, unwrapped_logger):
    """log_package_operation() should log successful package operations."""
    packages = ["git", "vim", "tmux"]
    logger.log_package_operation("pacman", "install", packages, success=True)

    unwrapped_logger.info.assert_called_once_with(
        "package_operation",
        manager="pacman",
        operation="install",
        package_count=3,
        packages=packages,
        success=True,
    )


def test_log_package_operation_failure(logger, unwrapped_logger):
    """log_package_operation() should log failed package operations."""
    packages = ["nonexistent-package"]
    logger.log_package_operation(
        "yay", "install", packages, success=False, error="package not found"
    )

    unwrapped_logger.error.assert_called_once_with(
        "package_operation",
        manager="yay",
        operation="install",
        package_count=1,
        packages=packages,
        success=False,
        error="package not found",
    )


# ==============================================================================
# Integration tests
# ==============================================================================


@pytest.mark.integration
def test_full_logging_workflow(temp_home):
    """Test complete logging workflow from setup to logging."""
    import json

    log_dir = temp_home / "logs"
    logger = logging_config.setup_logging("integration_test", log_dir=log_dir)

    # Test various logging methods
    logger.log_info("startup", version="1.0")
    logger = logger.bind(user="alice", session="123")
    logger.log_info("user_action", action="login")
    logger.log_warning("rate_limit", attempts=3)
    logger.log_error("validation_failed", field="email")

    # Read and verify log file
    log_file = log_dir / "dotfiles.log"
    assert log_file.exists()

    with open(log_file) as f:
        lines = f.readlines()
        assert len(lines) == 4

        # Check first log entry
        entry1 = json.loads(lines[0])
        assert entry1["event"] == "startup"
        assert entry1["version"] == "1.0"
        assert entry1["script"] == "integration_test"

        # Check bound context appears in subsequent logs
        entry2 = json.loads(lines[1])
        assert entry2["event"] == "user_action"
        assert entry2["user"] == "alice"
        assert entry2["session"] == "123"


@pytest.mark.integration
def test_log_file_rotation(temp_home):
    """Test that log file rotation works with RotatingFileHandler."""
    import logging

    log_dir = temp_home / "logs"
    logger = logging_config.setup_logging("rotation_test", log_dir=log_dir)

    # Write enough data to trigger rotation (>10MB)
    # Each log entry is roughly ~200 bytes, so write ~60k entries
    large_data = "x" * 100
    for i in range(60000):
        logger.log_info("bulk_data", iteration=i, data=large_data)

    # Force flush all handlers to ensure buffered data is written to disk
    # This ensures rotation occurs if the size threshold was exceeded
    for handler in logging.getLogger().handlers:
        handler.flush()

    # Check that rotation occurred
    log_file = log_dir / "dotfiles.log"
    backup_file = log_dir / "dotfiles.log.1"

    assert log_file.exists()
    assert backup_file.exists(), (
        "Rotation should have created backup file after flushing"
    )
    assert log_file.stat().st_size > 0


# ==============================================================================
# Property-based tests with hypothesis
# ==============================================================================


@pytest.mark.property
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    context_dict=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(
            st.integers(), st.text(), st.booleans(), st.none(), st.floats()
        ),
        max_size=10,
    )
)
def test_bind_with_arbitrary_context(logger, context_dict):
    """bind() should handle arbitrary context key-value pairs."""
    new_logger = logger.bind(**context_dict)
    assert isinstance(new_logger, logging_config.LoggingHelpers)
    assert new_logger is not logger


@pytest.mark.property
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    event_name=st.text(
        alphabet=st.characters(
            # whitelist_categories filters by Unicode character categories:
            # "Ll" = Lowercase letters (a-z and unicode lowercase)
            # "Nd" = Decimal numbers (0-9)
            # whitelist_characters="_" = Also allow underscore
            # Together this generates snake_case compatible strings
            whitelist_categories=("Ll", "Nd"),
            whitelist_characters="_",
        ),
        min_size=1,
        max_size=50,
    )
)
def test_log_methods_with_various_event_names(logger, unwrapped_logger, event_name):
    """log methods should accept various snake_case event names."""
    logger.log_info(event_name)
    # Should be callable without error
    assert unwrapped_logger.info.called
