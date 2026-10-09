# Implementation Plan: Issue #71

**Ghostty config is not managed by dotfiles**

## Issue Summary

Patrick has switched to Ghostty as his primary terminal and dropped tmux
(Ghostty's native split/tab keybinds now cover what tmux did). Its config at
`~/.config/ghostty` is a real, untracked directory on disk today — not
version controlled, not linked from this repo, and not reproduced by
`dotfiles-init` on a fresh machine. This repo already manages equivalent
per-tool config directories (`fish`, `lazy_nvim` → `nvim`, `direnv`, `git`,
`irssi`); Ghostty needs to join that list.

## Current State Analysis

### How config linking works today

`EnvironmentConfig.config_dirs` (`src/dotfiles/init.py`) is a
`list[tuple[str, str]]` of `(repo_dir_name, config_target_name)` pairs.
`Linux._get_base_config()` sets the dirs common to every environment:

```python
config_dirs=[
    ("direnv", "direnv"),
    ("fish", "fish"),
    ("lazy_nvim", "nvim"),
    ("git", "git"),
],
```

`Linux._get_environment_configs()` adds environment-specific dirs, e.g. the
`private` environment adds `("irssi", "irssi")`.

`Linux.install_config_dirs` (around line 381) then, for each pair, symlinks
`~/.config/{target}` → `{dotfiles_dir}/{repo_dir_name}`. Important behavior
to account for during migration: it only creates the symlink when
`~/.config/{target}` does **not already exist**. If it exists as a real
directory (not a symlink), it just logs a warning and does nothing —
it never moves files for you. So the real config must be moved into the
repo and the original directory removed _before_ `dotfiles-init` can link
it.

### Current Ghostty state on this machine

`~/.config/ghostty/` has two files:

- `config` — the real, active config (64 lines: sets `theme = Alabaster` and
  a block of `keybind` lines replicating tmux-style pane/tab navigation
  natively in Ghostty — this is literally the tmux replacement).
- `config.txt` — byte-identical to `config`. Looks like an accidental
  duplicate/editor artifact, not a second file Ghostty reads. Should not be
  carried into the repo.

### Packages

Ghostty is not in `packages.yaml` under any environment. It's currently
installed manually (confirmed via `pacman -Qi ghostty`, version 1.3.1 from
`cachyos-extra-v3`).

Packaging status by distro:

- **Arch**: in the official `extra` repo (and CachyOS's extra mirror) — a
  plain `ghostty` package name works.
- **Ubuntu**: officially in the Ubuntu 26.04 LTS archive (`apt install
ghostty`, version 1.3.0). Earlier Ubuntu releases need a PPA/deb/snap.
- **Debian**: not confirmed available in Debian's own repos as of this
  writing — needs a check at implementation time (`apt-cache show ghostty`
  on the target release, or Debian's package tracker) since this repo's
  `Debian` class covers both Debian and Ubuntu under one `packages.yaml`
  `debian:` list (see `base.debian`, `environments.*.debian` in
  `packages.yaml`), and the two distros currently disagree on availability.

### tmux

No active tmux integration exists in this repo to remove: `packages.yaml`
has no `tmux` entry, `config_dirs` has no tmux entry, and no fish config
auto-starts tmux. The only repo mention is a stale example path in
`docs/plans/2025-10-24-link-local-bin.md`, which is a historical plan doc,
not live code — no cleanup action needed there. tmux itself is still
installed on this machine as an untracked manual package; removing it is
outside this issue's scope (the gap is about Ghostty's config, not tmux
uninstallation) unless Patrick wants that folded in.

## Implementation Approach

1. **Bring the config into the repo**
   - Create `ghostty/` at the repo root.
   - Copy `~/.config/ghostty/config` → `ghostty/config` (not `config.txt`,
     which is a duplicate to discard).

2. **Wire up `config_dirs`**
   - Add `("ghostty", "ghostty")` to the config_dirs list Ghostty should
     apply to (see Open Questions — base vs. `private`-only, matching the
     precedent irssi set for environment-specific desktop tools).

3. **Add the package**
   - Add `ghostty` to `packages.yaml` under the same environment's `arch`
     list.
   - Add `ghostty` to the `debian` list for that environment only once its
     availability on the targeted Debian/Ubuntu release is confirmed
     (see Open Questions); otherwise leave `debian: []` and track as a
     follow-up.

4. **Migrate this machine**
   - Remove `~/.config/ghostty` (the real directory) and `config.txt`
     after the content is safely copied into the repo and committed.
   - Run `dotfiles-init` to create the symlink `~/.config/ghostty` →
     `<repo>/ghostty`.

5. **Document it**
   - Add a "Ghostty" section to `README.md`, following the structure of
     the existing per-tool sections (what gets installed/linked, any
     manual step left, e.g. Ghostty theme/font install if relevant).

6. **Tests**
   - Follow the pattern in `tests/test_init.py` for existing config_dirs
     entries: assert the new entry is present in the built
     `EnvironmentConfig` for the right environment(s), and (if there's
     existing coverage of `install_config_dirs` symlink creation) that it
     exercises the new pair too. No new runtime logic is being added (no
     new method, unlike the Syncthing work in PR #70), so this should
     mainly be config-table coverage, not new behavioral tests.

## Files to Modify

- `ghostty/config` — new file, copied from `~/.config/ghostty/config`.
- `src/dotfiles/init.py` — add `("ghostty", "ghostty")` to the relevant
  `config_dirs` list(s) in `_get_base_config` or
  `_get_environment_configs`.
- `packages.yaml` — add `ghostty` package entry under the relevant
  environment's `arch` (and `debian`, once confirmed) list.
- `README.md` — new "Ghostty" section documenting the linked config.
- `tests/test_init.py` — assert the new config_dirs entry is present for
  the right environment.

## Testing Strategy

- `make test-unit` — new/updated assertions on `EnvironmentConfig` for the
  relevant environment(s) include `("ghostty", "ghostty")`.
- `make test-compile` — sanity check that nothing broke CLI imports.
- Manual verification on this machine after merge: move the real
  `~/.config/ghostty` content aside, run `dotfiles-init`, confirm
  `~/.config/ghostty` becomes a symlink to the repo's `ghostty/` and Ghostty
  still picks up the theme/keybinds correctly.

## Dependencies

None blocking — this is independent of the open Syncthing work (PR #70,
issue #69).

## Open Questions

1. **Base vs. `private`-only `config_dirs` entry.** Ghostty is a desktop
   GUI terminal, so it likely belongs with `irssi` as a `private`
   environment addition rather than the base list (which `work` also
   inherits, and work machines may not run Ghostty). Needs Patrick's call
   on whether `work` should get it too.
2. **Debian package availability.** Needs a concrete check (`apt-cache
show ghostty` or Debian's tracker) on the specific Debian/Ubuntu release
   this repo targets before adding it to `packages.yaml`'s `debian:` list.
   If unavailable, document the manual install step in the README instead.
3. **`config.txt` duplicate.** Confirmed byte-identical to `config` — safe
   to delete rather than migrate, but flagging in case it was intentionally
   kept as a backup for a reason not visible from the file alone.
