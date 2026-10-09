# Implementation Plan: Issue #81

**Modernize git/config: remove obsolete settings, add current defaults, SSH
commit signing**

## Issue Summary

Apply the audit from #63 to `git/config` and add SSH commit signing, wired
into `dotfiles-init`. The settings, with explanations, are in the issue; this
plan covers how to implement and verify them.

## Current State Analysis

- `git/config` (after #79): colour blocks, `core.editor`, `diff.tool = meld`
  (not installed), stale `lt/llt/lm/llm` aliases, hard-coded
  `commit.template`, some defaults set explicitly.
- `dotfiles-init` links `git/` to `~/.config/git/`
  (`config_dirs`), and `setup_ssh_key` (`init.py`, remote mode only) creates
  `~/.ssh/id_ed25519`, enables `AddKeysToAgent`, and uploads the public key
  to GitHub. The `gh` token scope refresh requests `admin:public_key` in two
  places; signing needs `admin:ssh_signing_key`.
- `git/config` sets `user.email = do3cc@patrick-gerken.de`, while the SSH key
  comment uses `ssh_key_email` (`sshkeys@patrick-gerken.de`). The
  `allowed_signers` principal must match the **committer email**, so it has
  to come from git config, not from `ssh_key_email`.
- `EDITOR` is not exported anywhere in `fish/` or `direnv/`.
- #62 (`pushf`, `useForceIfIncludes`) edits the same file.

## Implementation Approach

1. **Config edits** in `git/config`, in the order of the issue: remove
   obsolete settings and colour blocks, fix `commit.template`, remove the
   unused aliases `lt`, `llt`, `lm`, `llm` (decided: never used), set `merge.tool`/`diff.tool = nvimdiff`, add the modern
   settings. Drop `core.editor`.
2. **EDITOR:** if nothing else sets it, add `set -gx EDITOR nvim` (and
   `VISUAL`) to `fish/config.fish`.
3. **Signing config.** Add the `[gpg]`, `[gpg "ssh"]`, `[user] signingKey`,
   `[commit]`/`[tag] gpgSign` block. Safety: unconditional `commit.gpgSign`
   breaks every commit on a machine without the key or agent (for example
   after `dotfiles-init --no-remote`). **Decided:** keep it simple, one
   unconditional block in `git/config`. A machine without the key could not
   push anyway, and `dotfiles-init` creates the key first. The generated
   `allowed_signers` lives in `~/.ssh/` (not under `~/.config/git`, which is a
   symlink into the repo), so nothing generated lands in the working tree.
4. **`dotfiles-init`** (extend `setup_ssh_key`, idempotent like its other
   steps): request `admin:ssh_signing_key` in the `gh auth refresh` calls;
   add the public key as a signing key if `gh ssh-key list` does not show it
   with type signing (verify the column format at implementation time);
   write `~/.config/git/allowed_signers` with
   `<git user.email> namespaces="git" <pubkey>`; write the signing include.
   The principal list should contain the keys of all machines so commits made
   elsewhere verify locally; `gh api users/<login>/ssh_signing_keys` can
   supply them.
5. **Verification** in a scratch repo with a throw-away key:
   `GIT_CONFIG_GLOBAL=<repo>/git/config` (or `-c include.path`), commit,
   `git verify-commit HEAD`, `git log --show-signature`. Check that `~/` is
   expanded in `user.signingKey` and `allowedSignersFile` on the installed
   git; otherwise write absolute paths at init time.

## Files to Modify

`git/config`, `fish/config.fish` (if needed), `src/dotfiles/init.py`,
`README.md` (SSH Keys section), tests.

## Testing Strategy

- Unit: parse `git/config` with `git config --file --list` and assert the
  removed keys are gone and the new keys present; `allowed_signers` writer and
  the signing-key upload logic with the command runner mocked (key already
  uploaded, missing, scope refresh).
- Manual: sign and verify a commit as in step 5; confirm "Verified" on GitHub
  after init on a real machine.
- `make test-unit`, `make test-compile`, pre-commit.

## Dependencies

- #62 touches the same file: merge one, then merge main into the other.
- Needs a real `gh` login for the GitHub part; cannot be tested in a
  container run with `--no-remote`.

## Decisions (from the owner)

1. **Aliases `lt/llt/lm/llm`:** removed, never used.
2. **Custom colour blocks:** dropped, git defaults plus `diff.colorMoved`.
3. **Sign tags** (`tag.gpgSign`): yes.
4. **Optional settings** (`transfer.fsckObjects`, `help.autocorrect = prompt`,
   `rebase.updateRefs`, `push.followTags`): all of them.
5. **Signing block:** unconditional in `git/config` (a machine without the
   key cannot push anyway), `allowed_signers` in `~/.ssh/`.
6. **`tab-in-indent`:** dropped, `core.whitespace = space-before-tab,trailing-space`.
7. SSH signing, `merge.tool`/`diff.tool = nvimdiff`, drop `core.editor`
   (`$EDITOR` is always nvim): decided earlier on the issue.

## Open Questions

None open.
