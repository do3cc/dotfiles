# pyright: strict
"""pkgstatus cache: what is cached, where it lives, and how it is read and written.

Shared by pkgstatus (which fills the cache) and swman (which invalidates it after
updates). Kept free of pkgstatus imports because pkgstatus imports swman.
"""

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from .logging_config import LoggingHelpers


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
        return {"name": self.name, "has_updates": self.has_updates, "count": self.count}

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

    packages: list[UpdateCheckResult] = field(default_factory=list[UpdateCheckResult])
    total_updates: int = 0
    last_check: int = 0
    status: CheckStatus = CheckStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "packages": [x.to_dict() for x in self.packages],
            "total_updates": self.total_updates,
            "last_check": self.last_check,
            "status": self.status.value,
        }

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
            {
                "last_check": self.last_check,
                "enabled": self.enabled,
                "in_repo": self.in_repo,
                "uncommitted": self.uncommitted,
                "ahead": self.ahead,
                "behind": self.behind,
                "branch": self.branch,
                "status": self.status.value,
            }
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
            {
                "enabled": self.enabled,
                "last_check": self.last_check,
                "last_run": self.last_run,
                "status": self.status.value,
                "dotfiles_found": self.dotfiles_found,
            }
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


class CacheRecord(Protocol):
    """Anything that can be stored in a cache entry."""

    def to_json(self) -> str: ...


class CacheEntry[T: CacheRecord]:
    """
    One cache file: where it lives, what it holds and how long it stays fresh.

    Attributes:
        path: Location of the JSON cache file
        max_age_hours: Default freshness window used by is_expired()
    """

    def __init__(
        self,
        path: Path,
        from_json: Callable[[str], T],
        default_factory: Callable[[], T],
        max_age_hours: int,
    ):
        self.path = path
        self.max_age_hours = max_age_hours
        self._from_json = from_json
        self._default_factory = default_factory

    def is_expired(self, max_age_hours: int | None = None) -> bool:
        """Missing or older than max_age_hours (default: the entry's own window)"""
        if not self.path.exists():
            return True

        if max_age_hours is None:
            max_age_hours = self.max_age_hours
        file_age = time.time() - self.path.stat().st_mtime
        return file_age > (max_age_hours * 3600)

    def load(self, logger: LoggingHelpers) -> T:
        """Load the cached record, or the default when nothing is cached yet"""
        logger = logger.bind(cache_file=str(self.path))
        # If cache file doesn't exist, return default (expected case)
        if not self.path.exists():
            logger.log_info("cache_file_not_found")
            return self._default_factory()

        # Cache file exists - attempt to load it
        # If this fails, it's a real error (corruption, permissions, etc.) that should be raised
        try:
            return self._from_json(self.path.read_text())
        except Exception as e:
            logger.log_exception(e, "cache_load_failed")
            raise

    def save(self, data: T, logger: LoggingHelpers) -> None:
        """Save the record atomically (temp file + rename)"""
        temp_file = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp_file.write_text(data.to_json())
            temp_file.replace(self.path)
        except Exception as e:
            logger.log_exception(e, "cache_save_failed", cache_file=str(self.path))
            if temp_file.exists():
                temp_file.unlink()

    def invalidate(self, logger: LoggingHelpers) -> None:
        """Delete the cache file so the next status check recomputes it"""
        logger = logger.bind(cache_file=str(self.path))
        try:
            self.path.unlink(missing_ok=True)
        except OSError as e:
            logger.log_exception(e, "cache_invalidation_failed")
            raise
        logger.log_info("cache_invalidated")


class StatusCache:
    """
    All pkgstatus cache entries, stored as JSON under $XDG_CACHE_HOME/dotfiles/status.

    Attributes:
        cache_dir: Base directory for all cache files
        packages: Package update counts (default 6h, overridable via fish config)
        git: Git status of the current directory (1h)
        init: Dotfiles init script freshness (24h)
    """

    def __init__(self, cache_dir: str | None = None):
        self.cache_dir = (
            Path(cache_dir or os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser()
            / "dotfiles"
            / "status"
        )
        self.packages = CacheEntry(
            self.cache_dir / "packages.json",
            UpdateCheckCache.from_json,
            UpdateCheckCache,
            max_age_hours=6,
        )
        self.git = CacheEntry(
            self.cache_dir / "git.json",
            GitStatus.from_json,
            GitStatus,
            max_age_hours=1,
        )
        self.init = CacheEntry(
            self.cache_dir / "init.json",
            InitScriptStatus.from_json,
            lambda: InitScriptStatus(enabled=True, status=CheckStatus.UNAVAILABLE),
            max_age_hours=24,
        )
