# Implementation Plan: Issue #54

**refactor: remove log_package_operation and use bind() for package context**

## Issue Summary

`LoggingHelpers.log_package_operation()` logs a generic `package_operation`
event, which goes against the event-based logging pattern (specific
snake_case events, context attached with `bind()`). Remove it and update the
documentation.

## Current State Analysis

Verified on current main:

- Definition: `src/dotfiles/logging_config.py:184-207`. It emits the event
  `package_operation` with `manager`, `operation`, `package_count`,
  `packages[:10]` and `success`.
- **No callers** in `src/` (confirmed with grep). The code that logs package
  work (`swman.py`, `init.py`) already uses `logger.bind(manager=...)` plus
  specific events (`update_started`, `update_completed`, ...), so the issue's
  "update code that would use this" step has nothing to do.
- Tests: `tests/test_logging_config.py:532-565` has two tests
  (`test_log_package_operation_success` / `_failure`) under the comment
  "will be removed per issue #54".
- Docs: one bullet in `CLAUDE.md:344` ("Enhanced Logging Abstractions").
- Related finding: `log_file_operation()` (`logging_config.py:167`) has the
  same generic-event shape (`file_operation`) and also has **no callers**.
  Not part of this ticket (see Open Questions).
- Related finding: the "Enhanced Logging Examples" in CLAUDE.md import
  module-level `log_progress`, `log_error`, `log_subprocess_result`,
  `log_exception`, `bind_context` from `logging_config`. The module only
  defines `setup_logging` at module level; those are `LoggingHelpers`
  methods. The examples are stale. Also not part of this ticket.

## Implementation Approach

1. Delete `LoggingHelpers.log_package_operation` from `logging_config.py`.
2. Delete the two tests and the "will be removed per issue #54" comment block
   in `tests/test_logging_config.py`.
3. Remove the `log_package_operation()` bullet from `CLAUDE.md`.
4. Optionally add one sentence in the "Context Binding Pattern" section of
   CLAUDE.md saying package-manager work binds `manager=`/`packages=` and uses
   the standard events, which is what the issue's "After" example shows.

## Files to Modify

`src/dotfiles/logging_config.py`, `tests/test_logging_config.py`, `CLAUDE.md`.

## Testing Strategy

- `grep -rn log_package_operation` returns nothing outside git history and
  plan/docs that mention the removal.
- `make test-unit`, `make test-compile`,
  `uvx pre-commit run --files <changed files>` (pyright strict covers
  `logging_config.py`).
- No behaviour change: nothing calls the method, no log consumer queries the
  `package_operation` event (grep of the repo; the owner's `jq` queries are
  outside the repo, see Open Questions).

## Dependencies

None. Touches `CLAUDE.md`, which #78 (cloud-session note) also edits in a
different section; trivial merge.

## Decisions (from the owner)

1. **`log_file_operation()`:** remove it in the same PR too (it is also unused and logs a generic event), with its tests and its CLAUDE.md bullet.
2. **Stale CLAUDE.md logging examples** (module-level imports that do not exist): fix them in this PR.
3. No external queries select `event=="package_operation"`.

## Open Questions

None open.
