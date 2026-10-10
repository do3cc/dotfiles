# Implementation Plan: Issue #62

**Add safer force-push git configuration**

## Issue Summary

Add a `pushf` alias (`push --force-with-lease`) and enable
`push.useForceIfIncludes` in `git/config`, so force-pushes cannot silently
overwrite commits that were never integrated locally.

## Requirements Analysis

1. `[alias] pushf = push --force-with-lease`
2. `[push] useForceIfIncludes = true`

Semantics to rely on (git >= 2.30; installed here: 2.43):

- `--force-with-lease` without an explicit expected value compares the remote
  ref against the remote-tracking ref. If something fetched in the background
  (IDE, `git fetch` in another terminal) updated that tracking ref without the
  commits being integrated locally, plain `--force-with-lease` is fooled.
- `push.useForceIfIncludes = true` makes git add `--force-if-includes`
  implicitly, which additionally requires that the remote-tracking tip is
  reachable from the local branch (via its reflog). It only takes effect
  together with `--force-with-lease` (no explicit value), so the alias and the
  setting belong together.

## Current State Analysis

`git/config` (symlinked to `~/.config/git/config`) has an `[alias]` block
(mixed tabs/spaces, `pp`, `wt*` entries) and a `[push]` block with
`default = simple` and `autoSetupRemote = true`. Neither `pushf` nor
`useForceIfIncludes` exists. Plain `git push --force` is not blocked by any
alias.

## Implementation Approach

1. Add `pushf = push --force-with-lease` to `[alias]`, next to `pp`.
2. Add `useForceIfIncludes = true` to `[push]`.
3. Keep the file's existing indentation (tab) for the new lines; whitespace
   normalisation of the whole file is part of #63, not this ticket.

## Files to Modify

`git/config` only.

## Testing Strategy

In a scratch clone (not the real repo): create two clones of a bare repo,
push a commit from A, fetch it into B without merging, then
`GIT_CONFIG_GLOBAL=<repo>/git/config git pushf` from B after amending its
branch. Expect rejection ("stale info" / "remote ref updated since checkout").
Also check the normal case (amend own commit, nothing new on remote) succeeds.
`GIT_CONFIG_GLOBAL=$PWD/git/config git config --list --show-origin` shows both
keys. `uvx pre-commit run --files git/config`.

## Dependencies

- #63 (git config review) edits the same file. Different sections, so a
  trivial merge; if both are open, merge whichever is ready first and merge
  main into the other.

## Decisions (from the owner)

1. Plain `git push --force` is not discouraged; the plan only adds the safer path.
2. `pushf` is not mentioned in README or CLAUDE.md.

## Open Questions

None open.
