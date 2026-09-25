"""Tests for status_cache.py - pkgstatus cache entries and their storage."""

import json
import os
import time

import pytest

from dotfiles.logging_config import setup_logging
from dotfiles.status_cache import (
    CheckStatus,
    GitStatus,
    InitScriptStatus,
    StatusCache,
    UpdateCheckCache,
)


@pytest.fixture
def cache(tmp_path):
    return StatusCache(cache_dir=str(tmp_path))


@pytest.fixture
def logger():
    return setup_logging("test")


def test_status_cache_layout(tmp_path):
    """Each entry lives in its own file under dotfiles/status."""
    cache = StatusCache(cache_dir=str(tmp_path))

    assert cache.cache_dir == tmp_path / "dotfiles" / "status"
    assert cache.packages.path == cache.cache_dir / "packages.json"
    assert cache.git.path == cache.cache_dir / "git.json"
    assert cache.init.path == cache.cache_dir / "init.json"


def test_status_cache_does_not_touch_disk(tmp_path):
    """Creating a StatusCache (e.g. from swman) must not create directories."""
    StatusCache(cache_dir=str(tmp_path))

    assert not (tmp_path / "dotfiles").exists()


def test_status_cache_default_max_ages(cache):
    assert cache.packages.max_age_hours == 6
    assert cache.git.max_age_hours == 1
    assert cache.init.max_age_hours == 24


# ==============================================================================
# CacheEntry.is_expired
# ==============================================================================


@pytest.mark.parametrize(
    "file_exists,file_age_seconds,expected_expired",
    [
        (False, 0, True),  # file doesn't exist
        (True, 1800, False),  # 30 minutes old, max 1 hour - not expired
        (True, 7200, True),  # 2 hours old, max 1 hour - expired
        (True, 3595, False),  # just under 1 hour old - not expired (boundary)
        (True, 3605, True),  # just over 1 hour old - expired (boundary)
    ],
)
def test_is_expired_uses_entry_max_age(
    cache, file_exists, file_age_seconds, expected_expired
):
    """git entry has a 1 hour window."""
    if file_exists:
        cache.git.path.parent.mkdir(parents=True)
        cache.git.path.write_text("{}")
        mtime = time.time() - file_age_seconds
        os.utime(cache.git.path, (mtime, mtime))

    assert cache.git.is_expired() is expected_expired


def test_is_expired_override_max_age(cache):
    """An explicit max age (pkgstatus_cache_hours) wins over the default."""
    cache.packages.path.parent.mkdir(parents=True)
    cache.packages.path.write_text("{}")
    mtime = time.time() - 2 * 3600
    os.utime(cache.packages.path, (mtime, mtime))

    assert cache.packages.is_expired() is False  # default 6h
    assert cache.packages.is_expired(1) is True


# ==============================================================================
# CacheEntry.load / save
# ==============================================================================


def test_load_missing_file_returns_default(cache, logger):
    result = cache.git.load(logger)

    assert isinstance(result, GitStatus)
    assert result.enabled is False
    assert result.in_repo is False


def test_load_missing_init_returns_unavailable(cache, logger):
    """init entry uses a custom default when nothing is cached."""
    result = cache.init.load(logger)

    assert isinstance(result, InitScriptStatus)
    assert result.enabled is True
    assert result.status == CheckStatus.UNAVAILABLE


def test_save_then_load_roundtrip(cache, logger):
    git_status = GitStatus(
        enabled=True, in_repo=True, branch="main", uncommitted=5, ahead=2, behind=1
    )

    cache.git.save(git_status, logger)

    assert cache.git.load(logger) == git_status


def test_save_is_atomic(cache, logger):
    """Save goes through a temp file which is gone afterwards."""
    cache.init.save(InitScriptStatus(enabled=True, last_run=12345), logger)

    assert cache.init.path.exists()
    assert not cache.init.path.with_suffix(".tmp").exists()


def test_load_corrupted_file_raises(cache, logger):
    cache.git.path.parent.mkdir(parents=True)
    cache.git.path.write_text("{invalid json")

    with pytest.raises(json.JSONDecodeError):
        cache.git.load(logger)


# ==============================================================================
# CacheEntry.invalidate
# ==============================================================================


def test_invalidate_removes_only_that_entry(cache, logger):
    cache.packages.save(UpdateCheckCache(total_updates=3), logger)
    cache.git.save(GitStatus(), logger)

    cache.packages.invalidate(logger)

    assert not cache.packages.path.exists()
    assert cache.git.path.exists()
    assert cache.packages.is_expired()


def test_invalidate_missing_file_is_ok(cache, logger):
    """No cache yet is not an error."""
    cache.packages.invalidate(logger)


def test_invalidate_reraises_on_failure(cache, logger):
    """A cache that cannot be deleted must not fail silently."""
    # A directory in place of the file makes unlink() raise
    cache.packages.path.mkdir(parents=True)

    with pytest.raises(OSError):
        cache.packages.invalidate(logger)
