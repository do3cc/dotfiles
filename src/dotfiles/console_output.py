"""
Console output and logging helper classes for dotfiles Python tools.

Provides Rich-based console output and logging helper abstractions.
"""

import structlog
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table
from rich import print as rich_print


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


# Global console instance for consistent styling
console = Console()


class ConsoleOutput:
    """
    Rich-based console output abstraction that replaces print statements.

    Provides consistent styling and formatting across all tools.
    """

    def __init__(self, verbose: bool = True, quiet: bool = False):
        self.verbose = verbose
        self.quiet = quiet
        self.console = console

    def status(self, message: str, emoji: str = "🔍") -> None:
        """Display a status message with emoji."""
        if not self.quiet:
            self.console.print(f"{emoji} {message}")

    def success(self, message: str, emoji: str = "✅") -> None:
        """Display a success message."""
        if not self.quiet:
            self.console.print(f"{emoji} {message}", style="green")

    def error(self, message: str, emoji: str = "❌") -> None:
        """Display an error message."""
        if not self.quiet:
            self.console.print(f"{emoji} {message}", style="red")

    def warning(self, message: str, emoji: str = "⚠️") -> None:
        """Display a warning message."""
        if not self.quiet:
            self.console.print(f"{emoji} {message}", style="yellow")

    def info(self, message: str, emoji: str = "💡") -> None:
        """Display an info message."""
        if not self.quiet and self.verbose:
            self.console.print(f"{emoji} {message}", style="blue")

    def header(self, title: str, emoji: str = "📊") -> None:
        """Display a section header."""
        if not self.quiet:
            self.console.print(f"\n{emoji} {title}", style="bold cyan")
            self.console.print("=" * (len(title) + 3))

    def table(self, title: str, columns: list, rows: list, emoji: str = "📋") -> None:
        """Display a formatted table."""
        if not self.quiet:
            table = Table(title=f"{emoji} {title}")

            for column in columns:
                table.add_column(column, style="cyan")

            for row in rows:
                table.add_row(*[str(cell) for cell in row])

            self.console.print(table)

    def progress_context(self):
        """Return a Rich progress context for long operations."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            disable=self.quiet,
        )

    def json(self, data) -> None:
        """Pretty print JSON data."""
        if not self.quiet:
            rich_print(data)
