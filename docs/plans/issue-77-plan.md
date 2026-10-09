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
  therefore add new violations without any code change. The hook runs
  `ruff check --fix` with `language: system`, so developers' versions differ.
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

1. **Config first.** Add a `[tool.ruff]` section to `pyproject.toml` that
   makes the current rule set explicit (`lint.select`), so the result no
   longer depends on the ruff version, and pin ruff in the `dev`/`test`
   dependency group (or the hook's `entry`). Which rules to keep is Open
   Question 1.
2. **Auto-fixes, one commit:** `uvx ruff check --fix .` then
   `ruff format .`; review the diff (annotation-only changes in
   `project_status.py`, import order elsewhere). `make test-unit` and pyright
   must still pass.
3. **Manual fixes, one commit:**
   - `B008` `logging_config.py:21`: move the call out of the default.
   - Tests: `B018` (assign or delete the expression), `TRY002` (use a custom
     exception class or `RuntimeError`), `DTZ005` (`datetime.now(tz=UTC)`).
   - `EXE001`: pick one (see Open Question 3).
4. **BLE001 decisions, one commit:** for each of the 17 sites, either narrow
   the exception (for example `OSError`, `subprocess.SubprocessError`,
   `json.JSONDecodeError`) or keep it with `# noqa: BLE001  # <reason>` where
   the tool must never crash (status checks that fall back to a degraded
   result). Log through `logger.log_exception` in every kept site (already the
   pattern).
5. Verify: `uvx ruff check .` and `uvx ruff format --check .` clean; pyright;
   `make test-unit`; `make test-compile`.

## Files to Modify

`pyproject.toml`, `src/dotfiles/project_status.py`, `swman.py`,
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

## Open Questions

1. **Rule set:** keep everything ruff 0.16 enables by default (current
   behaviour), or choose an explicit smaller set (for example `E,F,I,UP,B`)
   and drop the opinionated ones (`BLE`, `DTZ`, `TRY`)?
2. **BLE001:** narrow all 17 sites, or keep deliberate ones with `noqa` and a
   reason? A tool-specific default ("never crash, log and degrade") would let
   us ignore the rule for `src/dotfiles/{swman,pkgstatus,status_cache}.py`
   via `per-file-ignores` instead of 17 inline comments.
3. **`EXE001`:** make `project_status.py` executable or remove the shebang
   (it runs through the `dotfiles-status` entry point)? Removing is simpler.
4. **Pinning ruff:** pin in the dependency group (and run the hook via
   `uv run ruff`) so everyone, including prek and CI, uses one version?
