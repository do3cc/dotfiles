# pyright: strict

import subprocess
from typing import Any
from .logging_config import LoggingHelpers
from .output_formatting import ConsoleOutput


def run_command_with_error_handling(
    command: list[str],
    logger: LoggingHelpers,
    output: ConsoleOutput,
    description: str = "Command",
    timeout: int = 300,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command with comprehensive error handling and logging"""
    logger = logger.bind(description=description, command=command, timeout=timeout)
    logger.log_info("command_starting")

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            **kwargs,
        )

        # Use the new comprehensive subprocess logging
        logger.log_subprocess_result(description, command, result)
        return result

    except subprocess.TimeoutExpired as e:
        logger.log_exception(e, "command timed out")
        output.error(f"ERROR: {description} timed out after {timeout} seconds")
        output.status(f"Command: {' '.join(command)}")
        raise
    except subprocess.CalledProcessError as e:
        logger.log_exception(
            e,
            "command_failed",
            description=description,
            command=command,
            returncode=e.returncode,
            stdout=e.stdout,
            stderr=e.stderr,
        )
        output.error(f"ERROR: {description} failed: {e}")
        output.status(f"Command: {' '.join(command)}")
        if e.stdout:
            output.info(f"STDOUT:\n{e.stdout}", emoji="📄")
        if e.stderr:
            output.info(f"STDERR:\n{e.stderr}", emoji="📄")
        raise
    except Exception as e:
        logger.log_exception(
            e, f"Unexpected error running {description}", command=command
        )
        output.error(f"ERROR: Unexpected error running {description}: {e}")
        output.status(f"Command: {' '.join(command)}")
        raise


def run_interactive_command(
    command: list[str],
    logger: LoggingHelpers,
    output: ConsoleOutput,
    description: str = "Interactive Command",
    timeout: int = 300,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Run an interactive subprocess command (e.g., sudo requiring password)

    Unlike run_command_with_error_handling(), this function does NOT capture
    output, allowing stdin/stdout/stderr to flow naturally to the terminal.
    This enables password prompts and other interactive features.

    Use this for:
    - sudo commands that may require password
    - gh auth login (interactive authentication)
    - tailscale up (interactive setup)
    - Any command requiring user input

    Args:
        command: Command and arguments as list
        logger: Logging helper for structured logs
        output: Console output formatter
        description: Human-readable command description
        timeout: Command timeout in seconds
        **kwargs: Additional subprocess.run() arguments

    Returns:
        CompletedProcess with returncode (no stdout/stderr captured)

    Raises:
        subprocess.TimeoutExpired: Command exceeded timeout
        subprocess.CalledProcessError: Command failed (non-zero exit)
    """
    logger = logger.bind(description=description, command=command, timeout=timeout)
    logger.log_info("interactive_command_starting")

    try:
        with output.pause_for_interactive():
            # No output capture - let terminal I/O flow naturally
            result = subprocess.run(
                command,
                check=True,
                capture_output=False,  # Key difference from run_command_with_error_handling
                text=True,
                timeout=timeout,
                **kwargs,
            )

        logger = logger.bind(returncode=result.returncode)
        logger.log_info("interactive_command_completed")
        return result

    except subprocess.TimeoutExpired as e:
        logger.log_exception(e, "interactive_command_timeout")
        output.error(f"ERROR: {description} timed out after {timeout} seconds")
        output.status(f"Command: {' '.join(command)}")
        raise
    except subprocess.CalledProcessError as e:
        logger.log_exception(
            e,
            "interactive_command_failed",
            description=description,
            command=command,
            returncode=e.returncode,
        )
        output.error(f"ERROR: {description} failed with exit code {e.returncode}")
        output.status(f"Command: {' '.join(command)}")
        # Note: No stdout/stderr in error output since we didn't capture it
        raise
    except Exception as e:
        logger.log_exception(e, "interactive_command_unexpected_error", command=command)
        output.error(f"ERROR: Unexpected error running {description}: {e}")
        output.status(f"Command: {' '.join(command)}")
        raise
