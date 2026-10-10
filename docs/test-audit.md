# Test suite audit

Audit for issue #84 (plan: `docs/plans/issue-84-plan.md` on branch
`issue-84-plan`). This is PR 1: findings and a decision per finding. PR 2
applies them. Measured on `main` after #91: 249 test functions, 342 collected
cases.

## How it was measured

- AST scan of `tests/test_*.py`: test functions without any `assert`,
  `pytest.raises` or mock assertion; assertions combined with `or` that accept
  success and failure; tests whose only assertions are mock-call assertions.
- `ruff check tests --select PT,B015,B018` for style and weak patterns.
- CI workflows read for what actually runs (`.github/workflows/*.yml`).
- One mutation run (`mutmut` 3.8) on selected modules, see the last section.

## 1. Tests that check nothing (4)

| Test                                                                         | Problem                                        | Decision                                                                                                                                           |
| ---------------------------------------------------------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_init.py::test_install_dependencies`                                    | Body is `pass  # TODO: Implement`              | **Delete.** A real test of `install_dependencies` needs the NVM/Pyenv install scripts mocked; the gap is recorded in section 7 (init.py coverage). |
| `test_output_formatting.py::test_pause_for_interactive_context_manager`      | Enters the context manager and asserts nothing | **Strengthen:** set `output._active_progress` to a mock, assert `stop()` was called inside the block and `start()` after it.                       |
| `test_output_formatting.py::test_pause_for_interactive_with_active_progress` | Same, with a real progress bar                 | **Merge** into the test above (the real-bar variant adds nothing the mock one does not check).                                                     |
| `test_status_cache.py::test_invalidate_missing_file_is_ok`                   | "Does not raise" only                          | **Strengthen:** assert the file still does not exist and `cache_invalidated` was logged.                                                           |

## 2. Assertions that pass on success and on failure (2)

| Test                                                                   | Assertion                                                | Decision                                                                                |
| ---------------------------------------------------------------------- | -------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `test_init.py::test_main_successful_execution`                         | `exit_code == 0 or exit_code is None`                    | `assert result.exit_code == 0`. Since #83 failures exit non-zero, so this can be exact. |
| `test_init.py::test_main_uses_status_messages_not_persistent_progress` | `exception is None or isinstance(exception, SystemExit)` | `assert result.exit_code == 0` and `result.exception is None`.                          |

## 3. Tests whose only assertions are mock calls (52)

Not a defect by itself: for a thin wrapper the call is the contract.
Per group:

| Group                                                                                                                                             | Count | Verdict                                                                                                                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_logging_config.py`: `log_error/warning/info/progress/subprocess_result/exception`, `bind` (`logger.error` called with ...)                  | 22    | **Keep.** These wrappers do nothing but forward with a fixed event name; the assertion on the forwarded call is the behaviour. Parametrising the near-duplicates (`..._with_no_context`, `..._with_numeric_context`) per method would remove about 8 tests without losing a case. |
| `test_output_formatting.py`: `status/success/error/warning/info/header/table/json` (`console.print` called, not called when quiet, logger called) | 25    | **Keep.** `respects_quiet_mode` / `respects_verbose_mode` assert behaviour (nothing printed). `..._prints_green_with_default_emoji` asserts the style string passed to Rich; fine for a wrapper.                                                                                  |
| `test_process_helper.py`: `test_binds_context_before_execution`, `test_logs_command_starting`, `test_logs_subprocess_result_on_success`           | 3     | **Keep, but** `test_binds_context_before_execution` asserts how the logger is bound (an implementation detail); replace by asserting the logged record content with a real logger.                                                                                                |
| `test_init.py::test_reload_systemd_user_daemon_failure` (mine, #83)                                                                               | 1     | **Strengthen:** also assert the warning text names the container case and the exception was logged.                                                                                                                                                                               |
| `test_process_helper.py::test_real_timeout`                                                                                                       | 1     | Uses a real subprocess; keep.                                                                                                                                                                                                                                                     |

## 4. Real findings from the `PT` rules (4)

`PT017`, `PT011` and 2x `PT018` are the only non-style hits (the other 14 are
parametrize style, not enforced, per the decision on #84):

| Location                     | Rule                                     | Decision                                              |
| ---------------------------- | ---------------------------------------- | ----------------------------------------------------- |
| `test_logging_config.py:465` | PT017 assertion inside `except`          | Rewrite with `pytest.raises` and assert on `excinfo`. |
| `test_status_cache.py:165`   | PT011 `pytest.raises(OSError)` too broad | Add `match=` for the directory-instead-of-file error. |
| `test_swman.py:470`, `:480`  | PT018 composite `assert a and b`         | Split. (Both are mine, from #33.)                     |

## 5. Tests that never run

| Item                                           | Finding                                                                                                        | Decision                                                                                                                                                         |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_dockerfile_manifest.sh` (91 lines) | Referenced nowhere; passes today; 5 `grep` checks for text in `run-claude.sh`                                  | **Replace** by a pytest that parses `packages.yaml` and `run-claude.sh` and asserts the manifest keys the script reads (`base.debian`) exist; delete the script. |
| `integration` marker (8 tests)                 | Declared and used, never selected                                                                              | **Keep as documentation**, define it in CLAUDE.md; CI runs everything.                                                                                           |
| **CI does not run pytest at all**              | `pr.yml` runs `dotfiles-init --help`; `ci.yml` runs the container installs; no `make test-unit`, no pre-commit | **Add a unit test job to `pr.yml`** (decision 6 on the issue), with `fish` installed so `tests/test_wt_functions.py` does not skip silently.                     |
| Tests that skip silently                       | `test_wt_functions.py` and `test_git_config.py` skip when `fish`/`git` are missing                             | Install both in the CI job; make the AST check list skipped tests in its output.                                                                                 |

## 6. Property-based tests

6 `@given` tests (`test_init.py` 3, `test_logging_config.py` 2, `test_swman.py`
1). They cover config merging, the logging wrappers and the arrow-update
parser. The parsers added in #33 (`parse_apt_upgradable`, `parse_uv_outdated`)
and the logfmt normaliser (#48) have example tests only; a round-trip
property test for each is cheap and is proposed for PR 2.

## 7. Coverage gaps worth knowing

`init.py` is the largest module and the least tested: the install steps
(`install_dependencies`, package installation, shell setup, Tailscale,
`link_accounts`) are only reached through `main()` with the whole OS layer
mocked. Real tests need the command runner mocked per step. Not in scope for
this audit; recorded so the deleted `test_install_dependencies` stub does not
hide the gap.

## 8. Mutation testing

One run of `mutmut` 3.8 in a scratch worktree (config not committed), restricted
to `logging_config.py` and the parsers of `swman.py` (the new, pure code from
#33). **`init.py` was not mutated:** mutant generation for its roughly 2,100
lines did not finish within 10 minutes, so its config building is not covered
by this run.

| Target                                                                                                  | Mutants | Killed | Survived |
| ------------------------------------------------------------------------------------------------------- | ------- | ------ | -------- |
| `swman.py` parsers (`parse_arrow_updates`, `parse_apt_upgradable`, `parse_uv_outdated`, `_parse_lines`) | 64      | 62     | 2        |
| `logging_config.py`                                                                                     | 128     | 94     | 34       |

**Caveat on the numbers.** mutmut reports 16 survivors in `setup_logging`, but
that function configures process-global structlog state, and the result is not
reliable: I applied one of them by hand (`logger_factory=None`) and the tests
**do** fail (4 failures running `test_logging_config.py` alone). Those 16 are
treated as tool artifacts, not as findings. The other survivors were each
checked by hand by applying the mutation and running the tests:

| Survivor                                                                   | Verdict                                                                                                                                                                         | Action in PR 2                                 |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `_parse_lines`: `continue` replaced by `break` on an empty line            | **Real gap.** No test has an empty line _between_ entries (the existing one only has a trailing empty line); a blank line in `checkupdates` output would silently cut the list. | Add the test.                                  |
| `parse_apt_upgradable`: `old_first=False` replaced by `old_first=None`     | Equivalent mutant (`None` is falsy, same behaviour).                                                                                                                            | None.                                          |
| `log_subprocess_result`: key `operation` renamed                           | **Real gap.** The bound key `operation=subprocess` is never asserted.                                                                                                           | Assert the full bound data once.               |
| `log_subprocess_result`: event name `Subprocess output` replaced by `None` | **Real gap.** The debug event name is not asserted. (This event name also breaks the snake_case rule in CLAUDE.md.)                                                             | Assert the name; rename to a snake_case event. |
| `log_debug`: `**context` dropped                                           | **Real gap.** `log_debug` has fewer tests than its siblings; none passes context.                                                                                               | Add the test.                                  |
| `log_subprocess_result`: the remaining 14 survivors                        | Same two causes (keys of the bound dictionary and the debug event) as above.                                                                                                    | Covered by the two rows above.                 |

So three real test gaps plus one naming problem, all in thin logging code; the
parsers are well covered. This is a small sample; it does not say anything
about `init.py`.

## 9. Changes for PR 2

1. Apply sections 1, 2, 3 (the named rewrites) and 4.
2. Replace `test_dockerfile_manifest.sh` by the pytest check.
3. Add the AST "test without assertion" check (script + pre-commit hook + CI).
4. Add the unit test job to `pr.yml` with `fish` installed.
5. Document the `integration` marker in CLAUDE.md.
6. Add the property tests of section 6.
7. Close the real gaps from section 8 (blank line between parser entries, `log_subprocess_result` keys and event name, `log_debug` context) and rename the `Subprocess output` event to snake_case.
