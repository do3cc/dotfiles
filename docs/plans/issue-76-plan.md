# Implementation Plan: Issue #76

**Tools exit 0 on failure: click ignores main()'s return value**

## Issue Summary

Click commands whose `main()` does `return 1` exit 0, because Click's
standalone mode discards the return value and calls `sys.exit(0)` itself.
Failures are invisible to scripts, CI and systemd.

## Current State Analysis

Click-based entry points (`pyproject.toml` `[project.scripts]`):

| Tool                  | Returns non-zero today                                                                                                                                                            |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `init.py` `main`      | `return 1` at 6 places (OS detection x2, step failures, unexpected exception, ...), `return 130` on SIGINT; the new `DOTFILES_ENVIRONMENT` check (#74) already uses `sys.exit(1)` |
| `pkgstatus.py` `main` | `return 1` in the final `except` (line ~626)                                                                                                                                      |
| `swman.py` `main`     | `return 1` for "no operation given", and `return 1 if failed_count > 0 else 0` at the end                                                                                         |

`project_status.py` is **not** affected: it uses `argparse`, only `return 0`
and wraps `sys.exit(main())`. No change needed.

Consumers that would start seeing the real exit code:

- `systemd/pkgstatus-update.service` runs `dotfiles-pkgstatus --refresh`. A
  failing refresh will now mark the unit failed (correct, but visible).
- `test/run_tests.sh` / CI run `dotfiles-init --no-remote` and branch on its
  exit code. Today a failed init can pass CI. After the change, previously
  hidden failures may turn CI red; that is the point, but expect to fix some.
- `fish` helpers or prompts calling `dotfiles-pkgstatus --quiet`: check that
  none treat non-zero as "broken" (grep `fish/` and `local_bin/`).

Existing tests only assert "did not crash" (for example
`assert result.exception is None or isinstance(result.exception, SystemExit)`
in `tests/test_init.py`), which is why this was never caught.

## Implementation Approach

1. Replace `return <code>` with `sys.exit(<code>)` inside the three Click
   `main()` functions (not inside helpers). Keep the exit-code meaning:
   0 ok, 1 failure, 130 SIGINT.
   - `init.py`: all `return 1` / `return 130`; `sys` is already imported.
   - `pkgstatus.py`: the `except` branch; add `import sys` if missing.
   - `swman.py`: the "must specify at least one operation" branch (consider
     `2` for usage errors, the Click convention, or raise `click.UsageError`
     which prints help and exits 2), and the final
     `sys.exit(1 if failed_count > 0 else 0)`.
2. Remove the now-redundant `sys.exit(main())` wrappers only if they exist
   next to Click commands; harmless otherwise.
3. Tests: add `CliRunner` tests asserting `result.exit_code` for each failure
   path that can be triggered with monkeypatching (os-release missing,
   unsupported OS, step failure, unexpected exception, swman without
   arguments, swman with a failing manager, pkgstatus with a failing
   checker). Tighten the existing "did not crash" assertions to the real code.
4. Run the container tests (`make test-arch`, `make test-debian`) to find
   failures that were hiding behind exit 0.

## Files to Modify

`src/dotfiles/init.py`, `src/dotfiles/pkgstatus.py`, `src/dotfiles/swman.py`,
`tests/test_init.py`, `tests/test_pkgstatus.py`, `tests/test_swman.py`.

## Testing Strategy

- New exit-code tests (above), `make test-unit`, `make test-compile`.
- `make test-arch` / `make test-debian` for the hidden-failure sweep.
- Manual: `dotfiles-swman` (no args) -> `echo $?` is non-zero.

## Dependencies

- Best merged after #74 (touches `init.py` `main`) and the lint cleanup #77
  (`project_status.py`, `pkgstatus.py`, `swman.py`), to avoid conflicts. Not a
  hard blocker.

## Open Questions

1. **Usage errors in swman:** exit 1 (today's intent) or 2 (Click convention
   via `click.UsageError`)?
2. **`pkgstatus --refresh` failures:** should the systemd unit fail loudly, or
   should the tool stay exit 0 for refresh failures so the timer is not
   marked failed (it already logs the error)?
3. **SIGINT:** keep 130 (shell convention)?
