# Implementation Plan: Issue #48

**Change the log format for logging to logfmt**

## Issue Summary

Write `dotfiles.log` as logfmt instead of JSON (easier to read and grep), and
analyse whether some keys need special handling in the log configuration. The
ticket asked to wait for #46; it is merged (#91), so the plan builds on it.

## Current State Analysis

- `setup_logging` (`logging_config.py`) configures structlog with
  `JSONRenderer` and a stdlib `RotatingFileHandler` (10 MB, 5 backups,
  `%(message)s`). One JSON object per line.
- Coupled to the JSON format:
  - `ConsoleOutput.log_file_hint` prints `tail -f <path> | jq -c .` (#91).
  - `tests/test_verbose_logging.py` asserts that exact hint;
    `tests/test_logging_config.py` parses entries with `json.loads` (4 places).
  - CLAUDE.md: "JSON format", and the `jq 'select(.event=="update_completed")'`
    queryability example.
- No code reads the log file back; only humans and `tail`.

### Analysis: values the logfmt renderer handles badly

Checked with structlog 25.4 (`LogfmtRenderer`) against values the tools really
bind:

| Value                                                                             | Where                                | logfmt result                                                                                                                       | Handling                                                                                                           |
| --------------------------------------------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| list (`command`, `packages`)                                                      | process_helper, swman                | `command="['sudo', 'pacman', '-Syu']"` (Python repr in quotes)                                                                      | normalise lists to one string (see open question 1)                                                                |
| Enum (`package_manager_type`, `manager_type`)                                     | swman `bind_log`                     | `T.SYSTEM` (and `<T.SYSTEM: 'system'>` in JSON today)                                                                               | render `.value`; or bind `.value` at the source                                                                    |
| `Path` (`log_file`, `last_run_file`, ...)                                         | init, pkgstatus                      | fine (`str`, quoted when it has spaces)                                                                                             | none                                                                                                               |
| multi-line strings (`release_data` = whole `/etc/os-release`, `stderr`, `stdout`) | init, process_helper                 | quoted, newlines escaped as `\n`: stays one line, long                                                                              | optional truncation (open question 2)                                                                              |
| `None`                                                                            | various                              | `none=` (empty value), same as `""`                                                                                                 | render the literal `none` or drop the key                                                                          |
| booleans                                                                          | `success`, `dry_run`, `is_available` | default `bool_as_flag=True`: `True` becomes a bare key `a`, `False` becomes `b=false`                                               | set `bool_as_flag=False` so both are `key=true/false`                                                              |
| `exc_info`                                                                        | `log_exception`                      | **today the JSON has only `"exc_info": "ZeroDivisionError('division by zero')"`, no traceback** (CLAUDE.md claims a full traceback) | add `structlog.processors.format_exc_info` before the renderer: real traceback in `exception="Traceback ...\n..."` |
| key order                                                                         | all                                  | JSON today puts `event` near the end; logfmt default puts `event` first                                                             | `key_order=["timestamp", "level", "event", "script", "pid"]`, rest in insertion order                              |

## Implementation Approach

1. `logging_config.py`: replace `JSONRenderer()` with
   `LogfmtRenderer(key_order=[...], bool_as_flag=False)`; add
   `format_exc_info` before it; add a small processor (before the renderer)
   that normalises Enum -> `.value`, `None`, lists, and truncates long values
   as decided.
2. `ConsoleOutput.log_file_hint`: `tail -f <path>` (no jq; the lines are no
   longer JSON); keep soft-wrap; update the docstring.
3. Tests: replace `json.loads` of log entries by a tiny logfmt parser helper in
   `tests/` (or `shlex`-based) and assert on keys; add tests for each row of the
   analysis table (list, Enum, None, bool, multi-line, exception with
   traceback, key order).
4. CLAUDE.md: "Log File Management / Format: logfmt", replace the `jq` example
   with `grep 'event=update_completed' dotfiles.log`, fix the `log_exception`
   description (it now includes the traceback), update the `--verbose` bullet.
5. Existing log files contain JSON lines. They are not rewritten; the file is
   mixed until rotation (open question 5).

## Files to Modify

`src/dotfiles/logging_config.py`, `src/dotfiles/output_formatting.py`,
`tests/test_logging_config.py`, `tests/test_verbose_logging.py`, `CLAUDE.md`
(and `src/dotfiles/swman.py` only if the Enum is bound as `.value` at the
source).

## Testing Strategy

New unit tests per analysis row; `make test-unit`, `make test-compile`; run each
tool once with `--verbose` and read the real log lines (`tail`), including one
forced exception to see the traceback line.

## Dependencies

#46 / PR #91 (merged). No conflicts expected with open work.

## Open Questions

1. **List values** (`command`, `packages`): keep the Python repr in quotes
   (default, zero code), or join them (`command="sudo pacman -Syu"`,
   `packages=git,vim`) with a small processor? Proposed: join, `shlex.join` for
   `command`, comma for the rest.
2. **Very long values** (the whole `os-release`, command `stdout`/`stderr`):
   keep as they are (proposed), or truncate at a limit such as 2000 characters
   with a `...[truncated]` marker?
3. **Tracebacks:** add `format_exc_info` so `log_exception` records the real
   traceback in an `exception` key (proposed). Today only the exception's repr
   is logged.
4. **Hint and docs wording:** `tail -f <path>` and a `grep event=...` example
   instead of the `jq` ones (proposed). OK?
5. **Existing JSON lines** in `~/.cache/dotfiles/logs/dotfiles.log`: leave them
   (the file is mixed until the 10 MB rotation), or rename the old file once to
   `dotfiles.log.json` on the first logfmt write?
