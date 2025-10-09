"""Tests for output_formatting.py - Rich-based console output."""

from dotfiles.output_formatting import ConsoleOutput
import pytest
from unittest.mock import patch
from rich.table import Table


@pytest.fixture
def output():
    """ConsoleOutput instance for testing."""
    return ConsoleOutput()


@pytest.fixture
def quiet_output():
    """ConsoleOutput instance in quiet mode."""
    return ConsoleOutput(quiet=True)


@pytest.fixture
def non_verbose_output():
    """ConsoleOutput instance with verbose=False."""
    return ConsoleOutput(verbose=False, quiet=False)


# ==============================================================================
# ConsoleOutput Initialization Tests
# ==============================================================================


@pytest.mark.parametrize(
    "verbose,quiet,expected_verbose,expected_quiet",
    [
        # Default values
        (None, None, True, False),
        # Custom flags
        (False, True, False, True),
        # All combinations
        (True, True, True, True),
        (False, False, False, False),
    ],
    ids=["defaults", "both_custom", "verbose_and_quiet", "both_false"],
)
def test_console_output_initialization(
    verbose, quiet, expected_verbose, expected_quiet
):
    """ConsoleOutput should initialize with correct verbose and quiet flags."""
    # Create output with specified flags (or defaults if None)
    if verbose is None and quiet is None:
        output = ConsoleOutput()
    else:
        kwargs = {}
        if verbose is not None:
            kwargs["verbose"] = verbose
        if quiet is not None:
            kwargs["quiet"] = quiet
        output = ConsoleOutput(**kwargs)

    assert output.verbose is expected_verbose
    assert output.quiet is expected_quiet
    assert output.console is not None  # Always has console instance


# ==============================================================================
# status() Method Tests
# ==============================================================================


def test_status_prints_message_with_default_emoji(output):
    """status() should print message with default emoji."""
    with patch.object(output.console, "print") as mock_print:
        output.status("Checking status")
        mock_print.assert_called_once_with("🔍 Checking status")


def test_status_with_custom_emoji(output):
    """status() should use custom emoji when provided."""
    with patch.object(output.console, "print") as mock_print:
        output.status("Building project", emoji="🔨")
        mock_print.assert_called_once_with("🔨 Building project")


def test_status_respects_quiet_mode(quiet_output):
    """status() should not print when quiet=True."""
    with patch.object(quiet_output.console, "print") as mock_print:
        quiet_output.status("Should not print")
        mock_print.assert_not_called()


def test_status_logs_when_logger_provided(output, logger):
    """status() should call logger.log_info() when logger is provided."""
    with patch.object(output.console, "print"):
        output.status("Checking", logger=logger)
        logger.log_info.assert_called_once_with("Checking")


# ==============================================================================
# success() Method Tests
# ==============================================================================


def test_success_prints_green_with_default_emoji(output):
    """success() should print green message with checkmark."""
    with patch.object(output.console, "print") as mock_print:
        output.success("Operation successful")
        mock_print.assert_called_once_with("✅ Operation successful", style="green")


def test_success_with_custom_emoji(output):
    """success() should use custom emoji."""
    with patch.object(output.console, "print") as mock_print:
        output.success("Done", emoji="🎉")
        mock_print.assert_called_once_with("🎉 Done", style="green")


def test_success_respects_quiet_mode(quiet_output):
    """success() should not print when quiet=True."""
    with patch.object(quiet_output.console, "print") as mock_print:
        quiet_output.success("Should not print")
        mock_print.assert_not_called()


def test_success_logs_when_logger_provided(output, logger):
    """success() should log when logger is provided."""
    with patch.object(output.console, "print"):
        output.success("Success", logger=logger)
        logger.log_info.assert_called_once_with("Success")


# ==============================================================================
# error() Method Tests
# ==============================================================================


def test_error_prints_red_with_default_emoji(output):
    """error() should print red message with X emoji."""
    with patch.object(output.console, "print") as mock_print:
        output.error("Operation failed")
        mock_print.assert_called_once_with("❌ Operation failed", style="red")


def test_error_with_custom_emoji(output):
    """error() should use custom emoji."""
    with patch.object(output.console, "print") as mock_print:
        output.error("Failed", emoji="💥")
        mock_print.assert_called_once_with("💥 Failed", style="red")


def test_error_respects_quiet_mode(quiet_output):
    """error() should not print when quiet=True."""
    with patch.object(quiet_output.console, "print") as mock_print:
        quiet_output.error("Should not print")
        mock_print.assert_not_called()


def test_error_logs_when_logger_provided(output, logger):
    """error() should call logger.log_error() when logger is provided."""
    with patch.object(output.console, "print"):
        output.error("Error occurred", logger=logger)
        logger.log_error.assert_called_once_with("Error occurred")


# ==============================================================================
# warning() Method Tests
# ==============================================================================


def test_warning_prints_yellow_with_default_emoji(output):
    """warning() should print yellow message with warning emoji."""
    with patch.object(output.console, "print") as mock_print:
        output.warning("Be careful")
        mock_print.assert_called_once_with("⚠️ Be careful", style="yellow")


def test_warning_with_custom_emoji(output):
    """warning() should use custom emoji."""
    with patch.object(output.console, "print") as mock_print:
        output.warning("Caution", emoji="🚨")
        mock_print.assert_called_once_with("🚨 Caution", style="yellow")


def test_warning_respects_quiet_mode(quiet_output):
    """warning() should not print when quiet=True."""
    with patch.object(quiet_output.console, "print") as mock_print:
        quiet_output.warning("Should not print")
        mock_print.assert_not_called()


def test_warning_logs_when_logger_provided(output, logger):
    """warning() should call logger.log_warning()."""
    with patch.object(output.console, "print"):
        output.warning("Warning", logger=logger)
        logger.log_warning.assert_called_once_with("Warning")


# ==============================================================================
# info() Method Tests
# ==============================================================================


# TODO: REVIEW
def test_info_prints_blue_with_default_emoji(output):
    """info() should print blue message with bulb emoji."""
    with patch.object(output.console, "print") as mock_print:
        output.info("Some information")
        mock_print.assert_called_once_with("💡 Some information", style="blue")


# TODO: REVIEW
def test_info_with_custom_emoji(output):
    """info() should use custom emoji."""
    with patch.object(output.console, "print") as mock_print:
        output.info("Info", emoji="📝")
        mock_print.assert_called_once_with("📝 Info", style="blue")


def test_info_respects_quiet_mode(quiet_output):
    """info() should not print when quiet=True."""
    with patch.object(quiet_output.console, "print") as mock_print:
        quiet_output.info("Should not print")
        mock_print.assert_not_called()


def test_info_respects_verbose_mode(non_verbose_output):
    """info() should not print when verbose=False."""
    with patch.object(non_verbose_output.console, "print") as mock_print:
        non_verbose_output.info("Should not print")
        mock_print.assert_not_called()


def test_info_requires_both_verbose_and_not_quiet(output):
    """info() should only print when verbose=True and quiet=False."""
    # verbose=True, quiet=False -> prints
    with patch.object(output.console, "print") as mock_print:
        output.info("Should print")
        assert mock_print.called


def test_info_logs_when_logger_provided(non_verbose_output, logger):
    """info() should log even if not printed."""
    with patch.object(non_verbose_output.console, "print"):
        non_verbose_output.info("Info", logger=logger)
        logger.log_info.assert_called_once_with("Info")


# ==============================================================================
# header() Method Tests
# ==============================================================================


def test_header_prints_title_with_separator(output):
    """header() should print title with underline separator."""
    with patch.object(output.console, "print") as mock_print:
        output.header("Section Title")

        # Should print title and separator
        assert mock_print.call_count == 2
        calls = [call.args[0] for call in mock_print.call_args_list]
        assert "📊 Section Title" in calls[0]
        assert "=" in calls[1]


def test_header_with_custom_emoji(output):
    """header() should use custom emoji."""
    with patch.object(output.console, "print") as mock_print:
        output.header("Test", emoji="🔧")
        calls = [call.args[0] for call in mock_print.call_args_list]
        assert "🔧 Test" in calls[0]


def test_header_respects_quiet_mode(quiet_output):
    """header() should not print when quiet=True."""
    with patch.object(quiet_output.console, "print") as mock_print:
        quiet_output.header("Should not print")
        mock_print.assert_not_called()


def test_header_separator_length_matches_title(output):
    """header() separator should match title length plus emoji."""
    with patch.object(output.console, "print") as mock_print:
        output.header("Test")
        separator = mock_print.call_args_list[1].args[0]
        # "📊 Test" = 3 chars for emoji + space + 4 for "Test" = 7
        # But we use len(title) + 3
        assert len(separator) == len("Test") + 3


# ==============================================================================
# table() Method Tests
# ==============================================================================


def test_table_creates_rich_table(output):
    """table() should create and print a Rich table."""
    with patch.object(output.console, "print") as mock_print:
        output.table(
            title="Test Table",
            columns=["Name", "Value"],
            rows=[["foo", "bar"], ["baz", "qux"]],
        )

        # Should call print once with a Table object
        mock_print.assert_called_once()
        printed_obj = mock_print.call_args.args[0]
        assert isinstance(printed_obj, Table)


def test_table_with_custom_emoji(output):
    """table() should include emoji in title."""
    with patch.object(output.console, "print") as mock_print:
        output.table("Data", ["Col"], [[1]], emoji="📈")

        table = mock_print.call_args.args[0]
        assert "📈 Data" in str(table.title)


def test_table_respects_quiet_mode(quiet_output):
    """table() should not print when quiet=True."""
    with patch.object(quiet_output.console, "print") as mock_print:
        quiet_output.table("Test", ["Col"], [[1]])
        mock_print.assert_not_called()


# ==============================================================================
# progress_context() Method Tests
# ==============================================================================


def test_progress_context_returns_progress_object(output):
    """progress_context() should return a Rich Progress object."""
    progress = output.progress_context()

    from rich.progress import Progress

    assert isinstance(progress, Progress)


def test_progress_context_respects_quiet_mode(quiet_output):
    """progress_context() should be disabled when quiet=True."""
    progress = quiet_output.progress_context()

    assert progress.disable is True


def test_progress_context_enabled_when_not_quiet(output):
    """progress_context() should be enabled when quiet=False."""
    progress = output.progress_context()

    assert progress.disable is False


# ==============================================================================
# json() Method Tests
# ==============================================================================


def test_json_prints_data(output):
    """json() should print JSON data using rich_print."""
    with patch("dotfiles.output_formatting.rich_print") as mock_rich_print:
        data = {"key": "value", "count": 42}
        output.json(data)
        mock_rich_print.assert_called_once_with(data)


def test_json_respects_quiet_mode(quiet_output):
    """json() should not print when quiet=True."""
    with patch("dotfiles.output_formatting.rich_print") as mock_rich_print:
        quiet_output.json({"key": "value"})
        mock_rich_print.assert_not_called()


def test_json_with_complex_data(output):
    """json() should handle complex nested data structures."""
    with patch("dotfiles.output_formatting.rich_print") as mock_rich_print:
        data = {
            "users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
            "meta": {"count": 2, "page": 1},
        }
        output.json(data)
        mock_rich_print.assert_called_once_with(data)
