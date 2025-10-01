#!/usr/bin/env -S uv run python
# pyright: strict
"""
pkgstatus.py - Package and System Status Checker

Python backend for the Fish shell pkgstatus function.
Handles all complex logic for package, git, and init status checking.
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import click
from .logging_config import setup_logging
from .output_formatting import ConsoleOutput
from typing import Any


@dataclass
class StatusResult:
    packages: tuple[str, dict[str, str | int | dict[str, str]]]
    git: dict[str, str | int | bool]
    init: dict[str, str | int | bool | float]


class StatusChecker:
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

    def get_config(self, key: str, default: str) -> str:
        """Get Fish universal variable configuration"""
        try:
            result = subprocess.run(
                ["fish", "-c", f"echo $pkgstatus_{key}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            value = result.stdout.strip()
            return value if value else default
        except Exception:
            return default

    def is_cache_expired(self, cache_file: Path, max_age_hours: int) -> bool:
        """Check if cache file is expired"""
        if not cache_file.exists():
            return True

        file_age = time.time() - cache_file.stat().st_mtime
        return file_age > (max_age_hours * 3600)

    def get_packages_status(
        self, force_refresh: bool = False
    ) -> tuple[str, dict[str, str | int | dict[str, str]]]:
        """Get package status with caching"""
        cache_hours = int(self.get_config("cache_hours", "6"))

        if force_refresh or self.is_cache_expired(self.packages_cache, cache_hours):
            self._refresh_packages_cache()

        return self._load_cache(
            self.packages_cache,
            {
                "packages": dict(),
                "total_updates": 0,
                "last_check": 0,
                "error": "Cache unavailable",
            },
        )

    def get_git_status(self, force_refresh: bool = False) -> dict[str, str | bool]:
        """Get git status with caching"""
        enabled = self.get_config("git_enabled", "true") == "true"
        if not enabled:
            return {"enabled": False}

        if force_refresh or self.is_cache_expired(self.git_cache, 1):  # 1 hour cache
            self._refresh_git_cache()

        return self._load_cache(
            self.git_cache, {"enabled": True, "error": "Git status unavailable"}
        )

    def get_init_status(self, force_refresh: bool = False) -> dict[str, bool | str]:
        """Get init script status with caching"""
        enabled = self.get_config("init_enabled", "true") == "true"
        if not enabled:
            return {"enabled": False}

        if force_refresh or self.is_cache_expired(self.init_cache, 24):  # 24 hour cache
            self._refresh_init_cache()

        return self._load_cache(
            self.init_cache, {"enabled": True, "error": "Init status unavailable"}
        )

    def _load_cache(self, cache_file: Path, default: Any) -> Any:
        """Load JSON from cache file with fallback"""
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except Exception:
            return default

    def _save_cache(self, cache_file: Path, data: Any):
        """Save data to cache file atomically"""
        temp_file = cache_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w") as f:
                json.dump(data, f)
            temp_file.replace(cache_file)
        except Exception:
            if temp_file.exists():
                temp_file.unlink()

    def _refresh_packages_cache(self) -> None:
        """Refresh package status cache"""
        timestamp = int(time.time())

        # Try to find swman
        swman_cmd: str | None = None
        if Path("./swman.py").is_file():
            swman_cmd = "./swman.py"
        elif subprocess.run(["which", "swman.py"], capture_output=True).returncode == 0:
            swman_cmd = "swman.py"

        if swman_cmd:
            try:
                result = subprocess.run(
                    [swman_cmd, "--check", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    # Extract JSON from output (skip status messages)
                    output_lines = result.stdout.strip().split("\n")

                    # Find where JSON starts and ends
                    json_start_idx = -1
                    json_end_idx = -1

                    for i, line in enumerate(output_lines):
                        if line.strip().startswith("{"):
                            json_start_idx = i
                        elif line.strip() == "}" and json_start_idx != -1:
                            json_end_idx = i
                            break

                    json_line: dict[str, tuple[bool, int]] | None = None
                    if json_start_idx != -1 and json_end_idx != -1:
                        json_lines = output_lines[json_start_idx : json_end_idx + 1]
                        json_text = "\n".join(json_lines)
                        try:
                            packages_data: dict[str, tuple[bool, int]] = json.loads(
                                json_text
                            )
                            json_line = packages_data
                        except json.JSONDecodeError:
                            json_line = None

                    if json_line:
                        # Transform swman format to our format
                        packages: dict[str, dict[str, bool | int]] = {}
                        total_updates = 0

                        for manager, (has_updates, count) in json_line.items():
                            # Handle different update check states:
                            # - count > 0: confirmed updates available
                            # - count = 0: no updates
                            # - count < 0: cannot determine (indeterminate)
                            packages[manager] = {
                                "has_updates": has_updates,
                                "count": count,
                            }
                            # Only count positive updates (exclude indeterminate managers)
                            if has_updates and count > 0:
                                total_updates += count

                        data: dict[
                            str, int | bool | dict[str, dict[str, bool | int]]
                        ] = {
                            "packages": packages,
                            "total_updates": total_updates,
                            "last_check": timestamp,
                            "stale": False,
                        }
                    else:
                        data = {
                            "packages": {},
                            "total_updates": 0,
                            "last_check": timestamp,
                            "error": "Invalid swman output",
                        }
                else:
                    data = {
                        "packages": {},
                        "total_updates": 0,
                        "last_check": timestamp,
                        "error": "swman check failed",
                    }
            except subprocess.TimeoutExpired:
                data = {
                    "packages": {},
                    "total_updates": 0,
                    "last_check": timestamp,
                    "error": "swman check timed out",
                }
            except Exception as e:
                data = {
                    "packages": {},
                    "total_updates": 0,
                    "last_check": timestamp,
                    "error": f"swman error: {e}",
                }
        else:
            data = {
                "packages": {},
                "total_updates": 0,
                "last_check": timestamp,
                "error": "swman not available",
            }

        self._save_cache(self.packages_cache, data)

    def _refresh_git_cache(self) -> None:
        """Refresh git status cache"""
        timestamp = int(time.time())
        data: dict[str, str | int | bool] = {"enabled": True, "last_check": timestamp}

        try:
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"], capture_output=True, timeout=5
            )

            if result.returncode == 0:
                data["in_repo"] = True

                # Get current branch
                branch_result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                data["branch"] = branch_result.stdout.strip() or "detached"

                # Count uncommitted changes
                status_result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                data["uncommitted"] = (
                    len(status_result.stdout.strip().split("\n"))
                    if status_result.stdout.strip()
                    else 0
                )

                # Count commits ahead/behind
                data["ahead"] = 0
                data["behind"] = 0

                branch_value = data.get("branch")
                if branch_value != "detached":
                    try:
                        upstream_result = subprocess.run(
                            ["git", "rev-parse", "--abbrev-ref", "@{upstream}"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if upstream_result.returncode == 0:
                            upstream = upstream_result.stdout.strip()

                            counts_result = subprocess.run(
                                [
                                    "git",
                                    "rev-list",
                                    "--left-right",
                                    "--count",
                                    f"{upstream}...HEAD",
                                ],
                                capture_output=True,
                                text=True,
                                timeout=5,
                            )
                            if counts_result.returncode == 0:
                                counts = counts_result.stdout.strip().split()
                                if len(counts) == 2:
                                    data["behind"] = int(counts[0])
                                    data["ahead"] = int(counts[1])
                    except Exception:
                        pass  # No upstream or other git issue
            else:
                data["in_repo"] = False

        except Exception as e:
            data["error"] = f"Git check failed: {e}"

        self._save_cache(self.git_cache, data)

    def _refresh_init_cache(self) -> None:
        """Refresh init script status cache"""
        timestamp = int(time.time())
        data: dict[str, str | int | bool | float] = {
            "enabled": True,
            "last_check": timestamp,
        }

        # Check if we're in dotfiles directory
        if Path("./init.py").exists():
            data["in_dotfiles"] = True

            # Check last run time
            last_run_file = Path.home() / ".cache" / "dotfiles_last_update"
            last_run = 0

            if last_run_file.exists():
                try:
                    with open(last_run_file, "r") as f:
                        last_run_str = f.read().strip()
                    # Parse ISO format timestamp
                    from datetime import datetime

                    last_run_dt = datetime.fromisoformat(last_run_str)
                    last_run = int(last_run_dt.timestamp())
                except Exception:
                    pass

            data["last_run"] = last_run
            age_hours = (timestamp - last_run) / 3600
            data["age_hours"] = age_hours

            # Consider update needed if more than 7 days old
            data["needs_update"] = age_hours > 168
        else:
            data["in_dotfiles"] = False

        self._save_cache(self.init_cache, data)

    def get_status(self, force_refresh: bool = False) -> StatusResult:
        """Get complete status"""
        return StatusResult(
            packages=self.get_packages_status(force_refresh),
            git=self.get_git_status(force_refresh),
            init=self.get_init_status(force_refresh),
        )

    def format_quiet_output(self, status: StatusResult) -> str:
        """Format output for quiet mode (only show if issues)"""
        messages: list[str] = []

        # Check package updates
        _status_str, pkg_data = status.packages
        total_updates_raw = pkg_data.get("total_updates", 0)
        total_updates = total_updates_raw if isinstance(total_updates_raw, int) else 0
        if total_updates > 0:
            stale_raw = pkg_data.get("stale", False)
            stale = stale_raw if isinstance(stale_raw, bool) else False
            if stale:
                messages.append(
                    f"⚠️  {total_updates} package updates available (stale cache)"
                )
            else:
                last_check_raw = pkg_data.get("last_check", 0)
                last_check = last_check_raw if isinstance(last_check_raw, int) else 0
                age = self._format_age(last_check)
                messages.append(f"⚠️  {total_updates} package updates available ({age})")

        # Check git status
        git_data = status.git
        enabled_raw = git_data.get("enabled", False)
        in_repo_raw = git_data.get("in_repo", False)
        enabled = enabled_raw if isinstance(enabled_raw, bool) else False
        in_repo = in_repo_raw if isinstance(in_repo_raw, bool) else False
        if enabled and in_repo:
            uncommitted_raw = git_data.get("uncommitted", 0)
            ahead_raw = git_data.get("ahead", 0)
            uncommitted = uncommitted_raw if isinstance(uncommitted_raw, int) else 0
            ahead = ahead_raw if isinstance(ahead_raw, int) else 0
            if uncommitted > 0 or ahead > 0:
                git_msg = "🔄 Git:"
                if uncommitted > 0:
                    git_msg += f" {uncommitted} uncommitted"
                if ahead > 0:
                    git_msg += f" {ahead} unpushed"
                messages.append(git_msg)

        # Check init status
        init_data = status.init
        init_enabled_raw = init_data.get("enabled", False)
        needs_update_raw = init_data.get("needs_update", False)
        init_enabled = init_enabled_raw if isinstance(init_enabled_raw, bool) else False
        needs_update = needs_update_raw if isinstance(needs_update_raw, bool) else False
        if init_enabled and needs_update:
            age_hours_raw = init_data.get("age_hours", 0)
            age_hours = age_hours_raw if isinstance(age_hours_raw, (int, float)) else 0
            messages.append(f"⚙️  Init script not run in {int(age_hours / 24)}d")

        # Add tool name prefix to all messages
        if messages:
            prefixed_messages = [f"pkgstatus: {messages[0]}"]
            prefixed_messages.extend(f"pkgstatus: {msg}" for msg in messages[1:])
            return "\n".join(prefixed_messages)
        return ""

    def format_interactive_output(self, status: StatusResult) -> str:
        """Format output for interactive mode"""
        lines = ["📦 Package Status:"]

        # Package status
        pkg_data = status.packages
        pkg_error = pkg_data.get("error")
        if pkg_error:
            lines.append(f"   ❌ {pkg_error}")
        else:
            total_updates = pkg_data.get("total_updates", 0)
            if total_updates > 0:
                if pkg_data.get("stale", False):
                    lines.append(
                        f"   ⚠️  {total_updates} updates available (checking for new updates...)"
                    )
                else:
                    last_check = pkg_data.get("last_check", 0)
                    age = self._format_age(last_check)
                    lines.append(
                        f"   ⚠️  {total_updates} updates available (checked {age})"
                    )

                # Show breakdown by manager
                packages = pkg_data.get("packages", {})
                for manager, info in packages.items():
                    if info.get("has_updates", False):
                        count = info.get("count", 0)
                        if count > 0:
                            lines.append(f"      • {manager}: {count} updates")
                        else:
                            lines.append(f"      • {manager}: updates available")
            else:
                lines.append("   ✅ All packages up to date")

        # Git status
        git_data = status.git
        if git_data.get("enabled", False):
            lines.extend(["", "🔄 Git Status:"])
            git_error = git_data.get("error")
            if git_error:
                lines.append(f"   ❌ {git_error}")
            elif git_data.get("in_repo", False):
                branch = git_data.get("branch", "unknown")
                uncommitted = git_data.get("uncommitted", 0)
                ahead = git_data.get("ahead", 0)
                behind = git_data.get("behind", 0)

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
        if init_data.get("enabled", False):
            lines.extend(["", "⚙️  Init Status:"])
            init_error = init_data.get("error")
            if init_error:
                lines.append(f"   ❌ {init_error}")
            elif init_data.get("in_dotfiles", False):
                if init_data.get("needs_update", False):
                    age_hours = init_data.get("age_hours", 0)
                    lines.append(
                        f"   ⚠️  Last run {int(age_hours / 24)}d ago - consider running"
                    )
                else:
                    last_run = init_data.get("last_run", 0)
                    age_desc = self._format_age(last_run)
                    lines.append(f"   ✅ Recently run ({age_desc})")
            else:
                lines.append("   ℹ️  Not in dotfiles directory")

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
def main(quiet, json_output, refresh, cache_dir, verbose):
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
        status = checker.get_status(refresh)
        gather_log.log_info("operation_completed")

        # Log comprehensive status summary
        logger.log_info(
            "status_check_completed",
            packages_total_updates=status.packages.get("total_updates", 0),
            packages_error=status.packages.get("error"),
            git_in_repo=status.git.get("in_repo", False),
            git_uncommitted=status.git.get("uncommitted", 0),
            git_ahead=status.git.get("ahead", 0),
            git_behind=status.git.get("behind", 0),
            init_needs_update=status.init.get("needs_update", False),
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
