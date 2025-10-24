# pyright: strict
"""
Rich-based console output formatting for dotfiles Python tools.

Provides consistent styling and formatting across all tools.
Separated from logging to maintain single responsibility principle.
"""

from __future__ import annotations

from contextlib import contextmanager
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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .logging_config import LoggingHelpers


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
        self._active_progress: Progress | None = None  # Track active progress display

    def status(
        self, message: str, emoji: str = "🔍", logger: LoggingHelpers | None = None
    ) -> None:
        """Display a status message with emoji."""
        logger.log_info(message) if logger else None
        if not self.quiet:
            self.console.print(f"{emoji} {message}")

    def success(
        self, message: str, emoji: str = "✅", logger: LoggingHelpers | None = None
    ) -> None:
        """Display a success message."""
        logger.log_info(message) if logger else None
        if not self.quiet:
            self.console.print(f"{emoji} {message}", style="green")

    def error(
        self, message: str, emoji: str = "❌", logger: LoggingHelpers | None = None
    ) -> None:
        """Display an error message."""
        logger.log_error(message) if logger else None
        if not self.quiet:
            self.console.print(f"{emoji} {message}", style="red")

    def warning(
        self, message: str, emoji: str = "⚠️", logger: LoggingHelpers | None = None
    ) -> None:
        """Display a warning message."""
        logger.log_warning(message) if logger else None
        if not self.quiet:
            self.console.print(f"{emoji} {message}", style="yellow")

    def info(
        self, message: str, emoji: str = "💡", logger: LoggingHelpers | None = None
    ) -> None:
        """Display an info message."""
        logger.log_info(message) if logger else None
        if not self.quiet and self.verbose:
            self.console.print(f"{emoji} {message}", style="blue")

    def header(self, title: str, emoji: str = "📊") -> None:
        """Display a section header."""
        if not self.quiet:
            self.console.print(f"\n{emoji} {title}", style="bold cyan")
            self.console.print("=" * (len(title) + 3))

    def table(
        self,
        title: str,
        columns: list[str],
        rows: list[list[Any]],
        emoji: str = "📋",
    ) -> None:
        """Display a formatted table."""
        if not self.quiet:
            table = Table(title=f"{emoji} {title}")

            for column in columns:
                table.add_column(column, style="cyan")

            for row in rows:
                table.add_row(*[str(cell) for cell in row])

            self.console.print(table)

    @contextmanager
    def progress_context(self):
        """Return a Rich progress context for long operations."""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            disable=self.quiet,
        )
        # Store reference so pause_for_interactive() can stop it
        self._active_progress = progress
        try:
            with progress:
                yield progress
        finally:
            self._active_progress = None

    def json(self, data: Any) -> None:
        """Pretty print JSON data."""
        if not self.quiet:
            rich_print(data)

    @contextmanager
    def pause_for_interactive(self):
        """Pause Rich live displays for interactive command execution

        This context manager stops any active Rich displays (progress bars,
        live status, etc.) to allow raw terminal I/O for interactive commands
        like sudo password prompts.

        Usage:
            with output.pause_for_interactive():
                # Interactive command runs here with clean terminal I/O
                subprocess.run(["sudo", "command"])
        """
        # Stop the active progress display to show password prompt
        if self._active_progress is not None:
            self._active_progress.stop()

        # Flush any pending Rich output
        self.console.file.flush()

        try:
            yield
        finally:
            # Restart the progress display
            if self._active_progress is not None:
                self._active_progress.start()
            # Rich automatically resumes on context exit
            self.console.file.flush()
