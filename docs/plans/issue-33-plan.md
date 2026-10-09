# Implementation Plan: Issue #33

**Add dry-run option to swman for preview of package updates**

## Issue Summary

`dotfiles-swman --dry-run` should show which packages would change
(`name: old -> new`) and per-manager totals, instead of only
"Would update N packages".

## Current State Analysis

- `--dry-run` already exists (`swman.py` `main`, passed to
  `update_by_type`). In dry-run, `PacmanManager.update` calls
  `check_updates()` and returns `UpdateResult(message="Would update N
packages")`. `UvToolsManager`, `LazyNvimManager` and `FisherManager` return
  a fixed string ("Would upgrade all uv tools", ...). Output goes through
  `print_results_summary` (a table of status, manager, message, duration).
- `check_updates()` returns only `(has_updates, count)`. The raw command
  output already contains what is needed:
  - pacman: `checkupdates` prints `name old -> new` per line.
  - yay: `yay -Qu` prints the same format (repo and AUR).
  - Debian/Ubuntu: `apt list --upgradable` (after `sudo apt update`).
  - uv tools: the code says "uv has no outdated command" and returns
    `(False, -1)`. That is stale: `uv tool list --outdated` exists in uv
    0.11 (checked locally).
  - lazy.nvim and fisher: no read-only check; stay "cannot determine".
- The issue text mentions `--apply`; no such flag exists (updates run when
  `--dry-run` is absent). Drop that line from the intended output.
- `--system/--tools/--plugins/--all` filters already select managers, so the
  preview inherits them.

## Implementation Approach

1. Add a small dataclass `PackageUpdate(name, old, new)` and a method
   `PackageManager.list_updates(logger, output) -> list[PackageUpdate] | None`
   (`None` = cannot determine). Default implementation returns `None`.
2. Implement it for pacman, yay, apt and uv tools; parse the command output
   once and make `check_updates()` derive its count from `list_updates()` so
   the command runs once.
3. Extend `UpdateResult` with an optional `updates: list[PackageUpdate]`
   field. In dry-run, managers fill it and the message becomes
   "Would update N packages".
4. Rendering: add `print_update_preview(results, output)` producing the
   layout from the issue (per manager heading, one line per package, total,
   and a final "Would update X packages across Y managers"). Managers that
   cannot determine print "preview not available". JSON output (`--json`)
   includes the package list.
5. Keep non-dry-run behaviour unchanged.

## Files to Modify

`src/dotfiles/swman.py` (and tests). README/CLAUDE.md swman section: show the
new output.

## Testing Strategy

- Parser unit tests for each manager with fixture output (including odd
  version strings; hypothesis for the `name old -> new` parser).
- Dry-run tests with the command runner mocked: assert no mutating command is
  called, the preview lists the packages, filters are respected, JSON
  contains the list.
- Manual: `uv run dotfiles-swman --all --dry-run` on the Arch machine.

## Dependencies

- Touches `swman.py` like #76 (exit codes), #77 (lint) and #80 (handler
  cleanup). Suggested order: #77, #80, #76, then this.

## Open Questions

1. **apt needs sudo for the check** (`sudo apt update`): acceptable for a
   preview, or use `apt list --upgradable` on the existing cache and say the
   cache may be stale?
2. **`uv tool list --outdated`:** minimum uv version and exact output format
   must be confirmed on the machine; fall back to "cannot determine" on older
   uv?
3. **`--check`:** should it also list packages, or stay count-only?
4. **lazy.nvim / fisher:** just "preview not available", or invest in a
   check (for example `git fetch` + compare for lazy plugins)? Proposed:
   not available.
