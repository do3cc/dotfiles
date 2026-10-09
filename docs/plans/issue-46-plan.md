# Implementation Plan: Issue #46

**For all commands, with --verbose hint the user to the log file**

## Issue Summary

Every tool needs a `--verbose` flag. In verbose mode the log level must be
debug and the user gets a copy-pasteable `tail` command for the shared log
file. Add this as a rule to CLAUDE.md.

## Current State Analysis

- `setup_logging()` (`logging_config.py`) hard-codes `level=logging.INFO` and
  writes JSON lines to `~/.cache/dotfiles/logs/dotfiles.log` (the path is
  only a parameter default). All four tools share that file.
- `--verbose` exists on `init`, `swman` and `pkgstatus` (Click). It only
  toggles verbose-only messages in `ConsoleOutput` (one place,
  `output_formatting.py:84`); it does not touch logging.
- `dotfiles-status` (`project_status.py`) uses `argparse` and has no
  `--verbose`.
- `LoggingHelpers.log_debug()` exists but has no callers, so debug level
  would show nothing new today.
- `setup_logging` is called before `ConsoleOutput` is created in `init`,
  `swman` and `pkgstatus`.
- #48 (logfmt) is blocked by this ticket.

## Implementation Approach

1. `setup_logging(script_name, verbose=False, log_dir=...)`: set the stdlib
   root level to `DEBUG` when verbose, else `INFO`. Expose the log file path
   (for example `LoggingHelpers.log_file`).
2. Helper `announce_log_file(output, logger)` (in `output_formatting.py` or
   `logging_config.py`) that, when verbose and not quiet, prints
   `Log file: tail -f <path>` (optionally `| jq -c .` since the lines are
   JSON). Call it once at the start of each tool's `main`.
3. `dotfiles-status`: add `--verbose` (see Open Questions about converting it
   to Click).
4. Give debug level something to show: add `log_debug` calls where the tools
   run external commands (`process_helper.run_command_with_error_handling`:
   command, cwd, timeout) and at key decision points.
5. CLAUDE.md: add the rule (all tools have `--verbose`, share the log file,
   switch to debug level, and print the tail command in verbose mode).

## Files to Modify

`src/dotfiles/logging_config.py`, `output_formatting.py`,
`process_helper.py`, `init.py`, `swman.py`, `pkgstatus.py`,
`project_status.py`, `CLAUDE.md`, tests.

## Testing Strategy

- `setup_logging(verbose=True)` sets DEBUG; default stays INFO (logger-level
  assertion and a debug record in a temp log dir).
- Hint printed only with `--verbose` and not with `--quiet`, for each of the
  four tools (CliRunner / capsys).
- `--verbose` is accepted by all four entry points (`--help` test).
- `make test-unit`, `make test-compile`.

## Dependencies

- Blocks #48. Touches the tool mains, like #76; do #76 first.

## Open Questions

1. **Convert `dotfiles-status` to Click?** CLAUDE.md says all tools use Click
   and Rich; this one uses `argparse`. Converting is cleaner but bigger.
   Proposed: convert, in the same PR.
2. **Tail hint format:** plain `tail -f path` or with `| jq -c .`?
3. **`--verbose` with `--quiet`:** error out, or quiet wins?
4. **How much debug logging** to add now (process helper only, or broader)?
