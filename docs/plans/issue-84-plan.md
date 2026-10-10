# Implementation Plan: Issue #84

**Review the test suite for fake tests and silently ignored tests**

## Issue Summary

Audit the whole suite for tests that cannot fail or never run, fix what the
audit finds, and add guard rails so it stays fixed.

## Current State Analysis

Measured on main (249 test functions, AST scan plus grep):

- **No assertion at all (4):** `test_init.py::test_install_dependencies`
  (`pass  # TODO: Implement`), `test_output_formatting.py::
test_pause_for_interactive_context_manager` and
  `..._with_active_progress`, `test_status_cache.py::
test_invalidate_missing_file_is_ok` (probably an intentional "does not
  raise", but it should say so with `pytest.raises`-free structure and an
  assertion on the resulting state).
- **Assertions that pass on success and on failure (2):**
  `test_main_successful_execution` (`exit_code == 0 or exit_code is None`) and
  `test_main_uses_status_messages_not_persistent_progress`
  (`exception is None or isinstance(exception, SystemExit)`). #83 tightened the
  others.
- **Only mock-call assertions (52):** mostly thin-wrapper tests in
  `test_logging_config.py` (35: "`log_error` calls `logger.error` with ..."),
  `test_output_formatting.py` (about 25, "`status` calls `console.print`") and
  `test_process_helper.py`. For a wrapper whose whole job is the call this is a
  legitimate test, but some assert the mock's own configuration. Needs a
  per-test decision, not a blanket rule. `test_reload_systemd_user_daemon_failure`
  (mine, #83) only asserts `output.warning` was called in the container branch;
  that is fine but worth a look.
- **Never run:** `tests/test_dockerfile_manifest.sh` (91 lines) is referenced
  nowhere (Makefile, CI, pre-commit). The `integration` marker (8 tests) is
  declared and used, but nothing selects or deselects it, so CI runs those tests
  together with the unit tests; the marker is informational only.
- **Property tests:** 6 `@given` tests (init 3, logging 2, swman 1; #33 added
  one). Few, but they are the ones that can find real bugs.
- Container tests (`make test-arch/-debian`) now fail on a failing init (#83),
  so that earlier blind spot is closed.
- Coverage was 45% when #53 closed (`init.py` 24%, `swman.py` 26% then; #33 and
  #83 added tests since).

## Implementation Approach

1. **Audit report** (a short `docs/` note or the PR description, not a long
   doc): per finding, the decision: strengthen, delete, or keep (with reason).
   Cover the 4 + 2 above and sample-review the 52 mock-only tests, grouped by
   file.
2. **Fix the findings:** give the no-assertion tests a real assertion or delete
   them (`test_install_dependencies` becomes a real test of
   `install_dependencies` with the command runner mocked, or goes); tighten the
   two either-or assertions to the exact exit code and state; rewrite mock-only
   tests that assert their own mock.
3. **Wire or delete `test_dockerfile_manifest.sh`:** if it still passes, call it
   from `make test-unit` and CI; if it checks something the pytest suite covers
   (`test_package_manifest.py`), delete it.
4. **Define `integration`:** document in CLAUDE.md what it means (tests that
   drive `main()` end to end with the OS layer mocked) and that CI runs them;
   keep running them by default.
5. **Guard rails:**
   - A small script (AST) that fails if a `test_*` function has no `assert`,
     `pytest.raises` or mock assertion, run from pre-commit and CI. No new
     dependency.
   - Optional ruff `PT` (pytest-style) and `B015`/`B018` rules. This needs a
     `[tool.ruff.lint]` section and contradicts the "ruff defaults only"
     decision on #77, so it is an open question.
6. **Mutation testing (report only):** run `mutmut` once on
   `init.py` config building, `swman.py` parsers (new in #33) and
   `logging_config.py`; list surviving mutants as findings. Do not add it to CI.

## Files to Modify

`tests/*.py`, `tests/test_dockerfile_manifest.sh` (or its removal),
`Makefile`, `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, a new small
script (for example `.pre-commit-hooks/check-test-assertions.py`), `CLAUDE.md`.

## Testing Strategy

The guard-rail script gets its own tests (a function without assertion fails, a
`pytest.raises` test passes). After the fixes: `make test-unit`, and a
manual mutation check on the rewritten tests (break the code, the test must go
red), as done for the `pushf` test in #88.

## Dependencies

None blocking. Touches many test files; do it after the open PRs (#91) are
merged to avoid conflicts in `tests/test_init.py` / `tests/test_swman.py`.
Related: #90 (ruff 0.17 lint), #53 (closed, coverage).

## Open Questions

1. **Guard rails:** add the AST "test without assertion" check to pre-commit and
   CI (proposed)? And also enable ruff `PT`/`B015` rules via a
   `[tool.ruff.lint]` section, which contradicts "ruff defaults only" from #77?
2. **`test_dockerfile_manifest.sh`:** wire it into `make test-unit`/CI
   (proposed, if it still passes) or delete it?
3. **`integration` marker:** keep it as documentation only and keep running
   everything (proposed), or run those tests in a separate CI step/target?
4. **Mutation testing:** run `mutmut` once and report (proposed), or skip it?
5. **Scope of one PR:** audit and fixes together (proposed), or audit report
   first (for your review) and the fixes in a second PR?
