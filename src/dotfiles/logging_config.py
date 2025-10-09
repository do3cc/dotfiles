# pyright: strict
"""
Shared logging configuration for all dotfiles Python tools.

Provides structured JSON logging to rotating files with context support.
Logs go to files only - use output_formatting module for user interaction.
"""

import logging
import os
import subprocess
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

from typing import Any


def setup_logging(
    script_name: str, log_dir: Path = Path().home() / ".cache/dotfiles/logs"
) -> "LoggingHelpers":
    """
    Configure structured logging and return ready-to-use LoggingHelpers instance.

    Args:
        script_name: Name of the script (e.g., "init", "swman", "pkgstatus")

    Returns:
        LoggingHelpers instance ready for use
    """
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
        level=logging.INFO,
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
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Create logger with script context
    logger = structlog.get_logger()
    logger = logger.bind(script=script_name, pid=os.getpid())

    # Return LoggingHelpers instance instead of raw logger
    return LoggingHelpers(logger)


class LoggingHelpers:
    """
    Helper class for common logging operations that takes a logger instance.

    Follows Hynek's principle of explicit dependency injection instead of global state.
    """

    logger: structlog.BoundLogger

    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger

    def bind(self, **kwargs: object) -> "LoggingHelpers":
        return LoggingHelpers(self.logger.bind(**kwargs))

    def log_error(self, message: str, **context: object) -> None:
        """Log error with context."""
        self.logger.error(message, **context)

    def log_warning(self, message: str, **context: object) -> None:
        """Log warning with context."""
        self.logger.warning(message, **context)

    def log_info(self, message: str, **context: object) -> None:
        """Log info with context."""
        self.logger.info(message, **context)

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
        debug_log.log_debug("Subprocess output")

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

    def log_file_operation(
        self, operation: str, path: str, success: bool, **context: dict[str, object]
    ) -> None:
        """
        Log file system operations.

        Args:
            operation: Type of operation (create, link, delete, etc.)
            path: File path involved
            success: Whether operation succeeded
            **context: Additional context
        """
        level = "info" if success else "error"
        getattr(self.logger, level)(
            "file_operation", operation=operation, path=path, success=success, **context
        )

    def log_package_operation(
        self,
        manager: str,
        operation: str,
        packages: list[str],
        success: bool,
        **context: dict[str, object],
    ) -> None:
        """
        Log package manager operations.

        Args:
            manager: Package manager name (pacman, yay, apt, etc.)
            operation: Operation type (install, update, check, etc.)
            packages: List of packages involved
            success: Whether operation succeeded
            **context: Additional context
        """
        level = "info" if success else "error"
        getattr(self.logger, level)(
            "package_operation",
            manager=manager,
            operation=operation,
            package_count=len(packages),
            packages=packages[:10],  # Limit to first 10 for readability
            success=success,
            **context,
        )
