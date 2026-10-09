# Implementation Plan: Issue #77

**Clean up existing ruff violations**

## Issue Summary

`ruff check .` fails on main, so the `ruff-check` pre-commit hook (which runs
on changed files only) fails on any commit touching an affected file.

## Current State Analysis

- Measured with `uvx ruff check . --statistics` (ruff 0.16.10): **78**
  violations, **51** auto-fixable. (The issue text said ~84 / ~55; this plan
  has the measured numbers.)
- The repository has **no ruff configuration** (no `[tool.ruff]` in
  `pyproject.toml`, no `ruff.toml`) and does not pin ruff, so the rule set is
  whatever the installed ruff version enables by default. A newer ruff can
  therefore add new violations without any code change. **Decided (issue
  comment): keep ruff's defaults and do not pin; the risk of new failures with
  newer versions is accepted.**
- Breakdown:

| Rule                               | Count | Fix                                              |
| ---------------------------------- | ----- | ------------------------------------------------ |
| `UP006` `List`/`Dict` -> builtins  | 35    | auto                                             |
| `BLE001` blind `except Exception`  | 17    | decide                                           |
| `I001` unsorted imports            | 9     | auto                                             |
| `SIM117` nested `with`             | 4     | auto                                             |
| `DTZ005` `datetime.now()` no tz    | 3     | manual (tests only)                              |
| `UP035` deprecated `typing` import | 2     | auto (with UP006)                                |
| `UP045` `Optional[X]`              | 2     | auto                                             |
| `TRY002` bare `Exception` raised   | 2     | manual (tests only)                              |
| `B008` call in default arg         | 1     | manual (`logging_config.py:21`)                  |
| `EXE001` shebang not executable    | 1     | `chmod +x` or drop shebang (`project_status.py`) |
| `RET501` `return None`             | 1     | auto                                             |
| `B018` useless expression          | 1     | manual (`tests/test_init.py:58`)                 |

- By file: `project_status.py` 42, `swman.py` 9, `tests/test_init.py` 6,
  `pkgstatus.py` 6, `tests/test_project_status.py` 5, the rest 1-2 each.
- `BLE001` sites: `swman.py` x9, `pkgstatus.py` x6, `project_status.py` x1,
  `status_cache.py` x1. `init.py` already marks its deliberate top-level
  catch with `# noqa: BLE001`, which is the precedent.

## Implementation Approach

Decisions from the issue comment are folded in (see "Decisions" below).

1. **Auto-fixes, one commit:** `uvx ruff check --fix .` then
   `ruff format .`; review the diff (annotation-only changes in
   `project_status.py`, import order elsewhere). `make test-unit` and pyright
   must still pass. No config or version pin is added.
2. **Manual fixes, one commit:**
   - `B008` `logging_config.py:21`: move the call out of the default.
   - Tests: `B018` (assign or delete the expression), `TRY002` (use a custom
     exception class or `RuntimeError`), `DTZ005` (`datetime.now(tz=UTC)`).
   - `EXE001`: remove the shebang from `project_status.py`.
3. **BLE001, one commit, decided per site by reading the context.** None of
   the 17 flagged sites re-raises (ruff already exempts catch-and-re-raise),
   so there is no "log and re-raise" case to mark. Proposed classification,
   to be confirmed against the surrounding code while implementing:

   | Site                                          | What the handler does                                                | Proposed                                                                                        |
   | --------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
   | `swman.py` 228, 336, 487, 572, 650, 732       | per-manager `update()`: log, return `UpdateResult(FAILED)`           | keep, `# noqa: BLE001  # one failing manager must not abort the others`                         |
   | `swman.py` 777, 798, 820 (orchestrator loops) | log, record `(False, 0)` / FAILED result                             | keep, same reason; 820 does **not** log, so add `logger.log_exception`                          |
   | `pkgstatus.py` 173, 275, 497                  | cache refresh / status probes: log and fall back to a degraded value | keep with `noqa` and reason                                                                     |
   | `pkgstatus.py` 84 (read fish config)          | log, return default                                                  | narrow to the errors the read can raise (`OSError`) if the body allows                          |
   | `pkgstatus.py` 309                            | parse ISO timestamp                                                  | narrow to `ValueError` / `OSError`                                                              |
   | `pkgstatus.py` 617                            | top-level `main()` catch (same pattern as `init.py`)                 | keep with `noqa` (like `init.py`); coordinate with #76                                          |
   | `project_status.py` 362                       | worktree status via subprocess                                       | narrow to `OSError` / `subprocess.SubprocessError` if that covers what the body calls           |
   | `status_cache.py` 282                         | cache write failed: log, clean temp file                             | narrow to `OSError` / `TypeError` / `ValueError` if that covers the body, else keep with `noqa` |

   Any site where narrowing would change behaviour (an exception that used to
   be swallowed would now propagate) stays as `noqa` with a reason instead.

4. Verify: `uvx ruff check .` and `uvx ruff format --check .` clean; pyright;
   `make test-unit`; `make test-compile`.

## Files to Modify

`src/dotfiles/project_status.py`, `swman.py`,
`pkgstatus.py`, `status_cache.py`, `logging_config.py`,
`output_formatting.py`, `process_helper.py`, and the test files listed above.

## Testing Strategy

`make test-unit`, `make test-compile`, pyright through pre-commit, and
`uvx ruff check .` returning clean. Behaviour must not change except where
narrowing an `except` is deliberately decided.

## Dependencies

- Do before or together with #76 (exit codes): both touch `swman.py`,
  `pkgstatus.py`. Doing #77 first avoids rebase pain.
- Narrowed exceptions in `swman.py` can change failure behaviour; consider
  doing those after #76 so exit codes make failures visible.

## Decisions (from the owner's answers on the issue)

1. **Rule set:** use ruff's defaults. No explicit `select`, no config section.
2. **BLE001:** decide per site from context; sites that only log (and
   re-raise) may be kept with `noqa`. Finding while preparing this plan: no
   site re-raises, all 17 log and degrade; see the table above.
3. **`EXE001`:** remove the shebang from `project_status.py`.
4. **Pinning ruff:** do not pin; accept that newer ruff versions may add
   failures later.

## Open Questions

None open. One note for review: `swman.py:820` swallows an exception without
logging it; the plan adds a `log_exception` call there, which is a small
behaviour addition beyond pure lint cleanup.
