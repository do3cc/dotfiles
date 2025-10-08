# pyright: strict
"""
Rich-based console output formatting for dotfiles Python tools.

Provides consistent styling and formatting across all tools.
Separated from logging to maintain single responsibility principle.
"""

from __future__ import annotations

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

    def json(self, data: Any) -> None:
        """Pretty print JSON data."""
        if not self.quiet:
            rich_print(data)
