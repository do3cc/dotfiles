# pyright: strict
"""
Shared logging configuration for all dotfiles Python tools.

Provides structured JSON logging to rotating files with context support.
Logs go to files only - use output_formatting module for user interaction.
"""

import enum
import logging
import os
import shlex
import subprocess
from collections.abc import Sequence
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, cast

import structlog
from structlog.typing import EventDict, WrappedLogger

# The first keys of every log line, in this order; the rest follows as logged
LOG_KEY_ORDER = ["timestamp", "level", "event", "script", "pid"]


def _logfmt_value(key: str, value: object) -> object:
    """Make a value readable and greppable in logfmt.

    logfmt has no lists, enums or null: lists would show up as quoted Python
    reprs, enums as ``T.SYSTEM`` and None as an empty value.
    """
    if value is None:
        return "null"
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        items = [str(_logfmt_value(key, item)) for item in sequence]
        # shlex.join keeps arguments with spaces unambiguous in a command
        return shlex.join(items) if key == "command" else ",".join(items)
    return value


def normalize_logfmt_values(
    _logger: WrappedLogger, _method_name: str, event_dict: EventDict
) -> EventDict:
    """structlog processor: apply _logfmt_value to every value."""
    return {key: _logfmt_value(key, value) for key, value in event_dict.items()}


def setup_logging(
    script_name: str, verbose: bool = False, log_dir: Path | None = None
) -> "LoggingHelpers":
    """
    Configure structured logging and return ready-to-use LoggingHelpers instance.

    Args:
        script_name: Name of the script (e.g., "init", "swman", "pkgstatus")
        verbose: Log at debug level instead of info level
        log_dir: Directory for the log file (default: ~/.cache/dotfiles/logs)

    Returns:
        LoggingHelpers instance ready for use
    """
    if log_dir is None:
        log_dir = Path.home() / ".cache/dotfiles/logs"

    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "dotfiles.log"

    # Clear any existing handlers to avoid duplicates
    logging.getLogger().handlers.clear()

    # Configure standard library logging with rotating file handler
    logging.basicConfig(
        handlers=[
            RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
        ],
        format="%(message)s",
        level=logging.DEBUG if verbose else logging.INFO,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.CallsiteParameterAdder(
                parameters=[structlog.processors.CallsiteParameter.FILENAME]
            ),
            structlog.processors.format_exc_info,
            normalize_logfmt_values,
            structlog.processors.LogfmtRenderer(
                key_order=LOG_KEY_ORDER,
                sort_keys=False,
                bool_as_flag=False,
            ),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Create logger with script context
    logger = structlog.get_logger()
    logger = logger.bind(script=script_name, pid=os.getpid())

    # Return LoggingHelpers instance instead of raw logger
    return LoggingHelpers(logger, log_file)


class LoggingHelpers:
    """
    Helper class for common logging operations that takes a logger instance.

    Follows Hynek's principle of explicit dependency injection instead of global state.
    """

    logger: structlog.BoundLogger
    log_file: Path | None

    def __init__(self, logger: structlog.BoundLogger, log_file: Path | None = None):
        self.logger = logger
        self.log_file = log_file

    def bind(self, **kwargs: object) -> "LoggingHelpers":
        return LoggingHelpers(self.logger.bind(**kwargs), self.log_file)

    def log_error(self, message: str, **context: object) -> None:
        """Log error with context."""
        self.logger.error(message, **context)

    def log_warning(self, message: str, **context: object) -> None:
        """Log warning with context."""
        self.logger.warning(message, **context)

    def log_info(self, message: str, **context: object) -> None:
        """Log info with context."""
        self.logger.info(message, **context)

    def log_debug(self, message: str, **context: object) -> None:
        """Log debug with context."""
        self.logger.debug(message, **context)

    def log_progress(self, message: str, **context: object) -> None:
        """Log progress/status information."""
        self.logger.info("progress", message=message, **context)

    def log_subprocess_result(
        self,
        description: str,
        command: list[str],
        result: subprocess.CompletedProcess[str],
        **context: dict[str, Any],
    ) -> None:
        """
        Log comprehensive subprocess execution details.

        Args:
            description: Human readable description of the command
            command: The command that was executed
            result: subprocess.CompletedProcess result
            **context: Additional context
        """
        base_data = {
            "operation": "subprocess",
            "description": description,
            "command": command,
            "returncode": result.returncode,
            **context,
        }
        logger = self.logger.bind(**base_data)

        if result.returncode == 0:
            logger.info("subprocess_success")
        else:
            logger.error("subprocess_failed")

        # Always log stdout/stderr for debugging regardless of success
        debug_log = logger.bind(
            stdout=result.stdout.strip(), stderr=result.stderr.strip()
        )
        debug_log.debug("subprocess_output")

    def log_exception(
        self, exception: BaseException, context_msg: str, **context: object
    ) -> None:
        """
        Log exception with full context and traceback.

        Args:
            exception: The exception that occurred
            context_msg: Human readable context about what was happening
            **context: Additional context
        """
        self.logger.error(
            "exception_occurred",
            context=context_msg,
            exc_info=exception,
            **context,
        )
