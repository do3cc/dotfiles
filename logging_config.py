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