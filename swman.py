#!/usr/bin/env -S uv run python
"""
swman - Software Manager Orchestrator

A unified interface to manage updates across multiple package managers
and tools. Designed to work with any system, not just dotfiles.
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from logging_config import setup_logging, bind_context, log_unused_variables


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
                ["checkupdates"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
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
                updates_available=count
            )

        try:
            result = subprocess.run(
                ["sudo", "pacman", "-Syu", "--noconfirm"],
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode == 0:
                # Parse output to count actual updates
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.SUCCESS,
                    message="System packages updated successfully",
                    duration=time.time() - start_time
                )
            else:
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.FAILED,
                    message=f"Update failed: {result.stderr}",
                    duration=time.time() - start_time
                )
        except subprocess.TimeoutExpired:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message="Update timed out",
                duration=time.time() - start_time
            )
        except Exception as e:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Unexpected error: {e}",
                duration=time.time() - start_time
            )

    @staticmethod
    def _command_exists(command: str) -> bool:
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=True
            )
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
                ["yay", "-Qu"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
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
                updates_available=count
            )

        try:
            result = subprocess.run(
                ["yay", "-Syu", "--noconfirm"],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes for AUR builds
            )

            if result.returncode == 0:
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.SUCCESS,
                    message="AUR packages updated successfully",
                    duration=time.time() - start_time
                )
            else:
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.FAILED,
                    message=f"AUR update failed: {result.stderr}",
                    duration=time.time() - start_time
                )
        except subprocess.TimeoutExpired:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message="AUR update timed out",
                duration=time.time() - start_time
            )
        except Exception as e:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Unexpected error: {e}",
                duration=time.time() - start_time
            )

    @staticmethod
    def _command_exists(command: str) -> bool:
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False


class UvToolsManager(PackageManager):
    def __init__(self):
        super().__init__("uv-tools", ManagerType.TOOL)

    def is_available(self) -> bool:
        return self._command_exists("uv")

    def check_updates(self) -> Tuple[bool, int]:
        # UV doesn't have a direct "check updates" command
        # We'd need to parse `uv tool list` and check each tool
        return True, 0  # Assume updates available for now

    def update(self, dry_run: bool = False) -> ManagerResult:
        start_time = time.time()

        if dry_run:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Would upgrade all uv tools",
                duration=time.time() - start_time
            )

        try:
            result = subprocess.run(
                ["uv", "tool", "upgrade", "--all"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.SUCCESS,
                    message="UV tools updated successfully",
                    duration=time.time() - start_time
                )
            else:
                return ManagerResult(
                    name=self.name,
                    status=UpdateStatus.FAILED,
                    message=f"UV tools update failed: {result.stderr}",
                    duration=time.time() - start_time
                )
        except Exception as e:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Unexpected error: {e}",
                duration=time.time() - start_time
            )

    @staticmethod
    def _command_exists(command: str) -> bool:
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=True
            )
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
        # Lazy.nvim has automatic checking enabled in your config
        return True, 0  # Assume updates available

    def update(self, dry_run: bool = False) -> ManagerResult:
        start_time = time.time()

        if dry_run:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Would update Neovim plugins",
                duration=time.time() - start_time
            )

        try:
            result = subprocess.run(
                ["nvim", "--headless", "+Lazy! sync", "+qa"],
                capture_output=True,
                text=True,
                timeout=300
            )

            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Neovim plugins updated",
                duration=time.time() - start_time
            )
        except Exception as e:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Neovim plugin update failed: {e}",
                duration=time.time() - start_time
            )

    @staticmethod
    def _command_exists(command: str) -> bool:
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False


class FisherManager(PackageManager):
    def __init__(self):
        super().__init__("fisher", ManagerType.PLUGIN)

    def is_available(self) -> bool:
        return (self._command_exists("fish") and
                Path.home().joinpath(".config/fish/functions/fisher.fish").exists())

    def check_updates(self) -> Tuple[bool, int]:
        return True, 0  # Assume updates available

    def update(self, dry_run: bool = False) -> ManagerResult:
        start_time = time.time()

        if dry_run:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Would update Fish plugins",
                duration=time.time() - start_time
            )

        try:
            result = subprocess.run(
                ["fish", "-c", "fisher update"],
                capture_output=True,
                text=True,
                timeout=120
            )

            return ManagerResult(
                name=self.name,
                status=UpdateStatus.SUCCESS,
                message="Fish plugins updated",
                duration=time.time() - start_time
            )
        except Exception as e:
            return ManagerResult(
                name=self.name,
                status=UpdateStatus.FAILED,
                message=f"Fish plugin update failed: {e}",
                duration=time.time() - start_time
            )

    @staticmethod
    def _command_exists(command: str) -> bool:
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                check=True
            )
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
        """Check all managers for updates."""
        results = {}
        for manager in self.get_available_managers():
            try:
                results[manager.name] = manager.check_updates()
            except Exception as e:
                print(f"Error checking {manager.name}: {e}")
                results[manager.name] = (False, 0)
        return results

    def update_by_type(self, manager_type: ManagerType, dry_run: bool = False) -> List[ManagerResult]:
        """Update all managers of a specific type."""
        results = []
        for manager in self.get_available_managers():
            if manager.type == manager_type:
                try:
                    result = manager.update(dry_run)
                    results.append(result)
                except Exception as e:
                    results.append(ManagerResult(
                        name=manager.name,
                        status=UpdateStatus.FAILED,
                        message=f"Unexpected error: {e}",
                        duration=0.0
                    ))
        return results

    def update_all(self, dry_run: bool = False) -> List[ManagerResult]:
        """Update all available managers."""
        results = []
        for manager in self.get_available_managers():
            try:
                result = manager.update(dry_run)
                results.append(result)
            except Exception as e:
                results.append(ManagerResult(
                    name=manager.name,
                    status=UpdateStatus.FAILED,
                    message=f"Unexpected error: {e}",
                    duration=0.0
                ))
        return results


def print_status_table(check_results: Dict[str, Tuple[bool, int]]):
    """Print a nice status table."""
    print("\n📊 Software Manager Status")
    print("=" * 50)
    print(f"{'Manager':<15} {'Status':<15} {'Updates':<10}")
    print("-" * 50)

    for name, (has_updates, count) in check_results.items():
        status = "Updates Available" if has_updates else "Up to Date"
        updates_str = str(count) if count > 0 else "-"
        print(f"{name:<15} {status:<15} {updates_str:<10}")


def print_results_summary(results: List[ManagerResult]):
    """Print update results summary."""
    print("\n🔄 Update Results")
    print("=" * 60)

    for result in results:
        status_icon = {
            UpdateStatus.SUCCESS: "✅",
            UpdateStatus.FAILED: "❌",
            UpdateStatus.SKIPPED: "⏭️",
            UpdateStatus.NOT_AVAILABLE: "⚠️"
        }.get(result.status, "❓")

        print(f"{status_icon} {result.name:<15} {result.message}")
        if result.duration > 0:
            print(f"   Duration: {result.duration:.1f}s")


def main():
    # Initialize logging
    logger = setup_logging("swman")
    logger.info("swman_started")

    parser = argparse.ArgumentParser(
        description="Software Manager Orchestrator - Unified package manager updates"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for updates across all managers"
    )
    parser.add_argument(
        "--system",
        action="store_true",
        help="Update system packages only (pacman, yay, apt)"
    )
    parser.add_argument(
        "--tools",
        action="store_true",
        help="Update development tools (uv, etc.)"
    )
    parser.add_argument(
        "--plugins",
        action="store_true",
        help="Update plugins (nvim, fish, tmux)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Update everything"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without actually updating"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )

    args = parser.parse_args()

    if not any([args.check, args.system, args.tools, args.plugins, args.all]):
        parser.print_help()
        return 1

    orchestrator = SoftwareManagerOrchestrator()

    if args.check:
        logger.info("check_operation_started")
        print("🔍 Checking for updates...")
        check_results = orchestrator.check_all()
        # check_results is Dict[str, Tuple[bool, int]] where tuple is (success, updates_count)
        total_updates = sum(r[1] for r in check_results.values() if r[0])  # r[1] is updates_count, r[0] is success
        logger.info("check_operation_completed",
                   total_managers=len(check_results),
                   managers_with_updates=sum(1 for r in check_results.values() if r[0] and r[1] > 0),
                   total_updates_available=total_updates)

        if args.json:
            print(json.dumps(check_results, indent=2))
        else:
            print_status_table(check_results)
        return 0

    results = []

    # Set up operation context
    operation_types = []
    if args.system:
        operation_types.append("system")
    if args.tools:
        operation_types.append("tools")
    if args.plugins:
        operation_types.append("plugins")
    if args.all:
        operation_types.append("all")

    bind_context(operation_types=operation_types, dry_run=args.dry_run)

    if args.system:
        logger.info("system_update_started")
        print("🔄 Updating system packages...")
        results.extend(orchestrator.update_by_type(ManagerType.SYSTEM, args.dry_run))

    if args.tools:
        logger.info("tools_update_started")
        print("🔧 Updating development tools...")
        results.extend(orchestrator.update_by_type(ManagerType.TOOL, args.dry_run))

    if args.plugins:
        logger.info("plugins_update_started")
        print("🔌 Updating plugins...")
        results.extend(orchestrator.update_by_type(ManagerType.PLUGIN, args.dry_run))

    if args.all:
        logger.info("all_update_started")
        print("🚀 Updating everything...")
        results.extend(orchestrator.update_all(args.dry_run))

    if args.json:
        print(json.dumps([{
            'name': r.name,
            'status': r.status.value,
            'message': r.message,
            'duration': r.duration,
            'updates_available': r.updates_available,
            'updates_applied': r.updates_applied
        } for r in results], indent=2))
    else:
        print_results_summary(results)

    # Log completion and return appropriate exit code
    failed_count = sum(1 for r in results if r.status == UpdateStatus.FAILED)
    success_count = sum(1 for r in results if r.status == UpdateStatus.SUCCESS)

    logger.info("swman_completed",
               total_operations=len(results),
               successful=success_count,
               failed=failed_count)

    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())