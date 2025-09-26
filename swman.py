#!/usr/bin/env -S uv run python
"""
swman - Software Manager Orchestrator

A unified interface to manage updates across multiple package managers
and tools. Designed to work with any system, not just dotfiles.

KEY IMPROVEMENT: Now shows full package manager output instead of hiding it.
All package update operations (pacman, yay, uv tools, lazy.nvim, fisher)
display real-time progress so users can see what packages are being updated.
"""

import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Tuple

import click
from logging_config import setup_logging, bind_context, LoggingHelpers, ConsoleOutput


def run_with_streaming_output(
    command: List[str], timeout: int = 600
) -> subprocess.CompletedProcess:
    """
    Execute command with real-time output streaming for package managers.

    This function shows full package manager output to users instead of hiding it,
    while still capturing stderr for error handling and maintaining return codes.

    Args:
        command: Command to execute as list of strings
        timeout: Timeout in seconds (default 600 = 10 minutes)

    Returns:
        CompletedProcess with returncode and stderr (stdout flows to terminal)

    Note: This follows the same pattern used in init.py for APT/pacman streaming.
    """
    return subprocess.run(
        command,
        check=False,  # Don't raise exception, let caller handle return codes
        stderr=subprocess.PIPE,  # Capture stderr for error analysis
        text=True,
        timeout=timeout,
    )


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
class ManagerResult:
    name: str
    status: UpdateStatus
    message: str
    duration: float
    updates_available: int = 0
    updates_applied: int = 0


class PackageManager:
    def __init__(self, name: str, manager_type: ManagerType):
        self.name = name
        self.type = manager_type

    def is_available(self) -> bool:
        """Check if this package manager is available on the system."""
        raise NotImplementedError

    def check_updates(self) -> Tuple[bool, int]:
        """Check for available updates. Returns (has_updates, count)."""
        raise NotImplementedError

    def update(self, dry_run: bool = False) -> ManagerResult:
        """Perform the update operation."""
        raise NotImplementedError


class PacmanManager(PackageManager):
    def __init__(self):
        super().__init__("pacman", ManagerType.SYSTEM)

    def is_available(self) -> bool:
        return self._command_exists("pacman")

    def check_updates(self) -> Tuple[bool, int]:
        try:
            result = subprocess.run(
                ["checkupdates"], capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                count = (
                    len(result.stdout.strip().split("\n"))
                    if result.stdout.strip()
                    else 0
                )
                return count > 0, count
            return False, 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False, 0

    def update(self, dry_run: bool = False) -> ManagerResult:
        start_time = time.time()

        if dry_run:
            has_updates, count = self.check_updates()
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message=f"Would update {count} packages",
                duration=time.time() - start_time,
                updates_available=count,
            )

        try:
            # Use streaming output to show real-time pacman progress
            result = run_with_streaming_output(
                ["sudo", "pacman", "-Syu", "--noconfirm"], timeout=600
            )

            if result.returncode == 0:
                # Parse output to count actual updates
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.SUCCESS,
                    message="System packages updated successfully",
                    duration=time.time() - start_time,
                )
            else:
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.FAILED,
                    message=f"Update failed: {result.stderr}",
                    duration=time.time() - start_time,
                )
        except subprocess.TimeoutExpired:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message="Update timed out",
                duration=time.time() - start_time,
            )
        except Exception as e:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Unexpected error: {e}",
                duration=time.time() - start_time,
            )

    @staticmethod
    def _command_exists(command: str) -> bool:
        try:
            subprocess.run(["which", command], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


class YayManager(PackageManager):
    def __init__(self):
        super().__init__("yay", ManagerType.SYSTEM)

    def is_available(self) -> bool:
        return self._command_exists("yay")

    def check_updates(self) -> Tuple[bool, int]:
        try:
            result = subprocess.run(
                ["yay", "-Qu"], capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                count = (
                    len(result.stdout.strip().split("\n"))
                    if result.stdout.strip()
                    else 0
                )
                return count > 0, count
            return False, 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False, 0

    def update(self, dry_run: bool = False) -> ManagerResult:
        start_time = time.time()

        if dry_run:
            has_updates, count = self.check_updates()
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message=f"Would update {count} AUR packages",
                duration=time.time() - start_time,
                updates_available=count,
            )

        try:
            # Use streaming output to show real-time yay/AUR progress
            result = run_with_streaming_output(
                ["yay", "-Syu", "--noconfirm"],
                timeout=1800,  # 30 minutes for AUR builds
            )

            if result.returncode == 0:
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.SUCCESS,
                    message="AUR packages updated successfully",
                    duration=time.time() - start_time,
                )
            else:
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.FAILED,
                    message=f"AUR update failed: {result.stderr}",
                    duration=time.time() - start_time,
                )
        except subprocess.TimeoutExpired:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message="AUR update timed out",
                duration=time.time() - start_time,
            )
        except Exception as e:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Unexpected error: {e}",
                duration=time.time() - start_time,
            )

    @staticmethod
    def _command_exists(command: str) -> bool:
        try:
            subprocess.run(["which", command], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


class UvToolsManager(PackageManager):
    def __init__(self):
        super().__init__("uv-tools", ManagerType.TOOL)

    def is_available(self) -> bool:
        return self._command_exists("uv")

    def check_updates(self) -> Tuple[bool, int]:
        """Check for UV tool updates.

        UV doesn't provide a simple way to check for tool updates without actually
        updating them. To avoid false positives during shell startup checks,
        we return False to indicate no updates are available for checking.

        Users should manually run 'uv tool upgrade --all' or use swman --tools.
        """
        return False, 0  # Cannot check UV tool updates without updating

    def update(self, dry_run: bool = False) -> ManagerResult:
        start_time = time.time()

        if dry_run:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Would upgrade all uv tools",
                duration=time.time() - start_time,
            )

        try:
            # Use streaming output to show real-time UV tool upgrade progress
            result = run_with_streaming_output(
                ["uv", "tool", "upgrade", "--all"], timeout=300
            )

            if result.returncode == 0:
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.SUCCESS,
                    message="UV tools updated successfully",
                    duration=time.time() - start_time,
                )
            else:
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.FAILED,
                    message=f"UV tools update failed: {result.stderr}",
                    duration=time.time() - start_time,
                )
        except Exception as e:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Unexpected error: {e}",
                duration=time.time() - start_time,
            )

    @staticmethod
    def _command_exists(command: str) -> bool:
        try:
            subprocess.run(["which", command], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


class LazyNvimManager(PackageManager):
    def __init__(self):
        super().__init__("lazy.nvim", ManagerType.PLUGIN)

    def is_available(self) -> bool:
        lazy_path = Path.home() / ".local/share/nvim/lazy/lazy.nvim"
        return lazy_path.exists() and self._command_exists("nvim")

    def check_updates(self) -> Tuple[bool, int]:
        """Check for Neovim plugin updates.

        Lazy.nvim doesn't provide a command-line way to check for updates without
        opening Neovim. To avoid false positives during shell startup checks,
        we return False to indicate no updates are available for checking.

        Users should manually run ':Lazy sync' in Neovim or use swman --plugins.
        """
        return False, 0  # Cannot check lazy.nvim updates from command line

    def update(self, dry_run: bool = False) -> ManagerResult:
        start_time = time.time()

        if dry_run:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Would update Neovim plugins",
                duration=time.time() - start_time,
            )

        try:
            # Use streaming output to show real-time Neovim plugin updates
            _ = run_with_streaming_output(
                ["nvim", "--headless", "+Lazy! sync", "+qa"], timeout=300
            )

            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Neovim plugins updated",
                duration=time.time() - start_time,
            )
        except Exception as e:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Neovim plugin update failed: {e}",
                duration=time.time() - start_time,
            )

    @staticmethod
    def _command_exists(command: str) -> bool:
        try:
            subprocess.run(["which", command], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


class FisherManager(PackageManager):
    def __init__(self):
        super().__init__("fisher", ManagerType.PLUGIN)

    def is_available(self) -> bool:
        return (
            self._command_exists("fish")
            and Path.home().joinpath(".config/fish/functions/fisher.fish").exists()
        )

    def check_updates(self) -> Tuple[bool, int]:
        """Check for Fish plugin updates.

        Fisher doesn't provide a command to check for updates without updating.
        To avoid false positives during shell startup checks, we return False
        to indicate no updates are available for checking.

        Users should manually run 'fisher update' or use swman --plugins.
        """
        return False, 0  # Cannot check fisher updates without updating

    def update(self, dry_run: bool = False) -> ManagerResult:
        start_time = time.time()

        if dry_run:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Would update Fish plugins",
                duration=time.time() - start_time,
            )

        try:
            # Use streaming output to show real-time Fish plugin updates
            _ = run_with_streaming_output(["fish", "-c", "fisher update"], timeout=120)

            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Fish plugins updated",
                duration=time.time() - start_time,
            )
        except Exception as e:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Fish plugin update failed: {e}",
                duration=time.time() - start_time,
            )

    @staticmethod
    def _command_exists(command: str) -> bool:
        try:
            subprocess.run(["which", command], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


class SoftwareManagerOrchestrator:
    def __init__(self):
        self.managers: List[PackageManager] = [
            PacmanManager(),
            YayManager(),
            UvToolsManager(),
            LazyNvimManager(),
            FisherManager(),
        ]

    def get_available_managers(self) -> List[PackageManager]:
        return [mgr for mgr in self.managers if mgr.is_available()]

    def check_all(self) -> Dict[str, Tuple[bool, int]]:
        """Check all managers for updates. This method is READ-ONLY and never performs installations."""
        logger = LoggingHelpers(setup_logging("swman"))
        logger.log_info("check_all_started", operation="READ_ONLY_CHECK")
        results = {}
        for manager in self.get_available_managers():
            try:
                logger.log_info(
                    "checking_manager_updates",
                    manager=manager.name,
                    manager_type=manager.type.value,
                    operation="READ_ONLY_CHECK",
                )
                # CRITICAL: Only call check_updates(), never update()
                has_updates, count = manager.check_updates()
                results[manager.name] = (has_updates, count)
                logger.log_info(
                    "manager_check_completed",
                    manager=manager.name,
                    has_updates=has_updates,
                    count=count,
                    operation="READ_ONLY_CHECK",
                )
            except Exception as e:
                logger.log_error(
                    "manager_check_failed",
                    error=str(e),
                    manager=manager.name,
                    operation="READ_ONLY_CHECK",
                )
                results[manager.name] = (False, 0)
        logger.log_info(
            "check_all_completed",
            operation="READ_ONLY_CHECK",
            managers_checked=len(results),
        )
        return results

    def update_by_type(
        self, manager_type: ManagerType, dry_run: bool = False
    ) -> List[ManagerResult]:
        """Update all managers of a specific type."""
        results = []
        for manager in self.get_available_managers():
            if manager.type == manager_type:
                try:
                    result = manager.update(dry_run)
                    results.append(result)
                except Exception as e:
                    results.append(
                        ManagerResult(
                            name=manager.name,
                            status=UpdateStatus.FAILED,
                            message=f"Unexpected error: {e}",
                            duration=0.0,
                        )
                    )
        return results

    def update_all(self, dry_run: bool = False) -> List[ManagerResult]:
        """Update all available managers."""
        results = []
        for manager in self.get_available_managers():
            try:
                result = manager.update(dry_run)
                results.append(result)
            except Exception as e:
                results.append(
                    ManagerResult(
                        name=manager.name,
                        status=UpdateStatus.FAILED,
                        message=f"Unexpected error: {e}",
                        duration=0.0,
                    )
                )
        return results


def print_status_table(
    check_results: Dict[str, Tuple[bool, int]], output: ConsoleOutput
):
    """Print a nice status table using Rich."""
    rows = []
    for name, (has_updates, count) in check_results.items():
        status = "Updates Available" if has_updates else "Up to Date"
        updates_str = str(count) if count > 0 else "-"
        rows.append([name, status, updates_str])

    output.table("Software Manager Status", ["Manager", "Status", "Updates"], rows)


def print_results_summary(results: List[ManagerResult], output: ConsoleOutput):
    """Print update results summary using Rich."""
    rows = []
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
    check, system, tools, plugins, update_all, dry_run, json_output, quiet, verbose
):
    """Software Manager Orchestrator - Unified package manager updates"""

    # Initialize logging and console output
    logger = setup_logging("swman")
    logger = LoggingHelpers(logger)
    output = ConsoleOutput(verbose=verbose, quiet=quiet)
    logger.log_info("swman_started")

    if not any([check, system, tools, plugins, update_all]):
        click.echo("Error: Must specify at least one operation")
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        return 1

    orchestrator = SoftwareManagerOrchestrator()

    if check:
        logger.log_info("check_operation_started", mode="READ_ONLY")
        output.status("Checking for updates...")

        # CRITICAL SAFETY: Explicitly ensure we're in check-only mode
        # This prevents any accidental installations during shell startup
        if system or tools or plugins or update_all:
            logger.log_error(
                "invalid_flag_combination",
                check=True,
                system=system,
                tools=tools,
                plugins=plugins,
                update_all=update_all,
                security_violation="Check mode called with update flags",
            )
            click.echo("❌ ERROR: --check flag cannot be combined with update flags")
            click.echo("💡 This prevents accidental installations during status checks")
            return 1

        logger.log_info(
            "check_mode_safety_guard",
            mode="READ_ONLY",
            system=system,
            tools=tools,
            plugins=plugins,
            update_all=update_all,
            safety_message="Confirmed no update flags are set during check operation",
        )

        check_results = orchestrator.check_all()
        # check_results is Dict[str, Tuple[bool, int]] where tuple is (success, updates_count)
        total_updates = sum(
            r[1] for r in check_results.values() if r[0]
        )  # r[1] is updates_count, r[0] is success
        logger.log_info(
            "check_operation_completed",
            mode="READ_ONLY",
            total_managers=len(check_results),
            managers_with_updates=sum(
                1 for r in check_results.values() if r[0] and r[1] > 0
            ),
            total_updates_available=total_updates,
        )

        if json_output:
            # Convert tuples to JSON-serializable format for pkgstatus compatibility
            json_results = {
                name: {"has_updates": has_updates, "count": count}
                for name, (has_updates, count) in check_results.items()
            }
            output.json(json_results)
        else:
            print_status_table(check_results, output)

        # CRITICAL SAFETY: Log that we're exiting check mode without any installations
        logger.log_info(
            "check_operation_exit",
            mode="READ_ONLY",
            exit_message="Exiting check mode without performing any installations",
        )
        return 0

    results = []

    # Set up operation context
    operation_types = []
    if system:
        operation_types.append("system")
    if tools:
        operation_types.append("tools")
    if plugins:
        operation_types.append("plugins")
    if update_all:
        operation_types.append("all")

    bind_context(operation_types=operation_types, dry_run=dry_run)

    if system:
        logger.log_info("system_update_started")
        output.status("Updating system packages...", "🔄")
        results.extend(orchestrator.update_by_type(ManagerType.SYSTEM, dry_run))

    if tools:
        logger.log_info("tools_update_started")
        output.status("Updating development tools...", "🔧")
        results.extend(orchestrator.update_by_type(ManagerType.TOOL, dry_run))

    if plugins:
        logger.log_info("plugins_update_started")
        output.status("Updating plugins...", "🔌")
        results.extend(orchestrator.update_by_type(ManagerType.PLUGIN, dry_run))

    if update_all:
        logger.log_info("all_update_started")
        output.status("Updating everything...", "🚀")
        results.extend(orchestrator.update_all(dry_run))

    if json_output:
        output.json(
            [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "duration": r.duration,
                    "updates_available": r.updates_available,
                    "updates_applied": r.updates_applied,
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
