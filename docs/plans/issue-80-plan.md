# Implementation Plan: Issue #80

**swman: orchestrator error handling swallows or mislabels exceptions**

## Issue Summary

In `SoftwareManagerOrchestrator`, `update_all()` swallows exceptions without
logging, and two other handlers log human-readable messages instead of
snake_case events.

## Current State Analysis

- `update_all()` (~line 810) is not called anywhere. `main()` handles
  `--all` by selecting all three manager types and calling
  `update_by_type()`. The method duplicates that logic.
- `check_all()` logs `"Error checking for updates"`; `update_by_type()` logs
  `"Unexpected exception"`. CLAUDE.md requires snake_case events; the
  per-manager handlers already use `unexpected_exception`, and
  `update_check_failed` is in the standard event list.
- `tests/test_swman.py` has no tests for the orchestrator's error paths.
- Same handlers are flagged by ruff `BLE001` in #77 (decided there: keep with
  `noqa` and a reason).

## Implementation Approach

1. Delete `update_all()` (proposed; it is dead and redundant).
2. `check_all()`: log `update_check_failed`; `update_by_type()`: log
   `unexpected_exception`.
3. Tests: a manager that raises in `check_all` yields `(False, 0)` and calls
   `log_exception` with `update_check_failed`; a manager that raises in
   `update_by_type` yields a FAILED `UpdateResult` and calls `log_exception`
   with `unexpected_exception`; other managers still run.

## Files to Modify

`src/dotfiles/swman.py`, `tests/test_swman.py`.

## Testing Strategy

`make test-unit`, `make test-compile`, pre-commit on the changed files. No
behaviour change for users.

## Dependencies

Same file as #77, #76, #33; do #77 first so the `noqa` comments land once.

## Decisions (from the owner)

1. **`update_all()`:** delete it (unused and redundant).
2. **Event names:** `update_check_failed` for `check_all`, `unexpected_exception` for `update_by_type`.

## Open Questions

None open.
