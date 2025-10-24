#!/usr/bin/env -S uv run python
# pyright: strict
"""
pkgstatus.py - Package and System Status Checker

Python backend for the Fish shell pkgstatus function.
Handles all complex logic for package, git, and init status checking.
"""

import json
import os
from subprocess import CalledProcessError, TimeoutExpired
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

import click
from .logging_config import setup_logging, LoggingHelpers
from .output_formatting import ConsoleOutput
from .process_helper import run_command_with_error_handling
from .swman import SoftwareManagerOrchestrator
from typing import Any, Callable, cast


class CheckStatus(Enum):
    """Status of a check operation."""

    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass
class UpdateCheckResult:
    """
    System update status as reported by a single package manager.

    Attributes:
        name: Package manager name (e.g., "pacman", "yay", "apt")
        has_updates: Whether the package manager found updates available
        count: Number of updates found (0=no updates, >0=updates available, <0=indeterminate)
    """

    name: str
    has_updates: bool = False
    count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return dict(name=self.name, has_updates=self.has_updates, count=self.count)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdateCheckResult":
        return cls(
            name=data["name"],
            has_updates=bool(data["has_updates"]),
            count=int(data["count"]),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "UpdateCheckResult":
        return cls.from_dict(json.loads(json_str))


@dataclass
class UpdateCheckCache:
    """
    Cached results from checking all package managers for system updates.

    This represents a point-in-time snapshot of update availability.
    Cache freshness is determined by file modification time, not stored state.

    Attributes:
        packages: Update check results from each individual package manager
        total_updates: Total number of updates available across all managers
        last_check: Unix timestamp when this cache entry was created
        status: Check operation status
    """

    packages: list[UpdateCheckResult] = field(default_factory=lambda: [])
    total_updates: int = 0
    last_check: int = 0
    status: CheckStatus = CheckStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        return dict(
            packages=[x.to_dict() for x in self.packages],
            total_updates=self.total_updates,
            last_check=self.last_check,
            status=self.status.value,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdateCheckCache":
        return cls(
            packages=[UpdateCheckResult.from_dict(x) for x in data.get("packages", [])],
            total_updates=data.get("total_updates", 0),
            last_check=data.get("last_check", 0),
            status=CheckStatus(data.get("status", "success")),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "UpdateCheckCache":
        return cls.from_dict(json.loads(json_str))


@dataclass
class GitStatus:
    """
    Git repository status for the current working directory.

    Attributes:
        last_check: Unix timestamp of last check
        enabled: Whether git status checking is enabled
        in_repo: Whether current directory is in a git repository
        uncommitted: Number of uncommitted changes
        ahead: Number of commits ahead of remote
        behind: Number of commits behind remote
        branch: Current branch name, or "detached" if HEAD is detached
        status: Check operation status
    """

    last_check: int = 0
    enabled: bool = False
    in_repo: bool = False
    uncommitted: int = 0
    ahead: int = 0
    behind: int = 0
    branch: str = "detached"
    status: CheckStatus = CheckStatus.SUCCESS

    def to_json(self) -> str:
        return json.dumps(
            dict(
                last_check=self.last_check,
                enabled=self.enabled,
                in_repo=self.in_repo,
                uncommitted=self.uncommitted,
                ahead=self.ahead,
                behind=self.behind,
                branch=self.branch,
                status=self.status.value,
            )
        )

    @classmethod
    def from_json(cls, json_str: str) -> "GitStatus":
        data = json.loads(json_str)
        return cls(
            last_check=data.get("last_check", 0),
            enabled=data.get("enabled", False),
            in_repo=data.get("in_repo", False),
            uncommitted=data.get("uncommitted", 0),
            ahead=data.get("ahead", 0),
            behind=data.get("behind", 0),
            branch=data.get("branch", "detached"),
            status=CheckStatus(data.get("status", "success")),
        )


@dataclass
class InitScriptStatus:
    """
    Dotfiles init script execution status.

    Tracks when the dotfiles init script was last run to determine
    if the system configuration needs refreshing.

    Attributes:
        enabled: Whether init script status checking is enabled
        last_check: Unix timestamp of last status check
        last_run: Unix timestamp of last init script execution
        status: Check operation status
        dotfiles_found: Whether dotfiles repository was found at DOTFILES_DIR
    """

    enabled: bool = False
    last_check: int = 0
    last_run: int = 0
    status: CheckStatus = CheckStatus.SUCCESS
    dotfiles_found: bool = False

    @property
    def age_hours(self) -> float:
        """Hours since init script was last run.

        Returns float('inf') when never run (last_run=0), indicating infinite time ago.
        This ensures needs_update correctly evaluates to True for never-run scripts.
        """
        if self.last_run == 0:
            return float("inf")
        return (time.time() - self.last_run) / 3600

    @property
    def needs_update(self) -> bool:
        """Whether init script should be run (>7 days since last run)."""
        return self.age_hours > 168

    def to_json(self) -> str:
        return json.dumps(
            dict(
                enabled=self.enabled,
                last_check=self.last_check,
                last_run=self.last_run,
                status=self.status.value,
                dotfiles_found=self.dotfiles_found,
            )
        )

    @classmethod
    def from_json(cls, json_str: str) -> "InitScriptStatus":
        data = json.loads(json_str)
        return cls(
            enabled=data.get("enabled", False),
            last_check=data.get("last_check", 0),
            last_run=data.get("last_run", 0),
            status=CheckStatus(data.get("status", "success")),
            dotfiles_found=data.get("dotfiles_found", False),
        )


@dataclass
class SystemStatus:
    """
    Complete system status combining package, git, and init script information.

    Attributes:
        packages: Aggregated package update status across all managers
        package_cache_path: Path to the packages cache file
        git: Git repository status for current directory
        init: Dotfiles init script execution status
    """

    packages: UpdateCheckCache
    package_cache_path: Path
    git: GitStatus
    init: InitScriptStatus


class StatusChecker:
    """
    System status checker with intelligent caching for packages, git, and init script.

    Provides cached status information for multiple aspects of system health:
    - Package updates across multiple package managers (via swman)
    - Git repository status for current directory
    - Dotfiles init script freshness

    Each status type has configurable cache expiration and can be force-refreshed.
    Cache files are stored as JSON and loaded/saved atomically to prevent corruption.

    Attributes:
        cache_dir: Base directory for all cache files
        packages_cache: Path to packages.json cache file
        git_cache: Path to git.json cache file
        init_cache: Path to init.json cache file
    """

    def __init__(self, cache_dir: str | None = None):
        self.cache_dir = (
            Path(cache_dir or os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser()
            / "dotfiles"
            / "status"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache file paths
        self.packages_cache = self.cache_dir / "packages.json"
        self.git_cache = self.cache_dir / "git.json"
        self.init_cache = self.cache_dir / "init.json"

    def _get_fish_config(
        self, key: str, default: str, logger: LoggingHelpers, output: ConsoleOutput
    ) -> str:
        """Get Fish universal variable configuration"""
        try:
            result = run_command_with_error_handling(
                ["fish", "-c", f"echo $pkgstatus_{key}"],
                logger=logger,
                output=output,
                description=f"Get fish config pkgstatus_{key}",
                timeout=5,
            )
            value = result.stdout.strip()
            return value if value else default
        except Exception as e:
            logger.log_exception(e, "fish_config_read_failed", key=key)
            return default

    def is_cache_expired(self, cache_file: Path, max_age_hours: int) -> bool:
        """Check if cache file is expired"""
        if not cache_file.exists():
            return True

        file_age = time.time() - cache_file.stat().st_mtime
        return file_age > (max_age_hours * 3600)

    def get_packages_status(
        self,
        logger: LoggingHelpers,
        output: ConsoleOutput,
        force_refresh: bool,
    ) -> UpdateCheckCache:
        """Get package status with caching"""
        cache_hours = int(self._get_fish_config("cache_hours", "6", logger, output))

        if force_refresh or self.is_cache_expired(self.packages_cache, cache_hours):
            self._refresh_packages_cache(logger, output)

        return self._load_cache(
            self.packages_cache, UpdateCheckCache, UpdateCheckCache, logger
        )

    def get_git_status(
        self, logger: LoggingHelpers, output: ConsoleOutput, force_refresh: bool
    ) -> GitStatus:
        """Get git status with caching"""
        enabled = self._get_fish_config("git_enabled", "true", logger, output) == "true"
        logger = logger.bind(git_enabled=enabled)
        if not enabled:
            logger.log_info("git_disabled")
            return GitStatus(
                enabled=False, in_repo=False, uncommitted=0, ahead=0, behind=0
            )

        if force_refresh or self.is_cache_expired(self.git_cache, 1):  # 1 hour cache
            logger.log_info("cache_refresh")
            self._refresh_git_cache(logger, output)

        return self._load_cache(self.git_cache, GitStatus, GitStatus, logger)

    def get_init_status(
        self, logger: LoggingHelpers, output: ConsoleOutput, force_refresh: bool
    ) -> InitScriptStatus:
        """Get init script status with caching"""
        enabled = (
            self._get_fish_config("init_enabled", "true", logger, output) == "true"
        )
        logger = logger.bind(init_enabled=enabled)
        if not enabled:
            logger.log_info("init_disabled")
            return InitScriptStatus()

        if force_refresh or self.is_cache_expired(self.init_cache, 24):  # 24 hour cache
            logger.log_info("cache_refresh")
            self._refresh_init_cache(logger)

        return self._load_cache(
            self.init_cache,
            InitScriptStatus,
            lambda: InitScriptStatus(enabled=True, status=CheckStatus.UNAVAILABLE),
            logger,
        )

    def _load_cache[T: GitStatus | InitScriptStatus | UpdateCheckCache](
        self,
        cache_file: Path,
        cls: type[T],
        default_factory: type[T] | Callable[[], T],
        logger: LoggingHelpers,
    ) -> T:
        """Load JSON from cache file with fallback"""
        logger = logger.bind(cache_file=str(cache_file), cls=cls.__name__)
        # If cache file doesn't exist, return default (expected case)
        if not cache_file.exists():
            logger.log_info("cache_file_not_found")
            return default_factory()

        # Cache file exists - attempt to load it
        # If this fails, it's a real error (corruption, permissions, etc.) that should be raised
        try:
            with open(cache_file, "r") as f:
                return cast(T, cls.from_json(f.read()))
        except Exception as e:
            logger.log_exception(
                e,
                "cache_load_failed",
            )
            raise

    def _save_cache(
        self,
        cache_file: Path,
        data: GitStatus | InitScriptStatus | UpdateCheckCache,
        logger: LoggingHelpers,
    ) -> None:
        """Save data to cache file atomically"""
        temp_file = cache_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w") as f:
                f.write(data.to_json())
            temp_file.replace(cache_file)
        except Exception as e:
            logger.log_exception(e, "cache_save_failed", cache_file=str(cache_file))
            if temp_file.exists():
                temp_file.unlink()

    def _refresh_packages_cache(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> None:
        """Refresh package status cache by calling swman directly"""
        timestamp = int(time.time())

        try:
            # Call swman directly instead of subprocess
            orchestrator = SoftwareManagerOrchestrator()
            check_results = orchestrator.check_all(logger=logger, output=output)

            # Transform swman format to our format
            packages: list[UpdateCheckResult] = []
            total_updates = 0

            for manager, (has_updates, count) in check_results.items():
                # Handle different update check states:
                # - count > 0: confirmed updates available
                # - count = 0: no updates
                # - count < 0: cannot determine (indeterminate)
                packages.append(
                    UpdateCheckResult(
                        name=manager, has_updates=has_updates, count=count
                    )
                )
                # Only count positive updates (exclude indeterminate managers)
                if has_updates and count > 0:
                    total_updates += count

            data = UpdateCheckCache(
                packages=packages,
                total_updates=total_updates,
                last_check=timestamp,
            )

        except Exception as e:
            logger.log_exception(e, "packages_cache_refresh_failed")
            data = UpdateCheckCache()

        self._save_cache(self.packages_cache, data, logger)

    def _refresh_git_cache(self, logger: LoggingHelpers, output: ConsoleOutput) -> None:
        """Refresh git status cache"""
        timestamp = int(time.time())
        git_data = GitStatus(last_check=timestamp, enabled=True)
        logger = logger.bind(timestamp=timestamp)

        try:
            # Check if we're in a git repository
            try:
                run_command_with_error_handling(
                    ["git", "rev-parse", "--git-dir"],
                    logger=logger,
                    output=output,
                    description="Check if in git repository",
                    timeout=5,
                )
                git_data.in_repo = True
                logger = logger.bind(in_repo=True)
            except CalledProcessError:
                # Git command failed (not in a repo) - this is expected/normal
                logger.log_info("no_git_repo")
                git_data.in_repo = False
                self._save_cache(self.git_cache, git_data, logger)
                return
            # Other exceptions (timeout, git not found, permissions) bubble up to outer catch

            # Get current branch
            branch_result = run_command_with_error_handling(
                ["git", "branch", "--show-current"],
                logger=logger,
                output=output,
                description="Get current git branch",
                timeout=5,
            )
            git_data.branch = branch_result.stdout.strip() or "detached"
            logger = logger.bind(branch=git_data.branch)

            # Count uncommitted changes
            status_result = run_command_with_error_handling(
                ["git", "status", "--porcelain"],
                logger=logger,
                output=output,
                description="Get git status",
                timeout=5,
            )
            git_data.uncommitted = (
                len(status_result.stdout.strip().split("\n"))
                if status_result.stdout.strip()
                else 0
            )
            logger = logger.bind(uncommitted=git_data.uncommitted)

            if git_data.branch != "detached":
                try:
                    upstream_result = run_command_with_error_handling(
                        ["git", "rev-parse", "--abbrev-ref", "@{upstream}"],
                        logger=logger,
                        output=output,
                        description="Get git upstream branch",
                        timeout=5,
                    )
                    upstream = upstream_result.stdout.strip()
                    logger = logger.bind(upstream_branch_rev=upstream)

                    counts_result = run_command_with_error_handling(
                        [
                            "git",
                            "rev-list",
                            "--left-right",
                            "--count",
                            f"{upstream}...HEAD",
                        ],
                        logger=logger,
                        output=output,
                        description="Count commits ahead/behind",
                        timeout=5,
                    )
                    counts = counts_result.stdout.strip().split()
                    if len(counts) == 2:
                        git_data.behind = int(counts[0])
                        git_data.ahead = int(counts[1])
                        logger = logger.bind(
                            behind=git_data.behind, ahead=git_data.ahead
                        )
                except CalledProcessError as e:
                    # No upstream branch configured - expected for local-only branches
                    logger.log_exception(e, "git_upstream_check_failed")

        except CalledProcessError as e:
            # Git command failed unexpectedly
            git_data.status = CheckStatus.FAILED
            logger.log_exception(e, "git_command_failed")
        except TimeoutExpired as e:
            # Git command timed out
            git_data.status = CheckStatus.FAILED
            logger.log_exception(e, "git_timeout")
        except Exception as e:
            # Unexpected error (git not installed, permissions, etc.)
            git_data.status = CheckStatus.FAILED
            logger.log_exception(e, "git_check_failed")

        self._save_cache(self.git_cache, git_data, logger)

    def _refresh_init_cache(self, logger: LoggingHelpers) -> None:
        """Refresh init script status cache"""
        timestamp = int(time.time())
        logger = logger.bind(timestamp=timestamp)
        init_data = InitScriptStatus(enabled=True, last_check=timestamp)

        # Get dotfiles directory from environment or use default
        dotfiles_dir = Path(
            os.environ.get("DOTFILES_DIR", "~/projects/dotfiles")
        ).expanduser()
        init_script = dotfiles_dir / "init.py"

        if init_script.exists():
            init_data.dotfiles_found = True

            # Check last run time
            last_run_file = Path.home() / ".cache" / "dotfiles_last_update"
            last_run = 0
            logger = logger.bind(last_run_file=last_run_file)

            if last_run_file.exists():
                try:
                    with open(last_run_file, "r") as f:
                        last_run_str = f.read().strip()
                    # Parse ISO format timestamp
                    last_run_dt = datetime.fromisoformat(last_run_str)
                    last_run = int(last_run_dt.timestamp())
                except Exception as e:
                    logger.log_exception(e, "init_cache_timestamp_parse_failed")

            init_data.last_run = last_run
            # age_hours and needs_update are now computed properties

        self._save_cache(self.init_cache, init_data, logger)

    def get_system_status(
        self,
        logger: LoggingHelpers,
        output: ConsoleOutput,
        force_refresh: bool,
    ) -> SystemStatus:
        """Get complete system status across packages, git, and init script"""
        return SystemStatus(
            package_cache_path=self.packages_cache,
            packages=self.get_packages_status(logger, output, force_refresh),
            git=self.get_git_status(logger, output, force_refresh),
            init=self.get_init_status(logger, output, force_refresh),
        )

    def format_quiet_output(self, status: SystemStatus) -> str:
        """Format output for quiet mode (only show if issues)"""
        messages: list[str] = []

        # Check package updates
        pkg_data = status.packages
        total_updates = pkg_data.total_updates
        if total_updates > 0:
            last_check = pkg_data.last_check
            age = self._format_age(last_check)
            messages.append(f"⚠️  {total_updates} package updates available ({age})")

        # Check git status
        git_data = status.git
        enabled = git_data.enabled
        in_repo = git_data.in_repo
        if enabled and in_repo:
            uncommitted = git_data.uncommitted
            ahead = git_data.ahead
            if uncommitted > 0 or ahead > 0:
                git_msg = "🔄 Git:"
                if uncommitted > 0:
                    git_msg += f" {uncommitted} uncommitted"
                if ahead > 0:
                    git_msg += f" {ahead} unpushed"
                messages.append(git_msg)

        # Check init status
        init_data = status.init
        init_enabled = init_data.enabled
        needs_update = init_data.needs_update
        if init_enabled and needs_update:
            if init_data.last_run == 0:
                messages.append("⚙️  Init script never run")
            else:
                age_hours = init_data.age_hours
                messages.append(f"⚙️  Init script not run in {int(age_hours / 24)}d")

        # Add tool name prefix to all messages
        if messages:
            prefixed_messages = [f"pkgstatus: {messages[0]}"]
            prefixed_messages.extend(f"pkgstatus: {msg}" for msg in messages[1:])
            return "\n".join(prefixed_messages)
        return ""

    def format_interactive_output(self, status: SystemStatus) -> str:
        """Format output for interactive mode"""
        lines = ["📦 Package Status:"]

        # Package status
        pkg_data = status.packages
        if pkg_data.status != CheckStatus.SUCCESS:
            lines.append(f"   ❌ Package check {pkg_data.status.value}")
        else:
            total_updates = pkg_data.total_updates
            if total_updates > 0:
                last_check = pkg_data.last_check
                age = self._format_age(last_check)
                lines.append(f"   ⚠️  {total_updates} updates available (checked {age})")

                # Show breakdown by manager
                packages = pkg_data.packages
                for package in packages:
                    if package.has_updates:
                        if package.count > 0:
                            lines.append(
                                f"      • {package.name}: {package.count} updates"
                            )
                        else:
                            lines.append(f"      • {package.name}: updates available")
            else:
                lines.append("   ✅ All packages up to date")

        # Git status
        git_data = status.git
        if git_data.enabled:
            lines.extend(["", "🔄 Git Status:"])
            if git_data.status != CheckStatus.SUCCESS:
                lines.append(f"   ❌ Git check {git_data.status.value}")
            elif git_data.in_repo:
                branch = git_data.branch
                uncommitted = git_data.uncommitted
                ahead = git_data.ahead
                behind = git_data.behind

                lines.append(f"   📁 Branch: {branch}")
                if uncommitted > 0:
                    lines.append(f"   ⚠️  {uncommitted} uncommitted changes")
                if ahead > 0:
                    lines.append(f"   ⬆️  {ahead} commits ahead of origin")
                if behind > 0:
                    lines.append(f"   ⬇️  {behind} commits behind origin")
                if uncommitted == 0 and ahead == 0 and behind == 0:
                    lines.append("   ✅ Working tree clean and up to date")
            else:
                lines.append("   ℹ️  Not in a git repository")

        # Init status
        init_data = status.init
        if init_data.enabled:
            lines.extend(["", "⚙️  Init Status:"])
            if init_data.status != CheckStatus.SUCCESS:
                lines.append(f"   ❌ Init check {init_data.status.value}")
            elif init_data.dotfiles_found:
                if init_data.needs_update:
                    if init_data.last_run == 0:
                        lines.append("   ⚠️  Init script never run - consider running")
                    else:
                        age_hours = init_data.age_hours
                        lines.append(
                            f"   ⚠️  Last run {int(age_hours / 24)}d ago - consider running"
                        )
                else:
                    last_run = init_data.last_run
                    age_desc = self._format_age(last_run)
                    lines.append(f"   ✅ Recently run ({age_desc})")
            else:
                dotfiles_dir = os.environ.get("DOTFILES_DIR", "~/projects/dotfiles")
                lines.append(f"   ❌ Dotfiles not found at {dotfiles_dir}")

        return "\n".join(lines)

    def _format_age(self, timestamp: int) -> str:
        """Format timestamp age as human readable"""
        if timestamp == 0:
            return "never"

        age = int(time.time()) - timestamp

        if age < 60:
            return "just now"
        elif age < 3600:
            return f"{age // 60}m ago"
        elif age < 86400:
            return f"{age // 3600}h ago"
        else:
            return f"{age // 86400}d ago"


@click.command()
@click.option("--quiet", is_flag=True, help="Only show if issues exist")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
@click.option("--refresh", is_flag=True, help="Force cache refresh")
@click.option("--cache-dir", help="Override cache directory")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def main(
    quiet: bool, json_output: bool, refresh: bool, cache_dir: str | None, verbose: bool
):
    """Package and system status checker

    \b
    To perform updates:
      Package updates:  Use 'dotfiles-swman --system' or 'dotfiles-swman --all'
      Git operations:   Use 'git add', 'git commit', 'git push'
      Init script:      Run 'dotfiles-init' in dotfiles directory

    For more information, see the README or run 'dotfiles-swman --help'
    """
    # Initialize logging and console output with CLI context
    logger = setup_logging("pkgstatus").bind(
        verbose=verbose,
        quiet=quiet,
        json_output=json_output,
        refresh=refresh,
        cache_dir=cache_dir or "default",
    )
    output = ConsoleOutput(verbose=verbose, quiet=quiet)
    logger.log_info("pkgstatus_started")

    try:
        checker = StatusChecker(cache_dir)

        # Gather status with logging
        gather_log = logger.bind(operation="gather_status")
        gather_log.log_info("operation_started")
        status = checker.get_system_status(logger, output, refresh)
        gather_log.log_info("operation_completed")

        # Log comprehensive status summary
        logger.log_info(
            "status_check_completed",
            packages_total_updates=status.packages.total_updates,
            packages_status=status.packages.status.value,
            git_in_repo=status.git.in_repo,
            git_uncommitted=status.git.uncommitted,
            git_ahead=status.git.ahead,
            git_behind=status.git.behind,
            git_status=status.git.status.value,
            init_needs_update=status.init.needs_update,
            init_status=status.init.status.value,
        )

        if json_output:
            status_output = {
                "packages": status.packages,
                "git": status.git,
                "init": status.init,
            }
            output.json(status_output)
        elif quiet:
            quiet_output = checker.format_quiet_output(status)
            if quiet_output:  # Only print if there are issues
                click.echo(quiet_output)
        else:
            # Display interactive output with Rich formatting
            interactive_output = checker.format_interactive_output(status)
            click.echo(interactive_output)

        return 0

    except Exception as e:
        logger.log_exception(e, "status_check_failed")
        output.error(f"Failed to check status: {e}")
        if verbose:
            output.info("DETAILED ERROR INFORMATION:")
            import traceback

            traceback.print_exc()
            output.info("Check the error details above and retry")
        return 1


if __name__ == "__main__":
    main()
