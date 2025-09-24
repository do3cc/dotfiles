"""
Shared logging configuration for all dotfiles Python tools.

Provides structured JSON logging to rotating files with context support.
Logs go to files only - use print() for user interaction.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog


def setup_logging(script_name: str) -> structlog.BoundLogger:
    """
    Configure structured logging for a dotfiles Python tool.

    Args:
        script_name: Name of the script (e.g., "init", "swman", "pkgstatus")

    Returns:
        Configured structlog logger
    """
    # Ensure log directory exists
    log_dir = Path.home() / ".cache" / "dotfiles" / "logs"
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

    return logger


def bind_context(**kwargs) -> None:
    """
    Bind key-value pairs to the global logging context.

    Useful for setting operation-wide context like environment, user, etc.
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys) -> None:
    """
    Remove specific keys from the global logging context.
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """
    Clear all variables from the global logging context.
    """
    structlog.contextvars.clear_contextvars()


def log_unused_variables(logger: structlog.BoundLogger, **variables) -> None:
    """
    Helper to log variables that might be unused in code but useful for debugging.

    This satisfies linters while preserving potentially useful information.

    Args:
        logger: The structlog logger instance
        **variables: Key-value pairs of variables to log as context
    """
    logger.debug("unused_variables_context", **variables)


class LoggingHelpers:
    """
    Helper class for common logging operations that takes a logger instance.

    Follows Hynek's principle of explicit dependency injection instead of global state.
    """

    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger

    def log_error(self, message: str, **context) -> None:
        """Log error with context."""
        self.logger.error(message, **context)

    def log_warning(self, message: str, **context) -> None:
        """Log warning with context."""
        self.logger.warning(message, **context)

    def log_info(self, message: str, **context) -> None:
        """Log info with context."""
        self.logger.info(message, **context)

    def log_progress(self, message: str, **context) -> None:
        """Log progress/status information."""
        self.logger.info("progress", message=message, **context)

    def log_subprocess_result(
        self, description: str, command: list, result, **context
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

        if result.returncode == 0:
            self.logger.info("subprocess_success", **base_data)
        else:
            self.logger.error("subprocess_failed", **base_data)

        # Always log stdout/stderr for debugging regardless of success
        if result.stdout:
            self.logger.debug(
                "subprocess_stdout",
                description=description,
                stdout=result.stdout.strip(),
            )

        if result.stderr:
            self.logger.debug(
                "subprocess_stderr",
                description=description,
                stderr=result.stderr.strip(),
            )

    def log_exception(self, exception: Exception, context_msg: str, **context) -> None:
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
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            **context,
        )

    def log_file_operation(
        self, operation: str, path: str, success: bool, **context
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
        self, manager: str, operation: str, packages: list, success: bool, **context
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
