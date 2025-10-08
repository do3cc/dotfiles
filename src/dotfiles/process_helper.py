# pyright: strict

import subprocess
from .logging_config import LoggingHelpers
from .output_formatting import ConsoleOutput
from typing import Any


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
