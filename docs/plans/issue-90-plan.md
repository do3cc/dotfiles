# Implementation Plan: Issue #90

**ruff 0.17 no longer enables DTZ rules: 5 unused noqa directives fail ruff-check**

## Issue Summary

`uvx ruff check .` is clean with ruff 0.16.10 (after #82) but reports 5 `RUF100`
(unused `noqa`) errors with 0.17.0, because 0.17 no longer enables the `DTZ`
rules by default.

## Current State Analysis

- No ruff config in the repo and no pinned version (decision on #77: use the
  defaults, accept that newer versions can fail).
- Measured with `ruff check --show-settings`: 0.17.0 removed `DTZ001`,
  `DTZ005`, `DTZ006`, `DTZ007`, `DTZ011`, `DTZ012`, `DTZ901` from the default
  rules and added `F406`. Everything else is unchanged.
- The 5 findings, all `datetime.now()  # noqa: DTZ005`:
  `src/dotfiles/init.py:1098`, `:1107`, `tests/test_init.py:365`, `:381`,
  `:414`. The code uses naive timestamps on purpose: `init.py` writes and reads
  a marker file (`~/.cache/dotfiles_last_update`) with naive ISO timestamps, so
  mixing in timezone-aware values would raise `TypeError` on comparison.
- The 23 `# noqa: BLE001` directives are still valid on 0.17.0.

## Implementation Approach

1. `uvx ruff check --fix .` (removes exactly the 5 unused directives), then
   `ruff format .`.
2. Review the diff: only those 5 comments disappear; no code change.
3. Verify with 0.17.0: `uvx ruff check .` and `ruff format --check .` clean;
   `make test-unit`, pyright.

## Files to Modify

`src/dotfiles/init.py`, `tests/test_init.py`.

## Testing Strategy

`uvx ruff@0.17.0 check .` clean; `make test-unit`; `make test-compile`;
pre-commit on the two files.

## Dependencies

None. Independent of the other open PRs (#87, #88, #89 touch other lines).

## Open Questions

1. **Remove the directives (proposed) or keep them for older ruff?** After the
   change, ruff 0.16.x reports `DTZ005` for these 5 lines. Alternatives: an
   explicit `[tool.ruff.lint]` config (contradicts the "use defaults" decision
   on #77), or making the timestamps timezone-aware (needs a marker-file
   format migration, not worth it). Proposed: remove the directives and accept
   that 0.16.x is outdated, as `dotfiles-swman` keeps ruff current.
