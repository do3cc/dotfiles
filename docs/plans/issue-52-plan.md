# Implementation Plan: Issue #52

**wt tools assume worktree directory structure exists**

## Issue Summary

The fish helpers `wt-new`, `wt-goto`, `wt-remove`, `wt-list` and `wt-clean`
assume `.worktrees/<type>/` already exists. They should create it, or fail
with a clear message.

## Current State Analysis

- The issue says `worktrees/`; the code and `.gitignore` use `.worktrees/`
  (CLAUDE.md's `/evaluate-issues` text still says `worktrees/<type>/`).
- `fish/functions/wt-new.fish`: validates the type with
  `test -d ".worktrees/$type"`. On a fresh clone that fails with
  "Invalid type '...'", which is misleading, and nothing ever creates the
  directories (`dotfiles-init` does not either).
- `wt-goto` and `wt-remove` use `find .worktrees -name "*$target*"`
  (relative to the current directory, first match wins); `wt-list` uses
  `test -d .worktrees`. They work only from the repository root. `wt-root`
  already knows how to find the root
  (`git rev-parse --git-common-dir`), but the others do not use it.
- `wt-list` handles a missing `.worktrees` ("No .worktrees directory
  found"); `wt-clean` only prunes and prints (`grep -v "main"` is crude).
- No automated tests for the fish functions.

## Implementation Approach

1. Define the valid types once: `review feature bugfix experimental`.
2. `wt-new`: check the type against that list (clear "Invalid type" message
   only for a real invalid type), then `mkdir -p .worktrees/$type` before
   `git worktree add`.
3. Add a private helper (for example `fish/functions/_wt_root.fish`)
   returning the main worktree root, and use it in `wt-new`, `wt-goto`,
   `wt-remove` and `wt-list`, so they work from inside a worktree or a
   subdirectory too.
4. `wt-goto` / `wt-remove` / `wt-clean`: when `.worktrees` is missing, say so
   ("no worktrees yet; create one with wt-new") instead of a failing `find`.
5. Update CLAUDE.md (`worktrees/<type>/` -> `.worktrees/<type>/`).

## Files to Modify

`fish/functions/wt-new.fish`, `wt-goto.fish`, `wt-remove.fish`,
`wt-list.fish`, `wt-clean.fish`, new `_wt_root.fish`, `CLAUDE.md`.

## Testing Strategy

No fish test harness exists. Proposed: a pytest module that runs
`fish -c` in a temporary git repository (skipped when fish is missing)
covering: `wt-new` on a repo without `.worktrees`, invalid type, `wt-goto`
and `wt-remove` from a subdirectory, behaviour with no `.worktrees`.
`fish_indent` and the pre-commit hook on the changed files (install `fish`
first in cloud sessions).

## Dependencies

None. #30 (worktree maintenance) was closed.

## Decisions (from the owner)

1. **Types:** fixed list `review feature bugfix experimental`; the directory is created on first use.
2. **Run from anywhere:** yes, all `wt-*` functions resolve the main worktree root.
3. **Tests:** yes, pytest runs the fish functions in a temporary git repo (skipped when fish is missing).

## Open Questions

None open.
