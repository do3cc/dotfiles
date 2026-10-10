"""Tests for git/config and the SSH signing setup in dotfiles-init."""

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dotfiles import init

REPO = Path(__file__).parent.parent
KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItestkey"


def git_config() -> dict[str, str]:
    result = subprocess.run(
        ["git", "config", "--file", str(REPO / "git" / "config"), "--list"],
        capture_output=True,
        text=True,
        check=True,
    )
    return dict(line.split("=", 1) for line in result.stdout.splitlines())


pytestmark_git = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


@pytestmark_git
@pytest.mark.parametrize(
    "key",
    [
        "core.editor",
        "core.excludesfile",
        "color.ui",
        "color.branch",
        "diff.renames",
        "push.default",
        "alias.lt",
        "alias.llt",
        "alias.lm",
        "alias.llm",
    ],
)
def test_obsolete_settings_are_gone(key):
    assert key not in git_config()


@pytestmark_git
@pytest.mark.parametrize(
    "key,value",
    [
        ("core.whitespace", "space-before-tab,trailing-space"),
        ("merge.tool", "nvimdiff"),
        ("diff.tool", "nvimdiff"),
        ("commit.template", "~/.config/git/message.txt"),
        ("commit.verbose", "true"),
        ("branch.sort", "-committerdate"),
        ("tag.sort", "version:refname"),
        ("rebase.updateRefs", "true"),
        ("push.followTags", "true"),
        ("push.useForceIfIncludes", "true"),
        ("alias.pushf", "push --force-with-lease"),
        ("transfer.fsckObjects", "true"),
        ("help.autocorrect", "prompt"),
        ("gpg.format", "ssh"),
        ("commit.gpgsign", "true"),
        ("tag.gpgsign", "true"),
        ("user.signingkey", "~/.ssh/id_ed25519.pub"),
        ("gpg.ssh.allowedsignersfile", "~/.ssh/allowed_signers"),
    ],
)
def test_expected_settings(key, value):
    # `git config --list` prints variable names in lower case
    assert git_config()[key.lower()] == value


def test_editor_is_set_in_fish_config():
    assert "set -gx EDITOR nvim" in (REPO / "fish" / "config.fish").read_text()


@pytest.mark.parametrize(
    "stdout,expected",
    [
        ("", (False, False)),
        ("laptop\tssh-ed25519 OTHER\tauthentication\n", (False, False)),
        ("laptop\tssh-ed25519 BLOB\tauthentication\n", (True, False)),
        ("laptop signing\tssh-ed25519 BLOB\tsigning\n", (False, True)),
        (
            "a\tssh-ed25519 BLOB\tauthentication\nb signing\tssh-ed25519 BLOB\tsigning\n",
            (True, True),
        ),
    ],
)
def test_parse_ssh_key_list(stdout, expected):
    assert init.parse_ssh_key_list(stdout, "BLOB") == expected


def test_write_allowed_signers_is_idempotent_and_keeps_existing(tmp_path):
    path = tmp_path / ".ssh" / "allowed_signers"
    path.parent.mkdir()
    path.write_text('other@example.com namespaces="git" ssh-ed25519 OLD\n')

    assert init.write_allowed_signers(path, "me@example.com", [KEY, "", KEY])
    assert not init.write_allowed_signers(path, "me@example.com", [KEY])

    assert path.read_text().splitlines() == [
        'other@example.com namespaces="git" ssh-ed25519 OLD',
        f'me@example.com namespaces="git" {KEY}',
    ]


def _arch(tmp_path):
    arch = init.Arch(no_remote_mode=False, homedir=tmp_path)
    (tmp_path / ".ssh").mkdir()
    pub = tmp_path / ".ssh" / "id_ed25519.pub"
    pub.write_text(f"{KEY} laptop\n")
    return arch, pub


def _runner(calls, api_keys="ssh-ed25519 OTHERMACHINE\n", api_fails=False):
    def run(command, logger, output, description="", **kwargs):
        calls.append(command)
        if command[:3] == ["git", "config", "--get"]:
            return MagicMock(stdout="me@example.com\n")
        if command[:2] == ["/usr/bin/gh", "api"]:
            if api_fails:
                raise subprocess.CalledProcessError(1, command)
            return MagicMock(stdout=api_keys)
        return MagicMock(stdout="")

    return run


def test_setup_ssh_signing_registers_missing_key(tmp_path, monkeypatch):
    arch, pub = _arch(tmp_path)
    calls = []
    interactive = []
    monkeypatch.setattr(init, "run_command_with_error_handling", _runner(calls))
    monkeypatch.setattr(
        init,
        "run_interactive_command",
        lambda command, *a, **k: interactive.append(command),
    )

    arch.setup_ssh_signing(MagicMock(), MagicMock(), pub, registered=False)

    assert any("admin:ssh_signing_key" in c for c in interactive)
    add = next(c for c in calls if c[:3] == ["/usr/bin/gh", "ssh-key", "add"])
    assert add[add.index("--type") + 1] == "signing"
    lines = (tmp_path / ".ssh" / "allowed_signers").read_text().splitlines()
    assert f'me@example.com namespaces="git" {KEY}' in lines
    assert 'me@example.com namespaces="git" ssh-ed25519 OTHERMACHINE' in lines


def test_setup_ssh_signing_skips_upload_when_registered(tmp_path, monkeypatch):
    arch, pub = _arch(tmp_path)
    calls = []
    interactive = []
    monkeypatch.setattr(init, "run_command_with_error_handling", _runner(calls))
    monkeypatch.setattr(
        init,
        "run_interactive_command",
        lambda command, *a, **k: interactive.append(command),
    )

    arch.setup_ssh_signing(MagicMock(), MagicMock(), pub, registered=True)

    assert interactive == []
    assert not any(c[:3] == ["/usr/bin/gh", "ssh-key", "add"] for c in calls)


def test_setup_ssh_signing_survives_github_api_failure(tmp_path, monkeypatch):
    arch, pub = _arch(tmp_path)
    monkeypatch.setattr(
        init, "run_command_with_error_handling", _runner([], api_fails=True)
    )
    arch.setup_ssh_signing(MagicMock(), MagicMock(), pub, registered=True)
    text = (tmp_path / ".ssh" / "allowed_signers").read_text()
    assert KEY in text


def _git(cwd, *args, env=None, check=True):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=check, env=env
    )


@pytestmark_git
def test_pushf_refuses_to_overwrite_commits_fetched_in_the_background(tmp_path):
    """--force-with-lease alone is fooled by a background fetch; the alias must not be."""
    import os

    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": str(REPO / "git" / "config"),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    ident = [
        "-c",
        "user.email=t@example.com",
        "-c",
        "user.name=t",
        "-c",
        "commit.gpgsign=false",
    ]
    _git(tmp_path, "init", "-q", "--bare", "remote.git", env=env)
    for name in ("a", "b"):
        _git(tmp_path, "clone", "-q", "remote.git", name, env=env, check=False)
    a, b = tmp_path / "a", tmp_path / "b"

    _git(a, "checkout", "-q", "-b", "feat", env=env)
    (a / "f").write_text("1")
    _git(a, "add", "f", env=env)
    _git(a, *ident, "commit", "-q", "-m", "one", env=env)
    _git(a, "push", "-q", "-u", "origin", "feat", env=env)
    _git(b, "fetch", "-q", env=env)
    _git(b, "checkout", "-q", "feat", env=env)

    # a pushes a new commit; b fetches it (as an IDE would) without integrating it
    (a / "f").write_text("2")
    _git(a, *ident, "commit", "-q", "-am", "two", env=env)
    _git(a, "push", "-q", "origin", "feat", env=env)
    _git(b, "fetch", "-q", env=env)

    (b / "g").write_text("3")
    _git(b, "add", "g", env=env)
    _git(b, *ident, "commit", "-q", "--amend", "-m", "rewrite", env=env)

    result = _git(b, *ident, "pushf", env=env, check=False)

    assert result.returncode != 0
    remote_tip = _git(
        tmp_path / "remote.git", "log", "-1", "--format=%s", "feat"
    ).stdout
    assert remote_tip.strip() == "two"
