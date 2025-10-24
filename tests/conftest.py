"""Shared pytest fixtures for all test modules."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def temp_home(tmp_path):
    """
    Temporary home directory for testing.

    Returns the tmp_path directly - tests can create whatever subdirectory
    structure they need (e.g., .cache/dotfiles/logs, .config, .ssh, etc.)
    """
    return tmp_path


@pytest.fixture
def unwrapped_logger():
    """
    Mock structlog BoundLogger for testing (internal logger wrapped by LoggingHelpers).

    MagicMock auto-generates attributes (.error, .warning, .info, etc.) on demand.
    We only need to configure bind() to return a new mock for chaining.
    """
    logger = MagicMock()
    logger.bind.return_value = MagicMock()
    return logger


@pytest.fixture
def logger():
    """Simple mock logger for init.py and other modules (not LoggingHelpers)."""
    return MagicMock()


@pytest.fixture
def mock_logging_helpers():
    """
    Mock LoggingHelpers for testing process_helper and similar modules.

    This mocks the LoggingHelpers wrapper class where bind() returns the same
    instance (for method chaining), not a new mock like unwrapped_logger.
    """
    from dotfiles.logging_config import LoggingHelpers

    logger = MagicMock(spec=LoggingHelpers)
    logger.bind.return_value = logger  # Returns self for chaining
    return logger


@pytest.fixture
def output():
    """Mock ConsoleOutput for testing (None for tests that don't need it)."""
    return None
