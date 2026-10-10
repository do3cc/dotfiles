"""The fish wt-* worktree helpers, run by real fish in a temporary git repository (#52)."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
FUNCTIONS = REPO / "fish" / "functions"

pytestmark = pytest.mark.skipif(
    shutil.which("fish") is None or shutil.which("git") is None,
    reason="needs fish and git",
)


@pytest.fixture
def repo(tmp_path):
    """A git repository with one commit; returns its (resolved) path."""
    root = (tmp_path / "project").resolve()
    root.mkdir()
    env = _env(tmp_path)
    for command in (
        ["git", "init", "-q", "-b", "main"],
        ["git", "commit", "-q", "--allow-empty", "-m", "initial"],
    ):
        subprocess.run(command, cwd=root, env=env, check=True, capture_output=True)
    return root


def _env(tmp_path):
    return {
        **os.environ,
        "HOME": str(tmp_path),
        "GIT_CONFIG_GLOBAL": str(tmp_path / "gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }


def fish(cwd, script):
    """Run a fish script with the repo's functions autoloadable; returns the result."""
    prelude = f"set fish_function_path {FUNCTIONS} $fish_function_path; "
    return subprocess.run(
        ["fish", "--no-config", "-c", prelude + script],
        cwd=cwd,
        env=_env(cwd.parent if cwd.name == "project" else cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def test_wt_new_creates_the_type_directory_and_the_worktree(repo):
    assert not (repo / ".worktrees").exists()

    result = fish(repo, "wt-new feature issue-1; and pwd")

    assert result.returncode == 0, result.stdout + result.stderr
    worktree = repo / ".worktrees" / "feature" / "issue-1"
    assert worktree.is_dir()
    assert result.stdout.strip().splitlines()[-1] == str(worktree)  # it cd'd there
    branches = subprocess.run(
        ["git", "branch", "--list", "issue-1"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "issue-1" in branches


def test_wt_new_rejects_an_unknown_type_without_creating_anything(repo):
    result = fish(repo, "wt-new featur issue-1")

    assert result.returncode == 1
    assert "Invalid type 'featur'" in result.stdout
    assert not (repo / ".worktrees").exists()


def test_wt_new_without_arguments_prints_usage(repo):
    result = fish(repo, "wt-new")
    assert result.returncode == 1
    assert "Usage: wt-new" in result.stdout


def test_wt_new_outside_a_repository_fails_clearly(tmp_path):
    outside = tmp_path / "plain"
    outside.mkdir()
    result = fish(outside, "wt-new feature x")
    assert result.returncode == 1
    assert "Not in a git repository" in result.stdout


def test_wt_new_from_a_subdirectory_uses_the_repository_root(repo):
    sub = repo / "some" / "dir"
    sub.mkdir(parents=True)

    result = fish(sub, "wt-new bugfix fix-1")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees" / "bugfix" / "fix-1").is_dir()
    assert not (sub / ".worktrees").exists()


def test_wt_new_from_inside_a_worktree_uses_the_main_repository_root(repo):
    fish(repo, "wt-new feature first")
    first = repo / ".worktrees" / "feature" / "first"

    result = fish(first, "wt-new review second")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees" / "review" / "second").is_dir()
    assert not (first / ".worktrees").exists()


def test_wt_goto_finds_a_worktree_from_a_subdirectory(repo):
    fish(repo, "wt-new feature issue-25-logging")
    sub = repo / "a"
    sub.mkdir()

    result = fish(sub, "wt-goto issue-25; and pwd")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip().splitlines()[-1] == str(
        repo / ".worktrees" / "feature" / "issue-25-logging"
    )


@pytest.mark.parametrize("command", ["wt-goto x", "wt-remove x"])
def test_wt_goto_and_remove_without_any_worktrees_say_so(repo, command):
    result = fish(repo, command)
    assert result.returncode == 1
    assert "No worktrees yet" in result.stdout


def test_wt_remove_removes_a_clean_worktree_from_a_subdirectory(repo):
    fish(repo, "wt-new feature gone")
    sub = repo / "a"
    sub.mkdir()

    result = fish(sub, "wt-remove gone")

    assert result.returncode == 0, result.stdout + result.stderr
    assert not (repo / ".worktrees" / "feature" / "gone").exists()


def test_wt_remove_refuses_a_worktree_with_uncommitted_changes(repo):
    fish(repo, "wt-new feature dirty")
    worktree = repo / ".worktrees" / "feature" / "dirty"
    (worktree / "new.txt").write_text("work in progress")

    result = fish(repo, "wt-remove dirty")

    assert result.returncode == 1
    assert "uncommitted changes" in result.stdout
    assert worktree.exists()


def test_wt_list_without_worktrees_does_not_fail(repo):
    result = fish(repo, "wt-list")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "No .worktrees directory found" in result.stdout


def test_wt_clean_lists_all_but_the_main_worktree(repo):
    # a branch name containing "main" used to be hidden by `grep -v main`
    fish(repo, "wt-new feature maintenance-work")

    result = fish(repo, "wt-clean")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "maintenance-work" in result.stdout
    listed = [line for line in result.stdout.splitlines() if line.startswith(str(repo))]
    assert all("/.worktrees/" in line for line in listed)
