"""Tests for project_status.py - Project status checker dataclasses."""

from dotfiles.project_status import IssueInfo, PRInfo, BranchInfo, WorktreeInfo


# ==============================================================================
# IssueInfo Dataclass Tests
# ==============================================================================


# TODO: REVIEW
def test_issue_info_initialization():
    """IssueInfo should store GitHub issue information."""
    issue = IssueInfo(
        number=42,
        title="Add new feature",
        state="open",
        labels=["enhancement", "help wanted"],
        assignee="alice",
        url="https://github.com/user/repo/issues/42",
    )

    assert issue.number == 42
    assert issue.title == "Add new feature"
    assert issue.state == "open"
    assert issue.labels == ["enhancement", "help wanted"]
    assert issue.assignee == "alice"
    assert issue.url == "https://github.com/user/repo/issues/42"


# TODO: REVIEW
def test_issue_info_with_no_assignee():
    """IssueInfo should handle None assignee."""
    issue = IssueInfo(
        number=10,
        title="Bug report",
        state="open",
        labels=["bug"],
        assignee=None,
        url="https://github.com/user/repo/issues/10",
    )

    assert issue.assignee is None


# TODO: REVIEW
def test_issue_info_with_empty_labels():
    """IssueInfo should handle empty labels list."""
    issue = IssueInfo(
        number=5,
        title="Question",
        state="open",
        labels=[],
        assignee=None,
        url="https://github.com/user/repo/issues/5",
    )

    assert issue.labels == []


# TODO: REVIEW
def test_issue_info_with_multiple_labels():
    """IssueInfo should handle multiple labels."""
    labels = ["bug", "critical", "needs-triage", "regression"]
    issue = IssueInfo(
        number=99,
        title="Critical bug",
        state="open",
        labels=labels,
        assignee="bob",
        url="https://github.com/user/repo/issues/99",
    )

    assert len(issue.labels) == 4
    assert "critical" in issue.labels


# TODO: REVIEW
def test_issue_info_with_closed_state():
    """IssueInfo should handle closed state."""
    issue = IssueInfo(
        number=1,
        title="Old issue",
        state="closed",
        labels=[],
        assignee=None,
        url="https://github.com/user/repo/issues/1",
    )

    assert issue.state == "closed"


# ==============================================================================
# PRInfo Dataclass Tests
# ==============================================================================


# TODO: REVIEW
def test_pr_info_initialization():
    """PRInfo should store GitHub pull request information."""
    pr = PRInfo(
        number=123,
        title="Feature: Add authentication",
        state="open",
        branch="feature/auth",
        base="main",
        draft=False,
        url="https://github.com/user/repo/pull/123",
    )

    assert pr.number == 123
    assert pr.title == "Feature: Add authentication"
    assert pr.state == "open"
    assert pr.branch == "feature/auth"
    assert pr.base == "main"
    assert pr.draft is False
    assert pr.url == "https://github.com/user/repo/pull/123"


# TODO: REVIEW
def test_pr_info_with_draft_status():
    """PRInfo should handle draft status."""
    pr = PRInfo(
        number=50,
        title="WIP: Experimental feature",
        state="open",
        branch="experimental",
        base="develop",
        draft=True,
        url="https://github.com/user/repo/pull/50",
    )

    assert pr.draft is True


# TODO: REVIEW
def test_pr_info_with_closed_state():
    """PRInfo should handle closed/merged state."""
    pr = PRInfo(
        number=10,
        title="Fix bug",
        state="merged",
        branch="fix/bug-123",
        base="main",
        draft=False,
        url="https://github.com/user/repo/pull/10",
    )

    assert pr.state == "merged"


# TODO: REVIEW
def test_pr_info_with_different_base_branches():
    """PRInfo should handle different base branches."""
    pr_main = PRInfo(
        number=1,
        title="PR to main",
        state="open",
        branch="f1",
        base="main",
        draft=False,
        url="",
    )
    pr_dev = PRInfo(
        number=2,
        title="PR to develop",
        state="open",
        branch="f2",
        base="develop",
        draft=False,
        url="",
    )

    assert pr_main.base == "main"
    assert pr_dev.base == "develop"


# ==============================================================================
# BranchInfo Dataclass Tests
# ==============================================================================


# TODO: REVIEW
def test_branch_info_initialization():
    """BranchInfo should store git branch information."""
    branch = BranchInfo(
        name="feature/new-feature",
        commit="abc123",
        ahead=3,
        behind=1,
        last_commit_date="2025-10-09",
        has_worktree=True,
        worktree_path="/home/user/project/worktrees/feature/new-feature",
    )

    assert branch.name == "feature/new-feature"
    assert branch.commit == "abc123"
    assert branch.ahead == 3
    assert branch.behind == 1
    assert branch.last_commit_date == "2025-10-09"
    assert branch.has_worktree is True
    assert branch.worktree_path == "/home/user/project/worktrees/feature/new-feature"


# TODO: REVIEW
def test_branch_info_without_worktree():
    """BranchInfo should handle branches without worktrees."""
    branch = BranchInfo(
        name="main",
        commit="def456",
        ahead=0,
        behind=0,
        last_commit_date="2025-10-08",
        has_worktree=False,
        worktree_path=None,
    )

    assert branch.has_worktree is False
    assert branch.worktree_path is None


# TODO: REVIEW
def test_branch_info_up_to_date():
    """BranchInfo should handle branches that are up to date."""
    branch = BranchInfo(
        name="main",
        commit="xyz789",
        ahead=0,
        behind=0,
        last_commit_date="2025-10-09",
        has_worktree=False,
        worktree_path=None,
    )

    assert branch.ahead == 0
    assert branch.behind == 0


# TODO: REVIEW
def test_branch_info_ahead_of_remote():
    """BranchInfo should handle branches ahead of remote."""
    branch = BranchInfo(
        name="feature/test",
        commit="aaa111",
        ahead=5,
        behind=0,
        last_commit_date="2025-10-09",
        has_worktree=False,
        worktree_path=None,
    )

    assert branch.ahead == 5
    assert branch.behind == 0


# TODO: REVIEW
def test_branch_info_behind_remote():
    """BranchInfo should handle branches behind remote."""
    branch = BranchInfo(
        name="feature/old",
        commit="bbb222",
        ahead=0,
        behind=10,
        last_commit_date="2025-09-01",
        has_worktree=False,
        worktree_path=None,
    )

    assert branch.ahead == 0
    assert branch.behind == 10


# TODO: REVIEW
def test_branch_info_diverged():
    """BranchInfo should handle diverged branches."""
    branch = BranchInfo(
        name="feature/diverged",
        commit="ccc333",
        ahead=2,
        behind=3,
        last_commit_date="2025-10-05",
        has_worktree=False,
        worktree_path=None,
    )

    assert branch.ahead == 2
    assert branch.behind == 3


# ==============================================================================
# WorktreeInfo Dataclass Tests
# ==============================================================================


# TODO: REVIEW
def test_worktree_info_initialization():
    """WorktreeInfo should store git worktree information."""
    worktree = WorktreeInfo(
        path="/home/user/project/worktrees/feature/issue-53",
        branch="issue-53-plan",
        commit="abc123",
        has_uncommitted=True,
        type_category="feature",
    )

    assert worktree.path == "/home/user/project/worktrees/feature/issue-53"
    assert worktree.branch == "issue-53-plan"
    assert worktree.commit == "abc123"
    assert worktree.has_uncommitted is True
    assert worktree.type_category == "feature"


# TODO: REVIEW
def test_worktree_info_without_uncommitted_changes():
    """WorktreeInfo should handle clean worktrees."""
    worktree = WorktreeInfo(
        path="/home/user/project/worktrees/review/pr-10",
        branch="review-pr-10",
        commit="def456",
        has_uncommitted=False,
        type_category="review",
    )

    assert worktree.has_uncommitted is False


# TODO: REVIEW
def test_worktree_info_type_categories():
    """WorktreeInfo should handle different type categories."""
    feature = WorktreeInfo(
        path="/path/feature",
        branch="f1",
        commit="a1",
        has_uncommitted=False,
        type_category="feature",
    )
    review = WorktreeInfo(
        path="/path/review",
        branch="r1",
        commit="a2",
        has_uncommitted=False,
        type_category="review",
    )
    bugfix = WorktreeInfo(
        path="/path/bugfix",
        branch="b1",
        commit="a3",
        has_uncommitted=False,
        type_category="bugfix",
    )
    experimental = WorktreeInfo(
        path="/path/exp",
        branch="e1",
        commit="a4",
        has_uncommitted=False,
        type_category="experimental",
    )

    assert feature.type_category == "feature"
    assert review.type_category == "review"
    assert bugfix.type_category == "bugfix"
    assert experimental.type_category == "experimental"


# TODO: REVIEW
def test_worktree_info_with_uncommitted_changes():
    """WorktreeInfo should handle worktrees with uncommitted changes."""
    worktree = WorktreeInfo(
        path="/project/worktrees/bugfix/fix-123",
        branch="fix-123",
        commit="xyz789",
        has_uncommitted=True,
        type_category="bugfix",
    )

    assert worktree.has_uncommitted is True
