#!/usr/bin/env -S uv run python
# pyright: strict
"""
swman - Software Manager Orchestrator

A unified interface to manage updates across multiple package managers
and tools. Designed to work with any system, not just dotfiles.
"""

from subprocess import SubprocessError, TimeoutExpired, CalledProcessError
from abc import ABC, abstractmethod
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import click

from dotfiles.process_helper import run_command_with_error_handling
from .logging_config import LoggingHelpers, setup_logging
from .output_formatting import ConsoleOutput


class ManagerType(Enum):
    SYSTEM = "system"
    LANGUAGE = "language"
    PLUGIN = "plugin"
    TOOL = "tool"


class UpdateStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_AVAILABLE = "not_available"


@dataclass
class UpdateResult:
    name: str
    status: UpdateStatus
    message: str
    duration: float


class PackageManager(ABC):
    def __init__(self, name: str, manager_type: ManagerType) -> None:
        self.name: str = name
        self.type: ManagerType = manager_type

    @abstractmethod
    def is_available(self, logger: LoggingHelpers, output: ConsoleOutput) -> bool:
        """Check if this package manager is available on the system."""
        raise NotImplementedError

    @abstractmethod
    def check_updates(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> tuple[bool, int]:
        """Check for available updates. Returns (has_updates, count)."""
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        logger: LoggingHelpers,
        output: ConsoleOutput,
        dry_run: bool = False,
    ) -> UpdateResult:
        """Perform the update operation."""
        raise NotImplementedError

    @staticmethod
    def _command_exists(
        command: str, logger: LoggingHelpers, output: ConsoleOutput
    ) -> bool:
        try:
            run_command_with_error_handling(
                ["which", command],
                logger=logger,
                output=output,
                description=f"Does command {command} exist?",
            )
            return True
        except CalledProcessError:
            return False

    def bind_log(self, logger: LoggingHelpers):
        return logger.bind(
            package_manager_name=self.name, package_manager_type=self.type
        )


class PacmanManager(PackageManager):
    def __init__(self) -> None:
        super().__init__("pacman", ManagerType.SYSTEM)

    def is_available(self, logger: LoggingHelpers, output: ConsoleOutput) -> bool:
        is_available = self._command_exists("pacman", logger, output)
        logger = self.bind_log(logger)
        logger.log_info("manager_availability_check", is_available=is_available)
        return is_available

    def check_updates(self, logger: LoggingHelpers, output: ConsoleOutput):
        logger = self.bind_log(logger)
        try:
            result = run_command_with_error_handling(
                ["checkupdates"],
                logger=logger,
                output=output,
                description="Pacman check for updates",
                timeout=30,
            )
            logger = logger.bind(returncode=result.returncode, stderr=result.stderr)
            if result.returncode == 0:
                count = (
                    len(result.stdout.strip().split("\n"))
                    if result.stdout.strip()
                    else 0
                )
                logger = logger.bind(updates_count=count)
                logger.log_info("update_check_completed")
                return count > 0, count
            logger.log_error("update_check_failed")
            return False, 0
        except (SubprocessError, FileNotFoundError) as e:
            logger.log_exception(e, "unexpected_exception")
            return False, 0

    def update(
        self, logger: LoggingHelpers, output: ConsoleOutput, dry_run: bool = False
    ) -> UpdateResult:
        logger = self.bind_log(logger)
        start_time = time.time()

        if dry_run:
            has_updates, count = self.check_updates(logger, output)
            logger = logger.bind(has_updates=has_updates, count=count)
            logger.log_info("update_simulated")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message=f"Would update {count} packages",
                duration=time.time() - start_time,
            )

        try:
            # Use streaming output to show real-time pacman progress
            result = run_command_with_error_handling(
                ["sudo", "pacman", "-Syu", "--noconfirm"],
                logger=logger,
                output=output,
                description="Pacman update command",
                timeout=600,
            )
            duration = time.time() - start_time
            logger = logger.bind(
                duration=duration, returncode=result.returncode, stderr=result.stderr
            )

            if result.returncode == 0:
                # Parse output to count actual updates
                logger.log_info("update_completed")
                return UpdateResult(
                    name=self.name,
                    status=UpdateStatus.SUCCESS,
                    message="System packages updated successfully",
                    duration=time.time() - start_time,
                )
            else:
                logger.log_error("update_failed")
                return UpdateResult(
                    name=self.name,
                    status=UpdateStatus.FAILED,
                    message=f"Update failed: {result.stderr}",
                    duration=time.time() - start_time,
                )
        except TimeoutExpired as e:
            logger.log_exception(e, "update_timeout")
            # Show partial output from before timeout
            output.error(
                f"Pacman update timed out after {e.timeout} seconds", logger=logger
            )
            if e.stdout:
                output.info("Partial output before timeout:", emoji="📄")
                # Show last 20 lines of output to see what it was doing
                stdout_str = (
                    e.stdout
                    if isinstance(e.stdout, str)
                    else e.stdout.decode("utf-8", errors="replace")
                )
                lines = stdout_str.strip().splitlines()
                for line in lines[-20:]:
                    output.info(f"  {line}")
            if e.stderr:
                output.warning("Error output:", emoji="⚠️")
                stderr_str = (
                    e.stderr
                    if isinstance(e.stderr, str)
                    else e.stderr.decode("utf-8", errors="replace")
                )
                for line in stderr_str.strip().splitlines():
                    output.warning(f"  {line}")
            output.info(
                "Try: Increase timeout or run 'sudo pacman -Syu' manually to complete",
                emoji="💡",
            )
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Update timed out after {e.timeout}s",
                duration=time.time() - start_time,
            )
        except Exception as e:
            logger.log_exception(e, "unexpected_exception")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Unexpected error: {e}",
                duration=time.time() - start_time,
            )


class YayManager(PackageManager):
    def __init__(self) -> None:
        super().__init__("yay", ManagerType.SYSTEM)

    def is_available(self, logger: LoggingHelpers, output: ConsoleOutput) -> bool:
        logger = self.bind_log(logger)
        is_available = self._command_exists("yay", logger, output)
        logger.log_info("manager_availability_check", is_available=is_available)
        return is_available

    def check_updates(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> tuple[bool, int]:
        logger = self.bind_log(logger)
        try:
            result = run_command_with_error_handling(
                ["yay", "-Qu"],
                logger,
                output,
                description="Yay check for updates",
                timeout=60,
            )
            logger = logger.bind(returncode=result.returncode, stderr=result.stderr)
            if result.returncode == 0:
                count = (
                    len(result.stdout.strip().split("\n"))
                    if result.stdout.strip()
                    else 0
                )
                logger = logger.bind(updates_count=count)
                logger.log_info("update_check_completed")
                return count > 0, count
            logger.log_error("update_check_failed")
            return False, 0
        except (SubprocessError, FileNotFoundError) as e:
            logger.log_exception(e, "unexpected_exception")
            return False, 0

    def update(
        self, logger: LoggingHelpers, output: ConsoleOutput, dry_run: bool = False
    ) -> UpdateResult:
        logger = self.bind_log(logger)
        start_time = time.time()

        if dry_run:
            has_updates, count = self.check_updates(logger, output)
            logger = logger.bind(has_updates=has_updates, count=count)
            logger.log_info("update_simulated")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message=f"Would update {count} AUR packages",
                duration=time.time() - start_time,
            )

        try:
            # Use streaming output to show real-time yay/AUR progress
            timeout = 1800

            result = run_command_with_error_handling(
                ["yay", "-Syu", "--noconfirm"],
                logger,
                output,
                description="Perform update with yay",
                timeout=timeout,
            )
            duration = time.time() - start_time
            logger = logger.bind(
                returncode=result.returncode,
                stderr=result.stderr,
                duration=duration,
                timeout=timeout,
            )

            if result.returncode == 0:
                logger.log_info("update_completed")
                return UpdateResult(
                    name=self.name,
                    status=UpdateStatus.SUCCESS,
                    message="AUR packages updated successfully",
                    duration=duration,
                )
            else:
                logger.log_error("update_failed")
                return UpdateResult(
                    name=self.name,
                    status=UpdateStatus.FAILED,
                    message=f"AUR update failed: {result.stderr}",
                    duration=duration,
                )
        except TimeoutExpired as e:
            logger.log_exception(e, "update_timeout")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message="AUR update timed out",
                duration=time.time() - start_time,
            )
        except Exception as e:
            logger.log_exception(e, "unexpected_exception")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Unexpected error: {e}",
                duration=time.time() - start_time,
            )


class DebianSystemManager(PackageManager):
    """System package manager for Debian/Ubuntu systems using apt"""

    def __init__(self) -> None:
        super().__init__("apt", ManagerType.SYSTEM)

    def is_available(self, logger: LoggingHelpers, output: ConsoleOutput) -> bool:
        logger = self.bind_log(logger)
        is_available = self._command_exists("apt", logger, output)
        logger.log_info("manager_availability_check", is_available=is_available)
        return is_available

    def check_updates(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> tuple[bool, int]:
        """Check for available updates using apt list --upgradable"""
        logger = self.bind_log(logger)
        try:
            # First update the package list
            result = run_command_with_error_handling(
                ["sudo", "apt", "update"],
                logger,
                output,
                description="Update apt cache",
                timeout=60,
            )
            logger = logger.bind(returncode=result.returncode, stderr=result.stderr)
            if result.returncode != 0:
                logger.log_error("cache_update_failed")
                return False, 0

            # Check for upgradable packages

            result = run_command_with_error_handling(
                ["apt", "list", "--upgradable"],
                logger,
                output,
                description="Get packages that can be updated",
                timeout=30,
            )
            logger = logger.bind(returncode=result.returncode, stderr=result.stderr)
            if result.returncode == 0:
                # Count lines excluding header
                lines = result.stdout.strip().split("\n")
                count = len([line for line in lines if "/" in line]) if lines else 0
                logger = logger.bind(updates_count=count)
                logger.log_info("update_check_completed")
                return count > 0, count
            logger.log_error("update_check_failed")
            return False, 0
        except (SubprocessError, FileNotFoundError) as e:
            logger.log_exception(e, "unexpected_exception")
            return False, 0

    def update(
        self, logger: LoggingHelpers, output: ConsoleOutput, dry_run: bool = False
    ) -> UpdateResult:
        """Perform system updates using apt"""
        logger = self.bind_log(logger)
        start_time = time.time()
        logger = logger.bind(start_time=start_time, dry_run=dry_run)
        logger.log_info("update_started")

        if dry_run:
            has_updates, count = self.check_updates(logger, output)
            logger = logger.bind(has_updates=has_updates, count=count)
            logger.log_info("update_simulated")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message=f"Would update {count} packages",
                duration=time.time() - start_time,
            )

        try:
            # First update package lists

            timeout = 300
            result = run_command_with_error_handling(
                ["sudo", "apt", "update"],
                logger,
                output,
                description="Run apt update",
                timeout=timeout,
            )
            duration = time.time() - start_time
            logger = logger.bind(
                returncode=result.returncode,
                stderr=result.stderr,
                timeout=timeout,
                duration=duration,
            )
            if result.returncode != 0:
                logger.log_error("cache_update_failed")
                return UpdateResult(
                    name=self.name,
                    status=UpdateStatus.FAILED,
                    message=f"Package list update failed: {result.stderr}",
                    duration=duration,
                )

            # Then upgrade packages with streaming output

            result = run_command_with_error_handling(
                ["sudo", "apt", "upgrade", "-y"],
                logger,
                output,
                description="Apt upgrade command",
            )
            duration = time.time() - start_time
            logger = logger.bind(
                returncode=result.returncode,
                stderr=result.stderr,
                timeout=timeout,
                duration=duration,
            )

            if result.returncode == 0:
                logger.log_info("update_completed")
                return UpdateResult(
                    name=self.name,
                    status=UpdateStatus.SUCCESS,
                    message="System packages updated successfully",
                    duration=duration,
                )
            else:
                logger.log_error("update_failed")
                return UpdateResult(
                    name=self.name,
                    status=UpdateStatus.FAILED,
                    message=f"Update failed: {result.stderr}",
                    duration=duration,
                )
        except TimeoutExpired as e:
            logger.log_exception(e, "update_timeout")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message="Update timed out",
                duration=time.time() - start_time,
            )
        except Exception as e:
            logger.log_exception(e, "unexpected_exception")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Unexpected error: {e}",
                duration=time.time() - start_time,
            )


class UvToolsManager(PackageManager):
    def __init__(self):
        super().__init__("uv-tools", ManagerType.TOOL)

    def is_available(self, logger: LoggingHelpers, output: ConsoleOutput) -> bool:
        logger = self.bind_log(logger)
        is_available = self._command_exists("uv", logger, output)
        logger.log_info("manager_availability_check", is_available=is_available)
        return is_available

    def check_updates(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> tuple[bool, int]:
        logger = self.bind_log(logger)
        # UV doesn't have a direct "check updates" command yet
        # We'd need to parse `uv tool list` and check each tool
        # Return cannot_determine status instead of false positive
        result = (False, -1)  # -1 indicates "cannot determine"
        del output

        logger.log_info(
            "manager_check_result",
            can_check=False,
            has_updates=result[0],
            count=result[1],
            reason="no_outdated_command_available",
        )

        return result

    def update(
        self, logger: LoggingHelpers, output: ConsoleOutput, dry_run: bool = False
    ) -> UpdateResult:
        logger = self.bind_log(logger)
        start_time = time.time()

        if dry_run:
            logger.log_info("update_simulated")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Would upgrade all uv tools",
                duration=time.time() - start_time,
            )

        try:
            # Use streaming output to show real-time UV tool upgrade progress
            result = run_command_with_error_handling(
                ["uv", "tool", "upgrade", "--all"],
                logger=logger,
                output=output,
                description="Upgrade all uv tools",
                timeout=300,
            )
            duration = time.time() - start_time

            logger = logger.bind(
                returncode=result.returncode, stderr=result.stderr, duration=duration
            )
            if result.returncode == 0:
                logger.log_info("update_completed")
                return UpdateResult(
                    name=self.name,
                    status=UpdateStatus.SUCCESS,
                    message="UV tools updated successfully",
                    duration=duration,
                )
            else:
                logger.log_error("update_failed")
                return UpdateResult(
                    name=self.name,
                    status=UpdateStatus.FAILED,
                    message=f"UV tools update failed: {result.stderr}",
                    duration=time.time() - start_time,
                )
        except Exception as e:
            logger.log_exception(e, "unexpected_exception")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Unexpected error: {e}",
                duration=time.time() - start_time,
            )


class LazyNvimManager(PackageManager):
    def __init__(self):
        super().__init__("lazy.nvim", ManagerType.PLUGIN)

    def is_available(self, logger: LoggingHelpers, output: ConsoleOutput) -> bool:
        logger = self.bind_log(logger)
        is_command_available = self._command_exists("nvim", logger, output)
        lazy_path = Path.home() / ".local/share/nvim/lazy/lazy.nvim"
        logger.log_info(
            "manager_availability_check",
            is_available=is_command_available,
            lazy_path=str(lazy_path),
            lazy_path_exists=lazy_path.exists(),
        )
        return lazy_path.exists() and is_command_available

    def check_updates(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> tuple[bool, int]:
        # Lazy.nvim doesn't provide headless read-only update checking
        # Return cannot_determine status instead of false positive
        logger = self.bind_log(logger)
        del output
        result = (False, -1)  # -1 indicates "cannot determine"

        logger.log_info(
            "manager_check_result",
            can_check=False,
            has_updates=result[0],
            count=result[1],
            reason="no_headless_check_command",
        )

        return result

    def update(
        self, logger: LoggingHelpers, output: ConsoleOutput, dry_run: bool = False
    ) -> UpdateResult:
        logger = self.bind_log(logger)
        start_time = time.time()

        if dry_run:
            logger.log_info("update_simulated")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Would update Neovim plugins",
                duration=time.time() - start_time,
            )

        try:
            # Use streaming output to show real-time Neovim plugin updates

            result = run_command_with_error_handling(
                ["nvim", "--headless", "+Lazy! sync", "+qa"],
                logger,
                output,
                description="update nvim",
            )

            logger = logger.bind(returncode=result.returncode, stderr=result.stderr)
            logger.log_info("update_completed")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Neovim plugins updated",
                duration=time.time() - start_time,
            )
        except Exception as e:
            logger.log_exception(e, "unexpected_exception")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Neovim plugin update failed: {e}",
                duration=time.time() - start_time,
            )


class FisherManager(PackageManager):
    def __init__(self):
        super().__init__("fisher", ManagerType.PLUGIN)

    def is_available(self, logger: LoggingHelpers, output: ConsoleOutput) -> bool:
        logger = self.bind_log(logger)
        is_command_available = self._command_exists("fish", logger, output)
        path = Path.home().joinpath(".config/fish/functions/fisher.fish")
        logger.log_info(
            "manager_availability_check",
            is_available=is_command_available,
            path=str(path),
            path_exists=path.exists(),
        )
        return is_command_available and path.exists()

    def check_updates(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> tuple[bool, int]:
        # Fisher doesn't provide update checking without installation
        # Return cannot_determine status instead of false positive
        logger = self.bind_log(logger)
        del output
        result = (False, -1)  # -1 indicates "cannot determine"

        logger.log_info(
            "manager_check_result",
            can_check=False,
            has_updates=result[0],
            count=result[1],
            reason="no_check_only_command",
        )

        return result

    def update(
        self, logger: LoggingHelpers, output: ConsoleOutput, dry_run: bool = False
    ) -> UpdateResult:
        logger = self.bind_log(logger)
        start_time = time.time()

        if dry_run:
            logger.log_info("update_simulated")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Would update Fish plugins",
                duration=time.time() - start_time,
            )

        try:
            # Use streaming output to show real-time Fish plugin updates

            result = run_command_with_error_handling(
                ["fish", "-c", "fisher update"],
                logger,
                output,
                description="Update Fish plugins",
                timeout=120,
            )
            duration = time.time() - start_time

            logger = logger.bind(
                returncode=result.returncode, stderr=result.stderr, duration=duration
            )
            logger.log_info("update_completed")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Fish plugins updated",
                duration=duration,
            )
        except Exception as e:
            logger.log_exception(e, "unexpected_exception")
            return UpdateResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Fish plugin update failed: {e}",
                duration=time.time() - start_time,
            )


class SoftwareManagerOrchestrator:
    """
    Orchestrates updates across multiple package managers and plugin systems.

    Provides a unified interface to check for updates and perform updates across
    system package managers (pacman, yay, apt), development tools (uv), and
    plugins (lazy.nvim, fisher).

    The orchestrator automatically detects which package managers are available
    on the system and only operates on those that are present.
    """

    def __init__(self):
        self.managers: list[PackageManager] = [
            PacmanManager(),
            YayManager(),
            UvToolsManager(),
            LazyNvimManager(),
            FisherManager(),
        ]

    def get_available_managers(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> list[PackageManager]:
        return [mgr for mgr in self.managers if mgr.is_available(logger, output)]

    def check_all(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> dict[str, tuple[bool, int]]:
        """Check all managers for updates."""
        results: dict[str, tuple[bool, int]] = {}
        for manager in self.get_available_managers(logger, output):
            logger = logger.bind(manager=manager.name)
            try:
                results[manager.name] = manager.check_updates(logger, output)
            except Exception as e:
                logger.log_exception(e, "Error checking for updates")
                results[manager.name] = (False, 0)
        return results

    def update_by_type(
        self,
        manager_type: ManagerType,
        logger: LoggingHelpers,
        output: ConsoleOutput,
        dry_run: bool = False,
    ) -> list[UpdateResult]:
        """Update all managers of a specific type."""
        results: list[UpdateResult] = []
        for manager in self.get_available_managers(logger, output):
            logger = logger.bind(manager=manager.name)
            if manager.type == manager_type:
                try:
                    result = manager.update(logger, output, dry_run)
                    results.append(result)
                    logger = logger.bind(results=results)
                except Exception as e:
                    logger.log_exception(e, "Unexpected exception")
                    results.append(
                        UpdateResult(
                            name=manager.name,
                            status=UpdateStatus.FAILED,
                            message=f"Unexpected error: {e}",
                            duration=0.0,
                        )
                    )
        return results

    def update_all(
        self, logger: LoggingHelpers, output: ConsoleOutput, dry_run: bool = False
    ) -> list[UpdateResult]:
        """Update all available managers."""
        results: list[UpdateResult] = []
        for manager in self.get_available_managers(logger, output):
            logger = logger.bind(manager=manager.name)
            try:
                result = manager.update(logger=logger, output=output, dry_run=dry_run)
                results.append(result)
            except Exception as e:
                results.append(
                    UpdateResult(
                        name=manager.name,
                        status=UpdateStatus.FAILED,
                        message=f"Unexpected error: {e}",
                        duration=0.0,
                    )
                )
        return results


def print_status_table(
    check_results: dict[str, tuple[bool, int]], output: ConsoleOutput
) -> None:
    """Print a nice status table using Rich."""
    rows: list[list[str]] = []
    for manager_name, (has_updates, count) in check_results.items():
        status = "Updates Available" if has_updates else "Up to Date"
        updates_str = str(count) if count > 0 else "-"
        rows.append([manager_name, status, updates_str])

    output.table("Software Manager Status", ["Manager", "Status", "Updates"], rows)


def print_results_summary(results: list[UpdateResult], output: ConsoleOutput) -> None:
    """Print update results summary using Rich."""
    rows: list[list[str]] = []
    for result in results:
        status_icon = {
            UpdateStatus.SUCCESS: "✅",
            UpdateStatus.FAILED: "❌",
            UpdateStatus.SKIPPED: "⏭️",
            UpdateStatus.NOT_AVAILABLE: "⚠️",
        }.get(result.status, "❓")

        duration_str = f"{result.duration:.1f}s" if result.duration > 0 else "-"
        rows.append([status_icon, result.name, result.message, duration_str])

    output.table(
        "Update Results", ["Status", "Manager", "Message", "Duration"], rows, emoji="🔄"
    )


@click.command()
@click.option("--check", is_flag=True, help="Check for updates across all managers")
@click.option(
    "--system", is_flag=True, help="Update system packages only (pacman, yay, apt)"
)
@click.option("--tools", is_flag=True, help="Update development tools (uv, etc.)")
@click.option("--plugins", is_flag=True, help="Update plugins (nvim, fish, tmux)")
@click.option("--all", "update_all", is_flag=True, help="Update everything")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be updated without actually updating",
)
@click.option(
    "--json", "json_output", is_flag=True, help="Output results in JSON format"
)
@click.option("--quiet", is_flag=True, help="Suppress non-essential output")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def main(
    check: bool,
    system: bool,
    tools: bool,
    plugins: bool,
    update_all: bool,
    dry_run: bool,
    json_output: bool,
    quiet: bool,
    verbose: bool,
) -> int:
    """Software Manager Orchestrator - Unified package manager updates"""

    # Initialize logging and console output with CLI context
    logger = setup_logging("swman").bind(
        verbose=verbose,
        quiet=quiet,
        dry_run=dry_run,
        json_output=json_output,
        check=check,
        system=system,
        tools=tools,
        plugins=plugins,
        update_all=update_all,
    )
    output = ConsoleOutput(verbose=verbose, quiet=quiet)
    logger.log_info("swman_started")

    if not any([check, system, tools, plugins, update_all]):
        click.echo("Error: Must specify at least one operation")
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        return 1

    orchestrator = SoftwareManagerOrchestrator()

    if check:
        check_log = logger.bind(operation="check")
        check_log.log_info("operation_started")
        output.status("Checking for updates...")
        check_results = orchestrator.check_all(logger=logger, output=output)
        # check_results is dict[str, tuple[bool, int]] where tuple is (success, updates_count)
        total_updates = sum(
            r[1] for r in check_results.values() if r[0]
        )  # r[1] is updates_count, r[0] is success
        check_log.log_info(
            "operation_completed",
            total_managers=len(check_results),
            managers_with_updates=sum(
                1 for r in check_results.values() if r[0] and r[1] > 0
            ),
            total_updates_available=total_updates,
        )

        if json_output:
            output.json(check_results)
        else:
            print_status_table(check_results, output)
        return 0

    results: list[UpdateResult] = []

    # Set up operation context
    operation_types: list[ManagerType] = []
    if update_all:
        operation_types = [ManagerType.SYSTEM, ManagerType.TOOL, ManagerType.PLUGIN]
    else:
        if system:
            operation_types.append(ManagerType.SYSTEM)
        if tools:
            operation_types.append(ManagerType.TOOL)
        if plugins:
            operation_types.append(ManagerType.PLUGIN)

    logger = logger.bind(operation_types=operation_types, dry_run=dry_run)

    # Execute operations
    for op_type in operation_types:
        op_log = logger.bind(op_type=op_type.name)
        op_log.log_info("op_type_started")
        output.status(f"Updating {op_type.name}")
        op_results = orchestrator.update_by_type(
            op_type, logger=logger, output=output, dry_run=dry_run
        )
        results.extend(op_results)
        op_log.log_info("operation_completed", result_count=len(op_results))

    if json_output:
        output.json(
            [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "duration": r.duration,
                }
                for r in results
            ]
        )
    else:
        print_results_summary(results, output)

    # Log completion and return appropriate exit code
    failed_count = sum(1 for r in results if r.status == UpdateStatus.FAILED)
    success_count = sum(1 for r in results if r.status == UpdateStatus.SUCCESS)

    logger.log_info(
        "swman_completed",
        total_operations=len(results),
        successful=success_count,
        failed=failed_count,
    )

    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
