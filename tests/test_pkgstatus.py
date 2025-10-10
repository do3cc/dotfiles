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
import time


# ==============================================================================
# UpdateCheckResult Tests
# ==============================================================================


# TODO: REVIEW
# XXX Group these tests by using parametrize
def test_update_check_result_defaults():
    """UpdateCheckResult should have default values."""
    result = UpdateCheckResult(name="pacman")
    assert result.name == "pacman"
    assert result.has_updates is False
    assert result.count == 0


# TODO: REVIEW
def test_update_check_result_with_updates():
    """UpdateCheckResult should store update information."""
    result = UpdateCheckResult(name="yay", has_updates=True, count=5)
    assert result.name == "yay"
    assert result.has_updates is True
    assert result.count == 5


# TODO: REVIEW
def test_update_check_result_to_dict():
    """to_dict() should convert UpdateCheckResult to dictionary."""
    result = UpdateCheckResult(name="apt", has_updates=True, count=10)
    data = result.to_dict()

    assert data == {"name": "apt", "has_updates": True, "count": 10}


# TODO: REVIEW
def test_update_check_result_to_json():
    """to_json() should serialize to JSON string."""
    result = UpdateCheckResult(name="pacman", has_updates=False, count=0)
    json_str = result.to_json()

    parsed = json.loads(json_str)
    assert parsed["name"] == "pacman"
    assert parsed["has_updates"] is False
    assert parsed["count"] == 0


# TODO: REVIEW
# XXX Why do we have from_dict and to_dict even? Can we remove this safely?
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


# TODO: REVIEW
# Use parametrize to reduce some tests.
def test_update_check_cache_defaults():
    """UpdateCheckCache should have default values."""
    cache = UpdateCheckCache()
    assert cache.packages == []
    assert cache.total_updates == 0
    assert cache.last_check == 0
    assert cache.status == CheckStatus.SUCCESS


# TODO: REVIEW
def test_update_check_cache_with_packages():
    """UpdateCheckCache should store multiple package results."""
    packages = [
        UpdateCheckResult(name="pacman", has_updates=True, count=5),
        UpdateCheckResult(name="yay", has_updates=True, count=3),
    ]
    cache = UpdateCheckCache(packages=packages, total_updates=8, last_check=123456)

    assert len(cache.packages) == 2
    assert cache.total_updates == 8
    assert cache.last_check == 123456


# TODO: REVIEW
# Do we need to dict function
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


# TODO: REVIEW
# XXX Do we even need this function
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


# TODO: REVIEW
# XXX Use parametrize for the next few tests that essential do the same tests with different inputs
def test_git_status_defaults():
    """GitStatus should have default values."""
    status = GitStatus()
    assert status.last_check == 0
    assert status.enabled is False
    assert status.in_repo is False
    assert status.uncommitted == 0
    assert status.ahead == 0
    assert status.behind == 0
    assert status.branch == "detached"
    assert status.status == CheckStatus.SUCCESS


# TODO: REVIEW
def test_git_status_with_changes():
    """GitStatus should store repository state."""
    status = GitStatus(
        last_check=123,
        enabled=True,
        in_repo=True,
        uncommitted=5,
        ahead=2,
        behind=1,
        branch="feature/test",
    )

    assert status.enabled is True
    assert status.in_repo is True
    assert status.uncommitted == 5
    assert status.ahead == 2
    assert status.behind == 1
    assert status.branch == "feature/test"


# TODO: REVIEW
# XXX Do we need the to_dict functionality?
def test_git_status_to_dict():
    """to_dict() should convert GitStatus to dictionary."""
    status = GitStatus(
        enabled=True, in_repo=True, branch="main", uncommitted=3, ahead=1, behind=0
    )
    data = status.to_dict()

    assert data["enabled"] is True
    assert data["in_repo"] is True
    assert data["branch"] == "main"
    assert data["uncommitted"] == 3
    assert data["ahead"] == 1
    assert data["behind"] == 0


def test_git_status_to_json():
    """to_json() should serialize to JSON string."""
    status = GitStatus(branch="develop", uncommitted=2)
    json_str = status.to_json()

    parsed = json.loads(json_str)
    assert parsed["branch"] == "develop"
    assert parsed["uncommitted"] == 2


# TODO: REVIEW
# XXX Do we even need this function
def test_git_status_from_dict():
    """from_dict() should create GitStatus from dictionary."""
    data = {
        "last_check": 999,
        "enabled": True,
        "in_repo": True,
        "uncommitted": 10,
        "ahead": 5,
        "behind": 2,
        "branch": "main",
        "status": "success",
    }
    status = GitStatus.from_dict(data)

    assert status.last_check == 999
    assert status.enabled is True
    assert status.uncommitted == 10
    assert status.ahead == 5
    assert status.behind == 2
    assert status.branch == "main"


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


# TODO: REVIEW
# The next few tests do test the same thing with different inputs. Convert to parametrize
def test_init_script_status_defaults():
    """InitScriptStatus should have default values."""
    status = InitScriptStatus()
    assert status.enabled is False
    assert status.last_check == 0
    assert status.last_run == 0
    assert status.status == CheckStatus.SUCCESS
    assert status.in_dotfiles is False


# TODO: REVIEW
def test_init_script_status_with_data():
    """InitScriptStatus should store execution information."""
    status = InitScriptStatus(
        enabled=True,
        last_check=123,
        last_run=100,
        in_dotfiles=True,
    )

    assert status.enabled is True
    assert status.last_check == 123
    assert status.last_run == 100
    assert status.in_dotfiles is True


# TODO: REVIEW
# XXX This is not the behavior that is sane! it should return something like max int.
# This behavior forces code to check for 0 and treat this as a special case.
# No need to treat maxint as special.
def test_init_script_status_age_hours_zero_when_never_run():
    """age_hours should be 0 when last_run is 0."""
    status = InitScriptStatus(last_run=0)
    assert status.age_hours == 0.0


def test_init_script_status_age_hours_calculation():
    """age_hours should calculate hours since last run."""
    # Set last_run to 2 hours ago
    two_hours_ago = int(time.time() - 7200)
    status = InitScriptStatus(last_run=two_hours_ago)

    # Should be approximately 2 hours (allow some tolerance for test execution time)
    assert 1.9 <= status.age_hours <= 2.1


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


# TODO: REVIEW
# Do we even need the todict method?
def test_init_script_status_to_dict():
    """to_dict() should convert InitScriptStatus to dictionary."""
    status = InitScriptStatus(
        enabled=True, last_check=999, last_run=888, in_dotfiles=True
    )
    data = status.to_dict()

    assert data["enabled"] is True
    assert data["last_check"] == 999
    assert data["last_run"] == 888
    assert data["in_dotfiles"] is True
    assert data["status"] == "success"


def test_init_script_status_to_json():
    """to_json() should serialize to JSON string."""
    status = InitScriptStatus(enabled=True, last_run=555)
    json_str = status.to_json()

    parsed = json.loads(json_str)
    assert parsed["enabled"] is True
    assert parsed["last_run"] == 555


# TODO: REVIEW
# Do we even need from_dict
def test_init_script_status_from_dict():
    """from_dict() should create InitScriptStatus from dictionary."""
    data = {
        "enabled": True,
        "last_check": 111,
        "last_run": 100,
        "status": "failed",
        "in_dotfiles": True,
    }
    status = InitScriptStatus.from_dict(data)

    assert status.enabled is True
    assert status.last_check == 111
    assert status.last_run == 100
    assert status.status == CheckStatus.FAILED
    assert status.in_dotfiles is True


def test_init_script_status_from_json():
    """from_json() should deserialize from JSON string."""
    json_str = '{"enabled": false, "last_check": 0, "last_run": 0, "status": "unavailable", "in_dotfiles": false}'
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
        in_dotfiles=True,
    )

    json_str = original.to_json()
    restored = InitScriptStatus.from_json(json_str)

    assert restored.enabled == original.enabled
    assert restored.last_check == original.last_check
    assert restored.last_run == original.last_run
    assert restored.status == original.status
    assert restored.in_dotfiles == original.in_dotfiles


# ==============================================================================
# SystemStatus Tests
# ==============================================================================


def test_system_status_initialization():
    """SystemStatus should store complete system state."""
    from pathlib import Path

    packages = UpdateCheckCache(total_updates=5)
    git = GitStatus(branch="main", uncommitted=2)
    init = InitScriptStatus(enabled=True, last_run=123)

    status = SystemStatus(
        packages=packages,
        package_cache_path=Path("/tmp/cache.json"),
        git=git,
        init=init,
    )

    assert status.packages.total_updates == 5
    assert status.package_cache_path == Path("/tmp/cache.json")
    assert status.git.branch == "main"
    assert status.init.enabled is True


def test_system_status_fields_are_dataclasses():
    """SystemStatus should contain the expected dataclass instances."""
    from pathlib import Path

    packages = UpdateCheckCache(total_updates=0)
    git = GitStatus()
    init = InitScriptStatus()

    status = SystemStatus(
        packages=packages, package_cache_path=Path("/tmp/test"), git=git, init=init
    )

    assert isinstance(status.packages, UpdateCheckCache)
    assert isinstance(status.git, GitStatus)
    assert isinstance(status.init, InitScriptStatus)
    assert isinstance(status.package_cache_path, Path)


# XXX Where are hypothesis tests?
# What about integration tests? Maybe configured that they must be called explicit and we put them in docker containers?
# Where are the methods tested?
