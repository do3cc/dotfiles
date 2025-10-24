"""Tests for pkgstatus.py - Package and system status checker."""

from dotfiles.pkgstatus import (
    CheckStatus,
    UpdateCheckResult,
    UpdateCheckCache,
    GitStatus,
    InitScriptStatus,
    SystemStatus,
)
import json
import pytest
import time
from pathlib import Path


# ==============================================================================
# UpdateCheckResult Tests
# ==============================================================================


def test_update_check_result_to_dict():
    """to_dict() should convert UpdateCheckResult to dictionary."""
    result = UpdateCheckResult(name="apt", has_updates=True, count=10)
    data = result.to_dict()

    assert data == {"name": "apt", "has_updates": True, "count": 10}


def test_update_check_result_to_json():
    """to_json() should serialize to JSON string."""
    result = UpdateCheckResult(name="pacman", has_updates=False, count=0)
    json_str = result.to_json()

    parsed = json.loads(json_str)
    assert parsed["name"] == "pacman"
    assert parsed["has_updates"] is False
    assert parsed["count"] == 0


def test_update_check_result_from_dict():
    """from_dict() should create UpdateCheckResult from dictionary."""
    data = {"name": "yay", "has_updates": True, "count": 15}
    result = UpdateCheckResult.from_dict(data)

    assert result.name == "yay"
    assert result.has_updates is True
    assert result.count == 15


def test_update_check_result_from_json():
    """from_json() should deserialize from JSON string."""
    json_str = '{"name": "apt", "has_updates": true, "count": 7}'
    result = UpdateCheckResult.from_json(json_str)

    assert result.name == "apt"
    assert result.has_updates is True
    assert result.count == 7


def test_update_check_result_roundtrip():
    """Serialization and deserialization should be lossless."""
    original = UpdateCheckResult(name="test", has_updates=True, count=42)
    json_str = original.to_json()
    restored = UpdateCheckResult.from_json(json_str)

    assert restored.name == original.name
    assert restored.has_updates == original.has_updates
    assert restored.count == original.count


# ==============================================================================
# UpdateCheckCache Tests
# ==============================================================================


def test_update_check_cache_to_dict():
    """to_dict() should convert UpdateCheckCache to dictionary."""
    packages = [UpdateCheckResult(name="apt", has_updates=False, count=0)]
    cache = UpdateCheckCache(
        packages=packages,
        total_updates=0,
        last_check=789,
        status=CheckStatus.SUCCESS,
    )
    data = cache.to_dict()

    assert data["total_updates"] == 0
    assert data["last_check"] == 789
    assert data["status"] == "success"
    assert len(data["packages"]) == 1
    assert data["packages"][0]["name"] == "apt"


def test_update_check_cache_to_json():
    """to_json() should serialize to JSON string."""
    cache = UpdateCheckCache(total_updates=5, last_check=999)
    json_str = cache.to_json()

    parsed = json.loads(json_str)
    assert parsed["total_updates"] == 5
    assert parsed["last_check"] == 999


def test_update_check_cache_from_dict():
    """from_dict() should create UpdateCheckCache from dictionary."""
    data = {
        "packages": [
            {"name": "pacman", "has_updates": True, "count": 10},
            {"name": "yay", "has_updates": False, "count": 0},
        ],
        "total_updates": 10,
        "last_check": 555,
        "status": "success",
    }
    cache = UpdateCheckCache.from_dict(data)

    assert len(cache.packages) == 2
    assert cache.packages[0].name == "pacman"
    assert cache.packages[1].name == "yay"
    assert cache.total_updates == 10
    assert cache.status == CheckStatus.SUCCESS


def test_update_check_cache_from_json():
    """from_json() should deserialize from JSON string."""
    json_str = '{"packages": [], "total_updates": 0, "last_check": 111, "status": "unavailable"}'
    cache = UpdateCheckCache.from_json(json_str)

    assert cache.packages == []
    assert cache.total_updates == 0
    assert cache.last_check == 111
    assert cache.status == CheckStatus.UNAVAILABLE


def test_update_check_cache_roundtrip():
    """Serialization and deserialization should be lossless."""
    packages = [
        UpdateCheckResult(name="test1", has_updates=True, count=5),
        UpdateCheckResult(name="test2", has_updates=False, count=0),
    ]
    original = UpdateCheckCache(
        packages=packages, total_updates=5, last_check=999, status=CheckStatus.FAILED
    )

    json_str = original.to_json()
    restored = UpdateCheckCache.from_json(json_str)

    assert len(restored.packages) == len(original.packages)
    assert restored.total_updates == original.total_updates
    assert restored.last_check == original.last_check
    assert restored.status == original.status


# ==============================================================================
# GitStatus Tests
# ==============================================================================


def test_git_status_to_json():
    """to_json() should serialize to JSON string."""
    status = GitStatus(branch="develop", uncommitted=2)
    json_str = status.to_json()

    parsed = json.loads(json_str)
    assert parsed["branch"] == "develop"
    assert parsed["uncommitted"] == 2


def test_git_status_from_json():
    """from_json() should deserialize from JSON string."""
    json_str = '{"enabled": false, "in_repo": false, "branch": "detached", "uncommitted": 0, "ahead": 0, "behind": 0, "last_check": 0, "status": "unavailable"}'
    status = GitStatus.from_json(json_str)

    assert status.enabled is False
    assert status.status == CheckStatus.UNAVAILABLE


def test_git_status_roundtrip():
    """Serialization and deserialization should be lossless."""
    original = GitStatus(
        last_check=555,
        enabled=True,
        in_repo=True,
        uncommitted=7,
        ahead=3,
        behind=1,
        branch="feature/test",
        status=CheckStatus.SUCCESS,
    )

    json_str = original.to_json()
    restored = GitStatus.from_json(json_str)

    assert restored.last_check == original.last_check
    assert restored.enabled == original.enabled
    assert restored.in_repo == original.in_repo
    assert restored.uncommitted == original.uncommitted
    assert restored.ahead == original.ahead
    assert restored.behind == original.behind
    assert restored.branch == original.branch
    assert restored.status == original.status


# ==============================================================================
# InitScriptStatus Tests
# ==============================================================================


def test_init_script_status_age_hours_infinity_when_never_run():
    """age_hours should be infinity when last_run is 0 (never run)."""
    status = InitScriptStatus(last_run=0)
    assert status.age_hours == float("inf")


def test_init_script_status_age_hours_calculation():
    """age_hours should calculate hours since last run."""
    # Set last_run to 2 hours ago
    two_hours_ago = int(time.time() - 7200)
    status = InitScriptStatus(last_run=two_hours_ago)

    # Should be approximately 2 hours (allow some tolerance for test execution time)
    assert 1.9 <= status.age_hours <= 2.1


def test_init_script_status_needs_update_true_when_never_run():
    """needs_update should be True when never run (last_run=0)."""
    status = InitScriptStatus(last_run=0)
    assert status.needs_update is True


def test_init_script_status_needs_update_false_when_recent():
    """needs_update should be False when last run was recent."""
    # Set last_run to 1 day ago (24 hours)
    one_day_ago = int(time.time() - 86400)
    status = InitScriptStatus(last_run=one_day_ago)

    assert status.needs_update is False


def test_init_script_status_needs_update_true_when_old():
    """needs_update should be True when last run was >7 days ago."""
    # Set last_run to 8 days ago (192 hours)
    eight_days_ago = int(time.time() - 691200)
    status = InitScriptStatus(last_run=eight_days_ago)

    assert status.needs_update is True


def test_init_script_status_needs_update_boundary():
    """needs_update should trigger at exactly 168 hours (7 days)."""
    # Test just under 168 hours (should not need update)
    just_under = int(time.time() - (168 * 3600 - 60))
    status1 = InitScriptStatus(last_run=just_under)
    assert status1.needs_update is False

    just_over = int(time.time() - (168 * 3600 + 60))
    status2 = InitScriptStatus(last_run=just_over)
    assert status2.needs_update is True


def test_init_script_status_to_json():
    """to_json() should serialize to JSON string."""
    status = InitScriptStatus(enabled=True, last_run=555)
    json_str = status.to_json()

    parsed = json.loads(json_str)
    assert parsed["enabled"] is True
    assert parsed["last_run"] == 555


def test_init_script_status_from_json():
    """from_json() should deserialize from JSON string."""
    json_str = '{"enabled": false, "last_check": 0, "last_run": 0, "status": "unavailable", "dotfiles_found": false}'
    status = InitScriptStatus.from_json(json_str)

    assert status.enabled is False
    assert status.status == CheckStatus.UNAVAILABLE


def test_init_script_status_roundtrip():
    """Serialization and deserialization should be lossless."""
    original = InitScriptStatus(
        enabled=True,
        last_check=999,
        last_run=888,
        status=CheckStatus.SUCCESS,
        dotfiles_found=True,
    )

    json_str = original.to_json()
    restored = InitScriptStatus.from_json(json_str)

    assert restored.enabled == original.enabled
    assert restored.last_check == original.last_check
    assert restored.last_run == original.last_run
    assert restored.status == original.status
    assert restored.dotfiles_found == original.dotfiles_found


# ==============================================================================
# SystemStatus Tests
# ==============================================================================
# (No tests needed - SystemStatus is a simple dataclass with no business logic)


# ==============================================================================
# StatusChecker Tests
# ==============================================================================


def test_status_checker_initialization(tmp_path):
    """StatusChecker should initialize with correct cache directory structure."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    assert checker.cache_dir == tmp_path / "dotfiles" / "status"
    assert checker.cache_dir.exists()
    assert checker.packages_cache == checker.cache_dir / "packages.json"
    assert checker.git_cache == checker.cache_dir / "git.json"
    assert checker.init_cache == checker.cache_dir / "init.json"


@pytest.mark.parametrize(
    "file_exists,file_age_seconds,max_age_hours,expected_expired",
    [
        (False, 0, 1, True),  # file doesn't exist
        (True, 1800, 1, False),  # 30 minutes old, max 1 hour - not expired
        (True, 7200, 1, True),  # 2 hours old, max 1 hour - expired
        (True, 3595, 1, False),  # just under 1 hour old - not expired (boundary)
        (True, 3605, 1, True),  # just over 1 hour old - expired (boundary)
    ],
)
def test_status_checker_is_cache_expired(
    tmp_path, file_exists, file_age_seconds, max_age_hours, expected_expired
):
    """is_cache_expired() should correctly determine cache freshness."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))
    cache_file = tmp_path / "test_cache.json"

    if file_exists:
        cache_file.write_text("{}")
        # Set file modification time to simulate age
        mtime = time.time() - file_age_seconds
        import os

        os.utime(cache_file, (mtime, mtime))

    assert checker.is_cache_expired(cache_file, max_age_hours) is expected_expired


@pytest.mark.parametrize(
    "timestamp,expected_output",
    [
        (0, "never"),  # zero timestamp
        (int(time.time() - 30), "just now"),  # 30 seconds ago
        (int(time.time() - 120), "2m ago"),  # 2 minutes ago
        (int(time.time() - 3600), "1h ago"),  # 1 hour ago
        (int(time.time() - 7200), "2h ago"),  # 2 hours ago
        (int(time.time() - 86400), "1d ago"),  # 1 day ago
        (int(time.time() - 172800), "2d ago"),  # 2 days ago
    ],
)
def test_status_checker_format_age(timestamp, expected_output):
    """_format_age() should format timestamps as human-readable strings."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker()
    assert checker._format_age(timestamp) == expected_output


# ==============================================================================
# StatusChecker Cache Operations Tests
# ==============================================================================


def test_status_checker_load_cache_missing_file(tmp_path):
    """_load_cache() should return default when cache file doesn't exist."""
    from dotfiles.pkgstatus import StatusChecker
    from dotfiles.logging_config import setup_logging

    checker = StatusChecker(cache_dir=str(tmp_path))
    logger = setup_logging("test")
    cache_file = tmp_path / "nonexistent.json"

    # Should return default GitStatus instance
    result = checker._load_cache(cache_file, GitStatus, GitStatus, logger)

    assert isinstance(result, GitStatus)
    assert result.enabled is False
    assert result.in_repo is False


def test_status_checker_load_cache_existing_file(tmp_path):
    """_load_cache() should load and deserialize existing cache file."""
    from dotfiles.pkgstatus import StatusChecker
    from dotfiles.logging_config import setup_logging

    checker = StatusChecker(cache_dir=str(tmp_path))
    logger = setup_logging("test")
    cache_file = tmp_path / "git.json"

    # Create a cache file with valid GitStatus JSON
    git_status = GitStatus(
        enabled=True, in_repo=True, branch="main", uncommitted=5, ahead=2, behind=1
    )
    cache_file.write_text(git_status.to_json())

    # Load should return the cached data
    result = checker._load_cache(cache_file, GitStatus, GitStatus, logger)

    assert result.enabled is True
    assert result.in_repo is True
    assert result.branch == "main"
    assert result.uncommitted == 5
    assert result.ahead == 2
    assert result.behind == 1


def test_status_checker_load_cache_corrupted_file(tmp_path):
    """_load_cache() should raise exception when cache file is corrupted."""
    from dotfiles.pkgstatus import StatusChecker
    from dotfiles.logging_config import setup_logging

    checker = StatusChecker(cache_dir=str(tmp_path))
    logger = setup_logging("test")
    cache_file = tmp_path / "corrupted.json"

    # Write invalid JSON
    cache_file.write_text("{invalid json")

    # Should raise exception (not return default)
    with pytest.raises(Exception):
        checker._load_cache(cache_file, GitStatus, GitStatus, logger)


def test_status_checker_save_cache(tmp_path):
    """_save_cache() should atomically save data to cache file."""
    from dotfiles.pkgstatus import StatusChecker
    from dotfiles.logging_config import setup_logging

    checker = StatusChecker(cache_dir=str(tmp_path))
    logger = setup_logging("test")
    cache_file = checker.cache_dir / "test.json"

    # Save a GitStatus object
    git_status = GitStatus(enabled=True, in_repo=True, branch="develop", uncommitted=3)
    checker._save_cache(cache_file, git_status, logger)

    # File should exist and contain correct JSON
    assert cache_file.exists()
    loaded = GitStatus.from_json(cache_file.read_text())
    assert loaded.branch == "develop"
    assert loaded.uncommitted == 3


def test_status_checker_save_cache_atomic_write(tmp_path):
    """_save_cache() should use temp file for atomic writes."""
    from dotfiles.pkgstatus import StatusChecker
    from dotfiles.logging_config import setup_logging

    checker = StatusChecker(cache_dir=str(tmp_path))
    logger = setup_logging("test")
    cache_file = checker.cache_dir / "atomic.json"

    # Save data
    init_status = InitScriptStatus(enabled=True, last_run=12345)
    checker._save_cache(cache_file, init_status, logger)

    # Temp file should not exist after successful write
    temp_file = cache_file.with_suffix(".tmp")
    assert not temp_file.exists()
    assert cache_file.exists()


def test_status_checker_load_cache_with_callable_default(tmp_path):
    """_load_cache() should support callable default_factory."""
    from dotfiles.pkgstatus import StatusChecker
    from dotfiles.logging_config import setup_logging

    checker = StatusChecker(cache_dir=str(tmp_path))
    logger = setup_logging("test")
    cache_file = tmp_path / "nonexistent.json"

    # Use a lambda as default_factory (like get_init_status does)
    result = checker._load_cache(
        cache_file,
        InitScriptStatus,
        lambda: InitScriptStatus(enabled=True, status=CheckStatus.UNAVAILABLE),
        logger,
    )

    assert isinstance(result, InitScriptStatus)
    assert result.enabled is True
    assert result.status == CheckStatus.UNAVAILABLE


# ==============================================================================
# StatusChecker Output Formatting Tests
# ==============================================================================


def test_status_checker_format_quiet_output_no_issues(tmp_path):
    """format_quiet_output() should return empty string when no issues."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    # Create status with no issues
    status = SystemStatus(
        packages=UpdateCheckCache(total_updates=0, last_check=int(time.time())),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(enabled=True, in_repo=True, uncommitted=0, ahead=0),
        init=InitScriptStatus(enabled=True, last_run=int(time.time())),
    )

    output = checker.format_quiet_output(status)
    assert output == ""


def test_status_checker_format_quiet_output_with_package_updates(tmp_path):
    """format_quiet_output() should show package updates."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    # Create status with package updates
    status = SystemStatus(
        packages=UpdateCheckCache(total_updates=5, last_check=int(time.time() - 3600)),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(enabled=False),
        init=InitScriptStatus(enabled=False),
    )

    output = checker.format_quiet_output(status)
    assert "pkgstatus:" in output
    assert "5 package updates available" in output
    assert "1h ago" in output


def test_status_checker_format_quiet_output_with_git_changes(tmp_path):
    """format_quiet_output() should show git uncommitted/unpushed changes."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    # Create status with git changes
    status = SystemStatus(
        packages=UpdateCheckCache(total_updates=0),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(enabled=True, in_repo=True, uncommitted=3, ahead=2),
        init=InitScriptStatus(enabled=False),
    )

    output = checker.format_quiet_output(status)
    assert "pkgstatus:" in output
    assert "Git:" in output
    assert "3 uncommitted" in output
    assert "2 unpushed" in output


def test_status_checker_format_quiet_output_with_stale_init(tmp_path):
    """format_quiet_output() should show stale init script."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    # Create status with old init script (10 days ago)
    ten_days_ago = int(time.time() - (10 * 86400))
    status = SystemStatus(
        packages=UpdateCheckCache(total_updates=0),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(enabled=False),
        init=InitScriptStatus(enabled=True, last_run=ten_days_ago),
    )

    output = checker.format_quiet_output(status)
    assert "pkgstatus:" in output
    assert "Init script not run in" in output
    assert "10d" in output


def test_status_checker_format_quiet_output_with_never_run_init(tmp_path):
    """format_quiet_output() should show never-run init script."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    # Create status with never-run init script
    status = SystemStatus(
        packages=UpdateCheckCache(total_updates=0),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(enabled=False),
        init=InitScriptStatus(enabled=True, last_run=0),
    )

    output = checker.format_quiet_output(status)
    assert "pkgstatus:" in output
    assert "Init script never run" in output


def test_status_checker_format_quiet_output_multiple_issues(tmp_path):
    """format_quiet_output() should show all issues with pkgstatus prefix."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    # Create status with multiple issues
    status = SystemStatus(
        packages=UpdateCheckCache(total_updates=10, last_check=int(time.time())),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(enabled=True, in_repo=True, uncommitted=5, ahead=3),
        init=InitScriptStatus(enabled=True, last_run=int(time.time() - (8 * 86400))),
    )

    output = checker.format_quiet_output(status)
    lines = output.split("\n")

    # All lines should have pkgstatus prefix
    assert all(line.startswith("pkgstatus:") for line in lines)
    assert len(lines) == 3  # packages, git, init


def test_status_checker_format_interactive_output_all_good(tmp_path):
    """format_interactive_output() should show clean status."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    # Create status with no issues
    status = SystemStatus(
        packages=UpdateCheckCache(total_updates=0, last_check=int(time.time())),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(enabled=True, in_repo=True, uncommitted=0, ahead=0, behind=0),
        init=InitScriptStatus(
            enabled=True, last_run=int(time.time()), dotfiles_found=True
        ),
    )

    output = checker.format_interactive_output(status)

    assert "📦 Package Status:" in output
    assert "All packages up to date" in output
    assert "🔄 Git Status:" in output
    assert "Working tree clean and up to date" in output
    assert "⚙️  Init Status:" in output
    assert "Recently run" in output


def test_status_checker_format_interactive_output_with_issues(tmp_path):
    """format_interactive_output() should show detailed issue breakdown."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    # Create status with multiple package updates
    packages = [
        UpdateCheckResult(name="pacman", has_updates=True, count=5),
        UpdateCheckResult(name="yay", has_updates=True, count=3),
    ]
    status = SystemStatus(
        packages=UpdateCheckCache(
            packages=packages, total_updates=8, last_check=int(time.time() - 7200)
        ),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(
            enabled=True, in_repo=True, branch="main", uncommitted=2, ahead=1, behind=0
        ),
        init=InitScriptStatus(enabled=False),
    )

    output = checker.format_interactive_output(status)

    # Check package section
    assert "8 updates available" in output
    assert "2h ago" in output
    assert "pacman: 5 updates" in output
    assert "yay: 3 updates" in output

    # Check git section
    assert "Branch: main" in output
    assert "2 uncommitted changes" in output
    assert "1 commits ahead of origin" in output


def test_status_checker_format_interactive_output_not_in_git_repo(tmp_path):
    """format_interactive_output() should handle not being in git repo."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    status = SystemStatus(
        packages=UpdateCheckCache(total_updates=0),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(enabled=True, in_repo=False),
        init=InitScriptStatus(enabled=True, dotfiles_found=False),
    )

    output = checker.format_interactive_output(status)

    assert "Not in a git repository" in output
    assert "Dotfiles not found at" in output


def test_status_checker_format_interactive_output_with_failed_checks(tmp_path):
    """format_interactive_output() should show failed check statuses."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    status = SystemStatus(
        packages=UpdateCheckCache(total_updates=0, status=CheckStatus.FAILED),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(enabled=True, in_repo=True, status=CheckStatus.FAILED),
        init=InitScriptStatus(
            enabled=True, status=CheckStatus.FAILED, dotfiles_found=True
        ),
    )

    output = checker.format_interactive_output(status)

    assert "Package check failed" in output
    assert "Git check failed" in output
    assert "Init check failed" in output


def test_status_checker_format_interactive_output_with_never_run_init(tmp_path):
    """format_interactive_output() should show never-run init script."""
    from dotfiles.pkgstatus import StatusChecker

    checker = StatusChecker(cache_dir=str(tmp_path))

    # Create status with never-run init script
    status = SystemStatus(
        packages=UpdateCheckCache(total_updates=0),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(enabled=False),
        init=InitScriptStatus(enabled=True, dotfiles_found=True, last_run=0),
    )

    output = checker.format_interactive_output(status)

    assert "⚙️  Init Status:" in output
    assert "Init script never run - consider running" in output


# ==============================================================================
# StatusChecker _refresh_init_cache Tests (DOTFILES_DIR Environment Variable)
# ==============================================================================


def test_refresh_init_cache_uses_dotfiles_dir_env(tmp_path, monkeypatch):
    """Should use DOTFILES_DIR environment variable when set"""
    from dotfiles.pkgstatus import StatusChecker
    from dotfiles.logging_config import setup_logging
    from dotfiles.output_formatting import ConsoleOutput

    # Setup fake dotfiles repo in custom location
    fake_dotfiles = tmp_path / "custom-dotfiles"
    fake_dotfiles.mkdir()
    (fake_dotfiles / "src" / "dotfiles").mkdir(parents=True)
    (fake_dotfiles / "src" / "dotfiles" / "init.py").touch()

    # Create and change to different directory
    other_dir = tmp_path / "other-dir"
    other_dir.mkdir()
    monkeypatch.setenv("DOTFILES_DIR", str(fake_dotfiles))
    monkeypatch.chdir(other_dir)

    checker = StatusChecker(cache_dir=str(tmp_path / "cache"))
    logger = setup_logging("test").bind()

    checker._refresh_init_cache(logger)

    # Should detect init.py via DOTFILES_DIR
    init_status = checker._load_cache(
        checker.init_cache, InitScriptStatus, InitScriptStatus, logger
    )
    assert init_status.dotfiles_found is True


def test_refresh_init_cache_uses_default_path_when_env_unset(tmp_path, monkeypatch):
    """Should use ~/projects/dotfiles fallback when DOTFILES_DIR unset"""
    from dotfiles.pkgstatus import StatusChecker
    from dotfiles.logging_config import setup_logging
    from dotfiles.output_formatting import ConsoleOutput

    monkeypatch.delenv("DOTFILES_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    # Create fake default dotfiles location
    default_dotfiles = tmp_path / "projects" / "dotfiles"
    default_dotfiles.mkdir(parents=True)
    (default_dotfiles / "src" / "dotfiles").mkdir(parents=True)
    (default_dotfiles / "src" / "dotfiles" / "init.py").touch()

    # Mock Path.expanduser to redirect to our tmp_path
    original_expanduser = Path.expanduser

    def mock_expanduser(self):  # type: ignore[no-untyped-def]
        path_str = str(self)
        if "~/projects/dotfiles" in path_str:
            return default_dotfiles
        return original_expanduser(self)

    monkeypatch.setattr(Path, "expanduser", mock_expanduser)

    checker = StatusChecker(cache_dir=str(tmp_path / "cache"))
    logger = setup_logging("test").bind()

    checker._refresh_init_cache(logger)

    init_status = checker._load_cache(
        checker.init_cache, InitScriptStatus, InitScriptStatus, logger
    )
    assert init_status.dotfiles_found is True


def test_format_interactive_output_dotfiles_not_found(tmp_path, monkeypatch):
    """Should show helpful error with DOTFILES_DIR path when dotfiles not found"""
    from dotfiles.pkgstatus import StatusChecker
    import os

    checker = StatusChecker(cache_dir=str(tmp_path))

    # Set a non-existent DOTFILES_DIR to test the error message
    monkeypatch.setenv("DOTFILES_DIR", "/nonexistent/path")

    status = SystemStatus(
        packages=UpdateCheckCache(),
        package_cache_path=tmp_path / "packages.json",
        git=GitStatus(),
        init=InitScriptStatus(enabled=True, dotfiles_found=False)
    )

    output = checker.format_interactive_output(status)

    # Should show error with path
    assert "Dotfiles not found at" in output
    assert "/nonexistent/path" in output


# ==============================================================================
# StatusChecker Public Methods Tests (get_* methods)
# ==============================================================================
# NOTE: Tests for get_packages_status(), get_git_status(), get_init_status(), and
# get_system_status() are NOT included here because they would require mocking
# internal methods of the StatusChecker class itself, which defeats the purpose
# of testing. These methods are orchestration logic that call external commands
# (pacman, git, fish) and are best tested via integration tests in Docker containers.
#
# The internal helper methods (_load_cache, _save_cache, is_cache_expired, etc.)
# ARE tested above with real file I/O, providing confidence in the building blocks.
