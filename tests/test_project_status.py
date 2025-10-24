"""Tests for project_status.py - Project status checker."""

import json
from unittest.mock import MagicMock, patch

import pytest

from dotfiles.logging_config import setup_logging
from dotfiles.project_status import (
    BranchInfo,
    IssueInfo,
    PRInfo,
    ProjectStatusChecker,
    WorktreeInfo,
)


# ==============================================================================
# IssueInfo Dataclass Tests
# ==============================================================================
# (No tests needed - IssueInfo is a simple dataclass with no business logic)


# ==============================================================================
# PRInfo Dataclass Tests
# ==============================================================================
# (No tests needed - PRInfo is a simple dataclass with no business logic)


# ==============================================================================
# BranchInfo Dataclass Tests
# ==============================================================================
# (No tests needed - BranchInfo is a simple dataclass with no business logic)


# ==============================================================================
# WorktreeInfo Dataclass Tests
# ==============================================================================
# (No tests needed - WorktreeInfo is a simple dataclass with no business logic)


# ==============================================================================
# ProjectStatusChecker Tests
# ==============================================================================


@pytest.fixture
def real_logging_helpers():
    """
    Real LoggingHelpers instance for integration testing ProjectStatusChecker.

    Unlike conftest.py's mock_logging_helpers (which returns a MagicMock),
    this fixture returns a real LoggingHelpers instance for integration tests
    that verify actual logging behavior.
    """
    return setup_logging("test")


@pytest.fixture
def output():
    """
    Real ConsoleOutput instance for integration testing ProjectStatusChecker.

    Unlike conftest.py's output fixture (which returns None),
    this fixture returns a real ConsoleOutput instance for integration tests.
    """
    from dotfiles.output_formatting import ConsoleOutput

    return ConsoleOutput()


# ==============================================================================
# get_github_issues() Tests
# ==============================================================================


def test_get_github_issues_success(real_logging_helpers, output):
    """get_github_issues() should parse gh command output into IssueInfo objects."""
    checker = ProjectStatusChecker()

    # Mock subprocess result
    mock_result = MagicMock()
    mock_result.stdout = json.dumps(
        [
            {
                "number": 123,
                "title": "Test Issue",
                "state": "OPEN",
                "labels": [{"name": "bug"}, {"name": "priority"}],
                "assignees": [{"login": "testuser"}],
                "url": "https://github.com/user/repo/issues/123",
            },
            {
                "number": 124,
                "title": "Another Issue",
                "state": "OPEN",
                "labels": [],
                "assignees": [],
                "url": "https://github.com/user/repo/issues/124",
            },
        ]
    )

    with patch(
        "dotfiles.project_status.run_command_with_error_handling",
        return_value=mock_result,
    ):
        issues = checker.get_github_issues(real_logging_helpers, output)

    assert len(issues) == 2
    assert issues[0].number == 123
    assert issues[0].title == "Test Issue"
    assert issues[0].labels == ["bug", "priority"]
    assert issues[0].assignee == "testuser"
    assert issues[1].number == 124
    assert issues[1].assignee is None


def test_get_github_issues_propagates_exceptions(real_logging_helpers, output):
    """get_github_issues() should propagate exceptions to caller."""
    checker = ProjectStatusChecker()

    with patch(
        "dotfiles.project_status.run_command_with_error_handling",
        side_effect=Exception("Command failed"),
    ):
        with pytest.raises(Exception, match="Command failed"):
            checker.get_github_issues(real_logging_helpers, output)


# ==============================================================================
# get_github_prs() Tests
# ==============================================================================


def test_get_github_prs_success(real_logging_helpers, output):
    """get_github_prs() should parse gh command output into PRInfo objects."""
    checker = ProjectStatusChecker()

    # Mock subprocess result
    mock_result = MagicMock()
    mock_result.stdout = json.dumps(
        [
            {
                "number": 456,
                "title": "Test PR",
                "state": "OPEN",
                "headRefName": "feature/test",
                "baseRefName": "main",
                "isDraft": False,
                "url": "https://github.com/user/repo/pull/456",
            },
            {
                "number": 457,
                "title": "Draft PR",
                "state": "OPEN",
                "headRefName": "feature/draft",
                "baseRefName": "main",
                "isDraft": True,
                "url": "https://github.com/user/repo/pull/457",
            },
        ]
    )

    with patch(
        "dotfiles.project_status.run_command_with_error_handling",
        return_value=mock_result,
    ):
        prs = checker.get_github_prs(real_logging_helpers, output)

    assert len(prs) == 2
    assert prs[0].number == 456
    assert prs[0].title == "Test PR"
    assert prs[0].branch == "feature/test"
    assert prs[0].base == "main"
    assert prs[0].draft is False
    assert prs[1].draft is True


def test_get_github_prs_propagates_exceptions(real_logging_helpers, output):
    """get_github_prs() should propagate exceptions to caller."""
    checker = ProjectStatusChecker()

    with patch(
        "dotfiles.project_status.run_command_with_error_handling",
        side_effect=Exception("Command failed"),
    ):
        with pytest.raises(Exception, match="Command failed"):
            checker.get_github_prs(real_logging_helpers, output)


# ==============================================================================
# get_worktrees() Tests
# ==============================================================================


def test_get_worktrees_success(real_logging_helpers, output):
    """get_worktrees() should parse git worktree list output."""
    checker = ProjectStatusChecker()

    # Mock subprocess result with porcelain format
    mock_result = MagicMock()
    mock_result.stdout = """worktree /home/user/dotfiles
HEAD abc1234567890
branch refs/heads/main

worktree /home/user/dotfiles/worktrees/feature/issue-53
HEAD def4567890123
branch refs/heads/issue-53

"""

    with patch(
        "dotfiles.project_status.run_command_with_error_handling",
        return_value=mock_result,
    ):
        worktrees = checker.get_worktrees(real_logging_helpers, output)

    assert len(worktrees) == 2
    assert worktrees[0].path == "/home/user/dotfiles"
    assert worktrees[0].branch == "refs/heads/main"
    assert worktrees[0].commit == "abc1234"
    assert worktrees[1].path == "/home/user/dotfiles/worktrees/feature/issue-53"
    assert worktrees[1].branch == "refs/heads/issue-53"


def test_get_worktrees_propagates_exceptions(real_logging_helpers, output):
    """get_worktrees() should propagate exceptions to caller."""
    checker = ProjectStatusChecker()

    with patch(
        "dotfiles.project_status.run_command_with_error_handling",
        side_effect=Exception("Command failed"),
    ):
        with pytest.raises(Exception, match="Command failed"):
            checker.get_worktrees(real_logging_helpers, output)


# ==============================================================================
# _process_worktree_info() Tests
# ==============================================================================


def test_process_worktree_info_main_worktree(real_logging_helpers, output):
    """_process_worktree_info() should identify main worktree."""
    checker = ProjectStatusChecker()

    wt_data = {
        "path": "/home/user/dotfiles",
        "branch": "refs/heads/main",
        "commit": "abc1234",
    }

    with patch("dotfiles.project_status.run_command_with_error_handling") as mock_run:
        mock_run.return_value.stdout = ""  # No uncommitted changes
        result = checker._process_worktree_info(wt_data, real_logging_helpers, output)

    assert result.path == "/home/user/dotfiles"
    assert result.branch == "refs/heads/main"
    assert result.commit == "abc1234"
    assert result.type_category == "main"
    assert result.has_uncommitted is False


def test_process_worktree_info_feature_worktree(real_logging_helpers, output):
    """_process_worktree_info() should extract type_category from path."""
    checker = ProjectStatusChecker()

    wt_data = {
        "path": "/home/user/dotfiles/worktrees/feature/issue-53",
        "branch": "refs/heads/issue-53",
        "commit": "def4567",
    }

    with patch("dotfiles.project_status.run_command_with_error_handling") as mock_run:
        mock_run.return_value.stdout = " M file.txt\n"  # Uncommitted changes
        result = checker._process_worktree_info(wt_data, real_logging_helpers, output)

    assert result.type_category == "feature"
    assert result.has_uncommitted is True


def test_process_worktree_info_detached(real_logging_helpers, output):
    """_process_worktree_info() should handle detached HEAD."""
    checker = ProjectStatusChecker()

    wt_data = {
        "path": "/home/user/dotfiles/worktrees/review/pr-123",
        "commit": "xyz9876",
        "detached": True,
    }

    with patch("dotfiles.project_status.run_command_with_error_handling") as mock_run:
        mock_run.return_value.stdout = ""
        result = checker._process_worktree_info(wt_data, real_logging_helpers, output)

    assert result.branch == "detached"
    assert result.type_category == "review"


def test_process_worktree_info_status_check_exception(real_logging_helpers, output):
    """_process_worktree_info() should handle status check exceptions gracefully.

    Status check failures are non-fatal - we log the exception and continue
    with has_uncommitted=False. This is correct behavior (graceful degradation).
    """
    checker = ProjectStatusChecker()

    wt_data = {
        "path": "/home/user/dotfiles",
        "branch": "refs/heads/main",
        "commit": "abc1234",
    }

    with patch(
        "dotfiles.project_status.run_command_with_error_handling",
        side_effect=Exception("git status failed"),
    ):
        result = checker._process_worktree_info(wt_data, real_logging_helpers, output)

    # Should handle exception gracefully (graceful degradation)
    assert result.has_uncommitted is False
    assert result.path == "/home/user/dotfiles"
    assert result.branch == "refs/heads/main"


def test_process_worktree_info_bare_worktree(real_logging_helpers, output):
    """_process_worktree_info() should skip status check for bare worktrees."""
    checker = ProjectStatusChecker()

    wt_data = {
        "path": "/home/user/dotfiles.git",
        "branch": "refs/heads/main",
        "commit": "abc1234",
        "bare": True,
    }

    with patch("dotfiles.project_status.run_command_with_error_handling") as mock_run:
        result = checker._process_worktree_info(wt_data, real_logging_helpers, output)
        # Should not call git status for bare worktree
        mock_run.assert_not_called()

    assert result.has_uncommitted is False


# ==============================================================================
# get_local_branches() Tests
# ==============================================================================


def test_get_local_branches_success(real_logging_helpers, output):
    """get_local_branches() should parse git branch info."""
    checker = ProjectStatusChecker()

    # Mock subprocess result for git for-each-ref
    mock_result = MagicMock()
    mock_result.stdout = """main|abc1234|2025-01-15 10:30:00 +0000|
feature/test|def5678|2025-01-16 14:20:00 +0000|><
bugfix/issue-42|ghi9012|2025-01-17 09:15:00 +0000|>
"""

    with (
        patch(
            "dotfiles.project_status.run_command_with_error_handling",
            return_value=mock_result,
        ),
        patch.object(checker, "get_worktrees", return_value=[]),
    ):
        branches = checker.get_local_branches(real_logging_helpers, output)

    assert len(branches) == 3
    assert branches[0].name == "main"
    assert branches[0].ahead == 0
    assert branches[0].behind == 0
    assert branches[1].name == "feature/test"
    assert branches[1].ahead == 1
    assert branches[1].behind == 1
    assert branches[2].name == "bugfix/issue-42"
    assert branches[2].ahead == 1
    assert branches[2].behind == 0


def test_get_local_branches_with_worktrees(real_logging_helpers, output):
    """get_local_branches() should associate branches with worktrees."""
    checker = ProjectStatusChecker()

    mock_result = MagicMock()
    mock_result.stdout = "feature/test|def5678|2025-01-16 14:20:00 +0000|\n"

    mock_worktree = WorktreeInfo(
        path="/home/user/dotfiles/worktrees/feature/test",
        branch="feature/test",
        commit="def5678",
        has_uncommitted=False,
        type_category="feature",
    )

    with (
        patch(
            "dotfiles.project_status.run_command_with_error_handling",
            return_value=mock_result,
        ),
        patch.object(checker, "get_worktrees", return_value=[mock_worktree]),
    ):
        branches = checker.get_local_branches(real_logging_helpers, output)

    assert len(branches) == 1
    assert branches[0].has_worktree is True
    assert branches[0].worktree_path == "/home/user/dotfiles/worktrees/feature/test"


def test_get_local_branches_propagates_exceptions(real_logging_helpers, output):
    """get_local_branches() should propagate exceptions to caller."""
    checker = ProjectStatusChecker()

    with patch(
        "dotfiles.project_status.run_command_with_error_handling",
        side_effect=Exception("Command failed"),
    ):
        with pytest.raises(Exception, match="Command failed"):
            checker.get_local_branches(real_logging_helpers, output)


# ==============================================================================
# format_status_report() Tests
# ==============================================================================


def test_format_status_report_text_format(real_logging_helpers, output):
    """format_status_report() should delegate to _format_text_report."""
    checker = ProjectStatusChecker()

    issues = [IssueInfo(123, "Test", "OPEN", ["bug"], None, "https://example.com/123")]
    prs = []
    branches = []
    worktrees = []

    with patch.object(
        checker, "_format_text_report", return_value="text output"
    ) as mock_text:
        result = checker.format_status_report(issues, prs, branches, worktrees, "text")

    mock_text.assert_called_once_with(issues, prs, branches, worktrees)
    assert result == "text output"


def test_format_status_report_json_format(real_logging_helpers, output):
    """format_status_report() should delegate to _format_json_report."""
    checker = ProjectStatusChecker()

    issues = []
    prs = []
    branches = []
    worktrees = []

    with patch.object(
        checker, "_format_json_report", return_value='{"issues": []}'
    ) as mock_json:
        result = checker.format_status_report(issues, prs, branches, worktrees, "json")

    mock_json.assert_called_once_with(issues, prs, branches, worktrees)
    assert result == '{"issues": []}'


# ==============================================================================
# _format_text_report() Tests
# ==============================================================================


def test_format_text_report_with_all_data(real_logging_helpers, output):
    """_format_text_report() should format comprehensive text report."""
    checker = ProjectStatusChecker()

    issues = [
        IssueInfo(
            123,
            "Bug Report",
            "OPEN",
            ["bug", "priority"],
            "testuser",
            "https://github.com/user/repo/issues/123",
        )
    ]
    prs = [
        PRInfo(
            456,
            "Feature PR",
            "OPEN",
            "feature/test",
            "main",
            False,
            "https://github.com/user/repo/pull/456",
        )
    ]
    branches = [
        BranchInfo(
            "feature/test",
            "def5678",
            2,
            1,
            "2025-01-16 14:20:00 +0000",
            True,
            "/home/user/worktrees/feature/test",
        )
    ]
    worktrees = [
        WorktreeInfo(
            "/home/user/dotfiles",
            "main",
            "abc1234",
            False,
            "main",
        ),
        WorktreeInfo(
            "/home/user/dotfiles/worktrees/feature/test",
            "feature/test",
            "def5678",
            True,
            "feature",
        ),
    ]

    report = checker._format_text_report(issues, prs, branches, worktrees)

    assert "🔍 DOTFILES PROJECT STATUS" in report
    assert "📋 OPEN ISSUES (1)" in report
    assert "#123: Bug Report" in report
    assert "[bug, priority]" in report
    assert "(@testuser)" in report
    assert "🔀 OPEN PULL REQUESTS (1)" in report
    assert "#456: Feature PR" in report
    assert "(feature/test → main)" in report
    assert "🌳 ACTIVE WORKTREES (1)" in report
    assert "FEATURE:" in report
    assert "*modified*" in report
    assert "🌿 ACTIVE BRANCHES (1)" in report
    assert "feature/test @ def5678" in report
    assert "[+2, -1, worktree]" in report
    assert "📊 SUMMARY" in report
    assert "⚠️  1 worktrees with uncommitted changes" in report


def test_format_text_report_empty_data(real_logging_helpers, output):
    """_format_text_report() should handle empty data gracefully."""
    checker = ProjectStatusChecker()

    report = checker._format_text_report([], [], [], [])

    assert "🔍 DOTFILES PROJECT STATUS" in report
    assert "No open issues" in report
    assert "No open pull requests" in report
    assert "No active worktrees" in report
    assert "No active branches" in report
    assert "📊 SUMMARY" in report
    assert "0 open issues" in report


def test_format_text_report_draft_pr(real_logging_helpers, output):
    """_format_text_report() should indicate draft PRs."""
    checker = ProjectStatusChecker()

    prs = [
        PRInfo(
            789,
            "Draft PR",
            "OPEN",
            "feature/draft",
            "main",
            True,
            "https://github.com/user/repo/pull/789",
        )
    ]

    report = checker._format_text_report([], prs, [], [])

    assert "#789: Draft PR" in report
    assert "[DRAFT]" in report


# ==============================================================================
# _format_json_report() Tests
# ==============================================================================


def test_format_json_report(real_logging_helpers, output):
    """_format_json_report() should format valid JSON."""
    checker = ProjectStatusChecker()

    issues = [
        IssueInfo(123, "Test", "OPEN", ["bug"], "user", "https://example.com/123")
    ]
    prs = [PRInfo(456, "PR", "OPEN", "feature", "main", False, "https://example.com")]
    branches = [
        BranchInfo("feature", "abc123", 1, 0, "2025-01-01", True, "/path/to/wt")
    ]
    worktrees = [WorktreeInfo("/path", "branch", "commit", False, "main")]

    json_str = checker._format_json_report(issues, prs, branches, worktrees)
    data = json.loads(json_str)

    assert "issues" in data
    assert "pull_requests" in data
    assert "branches" in data
    assert "worktrees" in data
    assert len(data["issues"]) == 1
    assert data["issues"][0]["number"] == 123
    assert data["pull_requests"][0]["draft"] is False
    assert data["branches"][0]["ahead"] == 1
    assert data["worktrees"][0]["type_category"] == "main"


def test_format_json_report_empty(real_logging_helpers, output):
    """_format_json_report() should handle empty data."""
    checker = ProjectStatusChecker()

    json_str = checker._format_json_report([], [], [], [])
    data = json.loads(json_str)

    assert data["issues"] == []
    assert data["pull_requests"] == []
    assert data["branches"] == []
    assert data["worktrees"] == []
