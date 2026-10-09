# Implementation Plan: Issue #73

**Remove environment profiles (minimal/work/private); install one configuration**

## Issue Summary

Only the `private` setup is used. Remove the three-profile machinery and make
today's `private` result the one and only configuration.

## Current State Analysis

- `src/dotfiles/init.py`
  - `VALID_ENVIRONMENTS = ["minimal", "work", "private"]`, validated in
    `Linux.__init__`; `self.environment` is stored.
  - `EnvironmentConfig` is merged in layers: `_get_base_config()` (Linux),
    `Arch._get_base_config()`, plus `_get_environment_configs()` (Linux and
    Arch) selected by `_build_environment_config(environment)`.
  - `private`-only content: `config_dirs` irssi (and ghostty once #72 lands),
    `systemd_user_services=["syncthing.service"]` (#70), Arch
    `systemd_services=["tailscaled"]`, the Tailscale block in `link_accounts`
    (`if self.environment in ["private"]`), and
    `packages.yaml: environments.private.arch`.
  - `work`-only content: `ssh_key_email="patrick.gerken@zumtobelgroup.com"`.
  - `self.environment` is also written into the SSH key comment
    (`{hostname} {email} {environment}`) and the GitHub key title
    (`{hostname} {environment}`).
  - `main()` requires `DOTFILES_ENVIRONMENT`, validates it, and prints it in
    the docstring/help text (three places).
- `packages.yaml`: `environments.{private,work,minimal}` and
  `aur.environments.*` (all empty except `private.arch`; every `debian` list
  is empty). Readers: `init.py` (Arch only; Debian reads `base` only),
  `local_bin/run-claude.sh` (reads `base.debian` only, so unaffected),
  `tests/test_package_manifest.py`.
- Test/CI plumbing that passes the variable: `Makefile` (6 places),
  `test/run_tests.sh` (`--environment`, default `minimal`),
  `test/run_test.sh`, `test/Containerfile.{arch,debian}` CMD,
  `.github/workflows/ci.yml` ("minimal environment" step).
- Docs: `README.md` (Quick Start), `CLAUDE.md` (setup section, package
  manifest section), `docs/testing/interactive-sudo-commands.md`.
  `docs/TEST_RESULTS.md` and old `docs/plans/*` are historical; leave them.
- `git/config`: `[http "https://git.dev.zgrp.net/"] sslVerify = false` is a
  work-host leftover.

## Implementation Approach

Prerequisite: PR #72 (ghostty) is merged, so the ghostty lines move together
with the rest.

1. **`packages.yaml`**: append `environments.private.arch` to `base.arch`
   (keep alphabetical order), delete the `environments:` block and
   `aur.environments`, update the header comment.
2. **`init.py` core**:
   - Delete `VALID_ENVIRONMENTS`, the `environment` constructor parameter,
     `self.environment`, `_get_environment_configs` (Linux and Arch),
     `_build_environment_config`. `self.config = self._get_base_config()`.
   - Move into `Linux._get_base_config()`: irssi + ghostty config dirs,
     `syncthing.service`. Move `tailscaled` into `Arch._get_base_config()`.
   - `ssh_key_email` becomes the single base value; drop the `work` override.
   - Keep `EnvironmentConfig.merge_with`; it still combines the Linux and
     Arch base configs.
   - Tailscale block: remove the `if self.environment` guard.
   - SSH key: comment becomes `{hostname} {email}`, GitHub title becomes
     `{hostname}`. Existing keys are matched on the key blob, not the title,
     so existing machines are not re-uploaded.
   - `detect_operating_system(logger, no_remote_mode)`: drop `environment`.
   - `main()`: remove the env var read/validation and error text; update the
     module/CLI help text.
3. **Tests**:
   - `tests/test_init.py`: drop the environment argument everywhere; remove
     `test_main_no_environment_variable` / `test_main_invalid_environment`;
     replace `test_buildEnvironmentConfig` with assertions that the base
     config contains ghostty, irssi, `syncthing.service`.
   - `tests/test_package_manifest.py`: drop `environments` assertions, assert
     the former private packages are in `base.arch`.
4. **Plumbing**: remove `DOTFILES_ENVIRONMENT` / `--environment` from
   `Makefile`, `test/run_tests.sh`, `test/run_test.sh`,
   `test/Containerfile.*`, `ci.yml` (rename the step to "Test ${{ matrix.os }}").
5. **Docs**: README Quick Start, CLAUDE.md (setup + package manifest
   sections), `docs/testing/interactive-sudo-commands.md`.
6. **`git/config`**: remove the `zgrp.net` section (see Open Questions).

Suggested commits: packages.yaml + init.py + unit tests together (they must
change together); plumbing/CI; docs; git config.

## Files to Modify

`packages.yaml`, `src/dotfiles/init.py`, `tests/test_init.py`,
`tests/test_package_manifest.py`, `Makefile`, `test/run_tests.sh`,
`test/run_test.sh`, `test/Containerfile.arch`, `test/Containerfile.debian`,
`.github/workflows/ci.yml`, `README.md`, `CLAUDE.md`,
`docs/testing/interactive-sudo-commands.md`, `git/config`.

## Testing Strategy

- `make test-unit`, `make test-compile`, `pre-commit run --files ...`.
  (`test_pkgstatus.py::test_refresh_init_cache_uses_default_path_when_env_unset`
  already fails on main; unrelated.)
- `make test-arch`, `make test-debian`, `make test-ubuntu` (container runs
  use `--no-remote`).
- `grep -rn "DOTFILES_ENVIRONMENT\|VALID_ENVIRONMENTS\|environments\b"`
  returns only historical docs.

## Dependencies

- PR #72 merged first (same lines in `init.py`).
- Follow-up: #40 (TOML config) assumes the profiles and must be rewritten.

## Open Questions

1. **Arch CI cost.** The Arch container run now installs the former private
   packages (firefox, imagemagick, bitwarden, tailscale, ghostty, ...).
   Slower and a bigger failure surface. Accept, or trim the CI package set?
2. **Stale env var.** If `DOTFILES_ENVIRONMENT` is still exported (shell rc,
   scripts): silently ignore (proposed) or fail with a hint?
3. **`git.dev.zgrp.net` `sslVerify = false`.** Remove with the work profile
   (proposed), or still needed?
4. **Desktop-only items on Debian/Ubuntu.** irssi/ghostty config dirs get
   linked there without the packages (harmless symlinks). Fine, or keep
   desktop items Arch-only?
5. **Work email** `patrick.gerken@zumtobelgroup.com` disappears from the
   repo. Confirm.
