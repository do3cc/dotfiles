# Link Local Bin Files Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Extend the dotfiles init script to automatically create symlinks for all files in `local_bin/` to `~/.local/bin/`

**Architecture:** Extend the existing `EnvironmentConfig` dataclass with a `local_bin_files` field, add a new `link_local_bin()` method to the `Linux` class (following the same pattern as `link_configs()`), and integrate it into the main installation flow.

**Tech Stack:** Python 3.12, Click CLI framework, Rich for output formatting, structlog for logging

---

## Task 1: Extend EnvironmentConfig Dataclass

**Files:**

- Modify: `src/dotfiles/init.py:30-60` (EnvironmentConfig class)

**Step 1: Add local_bin_files field to EnvironmentConfig**

In `src/dotfiles/init.py`, modify the `EnvironmentConfig` dataclass to add the new field:

```python
@dataclass
class EnvironmentConfig:
    """Type-safe configuration for a specific environment."""

    # Package management
    packages: list[str] = field(default_factory=list[str])
    aur_packages: list[str] = field(default_factory=list[str])

    # Configuration directories: (source_dir, target_dir)
    config_dirs: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])

    # Local bin files to link
    local_bin_files: list[str] = field(default_factory=list[str])

    # System services to enable
    systemd_services: list[str] = field(default_factory=list[str])

    # Environment-specific overrides
    ssh_key_email: str | None = None
```

**Step 2: Update merge_with method**

Update the `merge_with()` method to handle the new field:

```python
def merge_with(self, base_config: "EnvironmentConfig") -> "EnvironmentConfig":
    """Merge this config with a base, with this taking priority."""
    return EnvironmentConfig(
        packages=list(set(base_config.packages).union(set(self.packages))),
        aur_packages=list(
            set(base_config.aur_packages).union(set(self.aur_packages))
        ),
        config_dirs=list(set(base_config.config_dirs).union(set(self.config_dirs))),
        local_bin_files=list(
            set(base_config.local_bin_files).union(set(self.local_bin_files))
        ),
        systemd_services=list(
            set(base_config.systemd_services).union(set(self.systemd_services))
        ),
        ssh_key_email=self.ssh_key_email or base_config.ssh_key_email,
    )
```

**Step 3: Update Linux.\_get_base_config to include local_bin_files**

Modify the `_get_base_config()` method in the `Linux` class to include the new field:

```python
def _get_base_config(self) -> EnvironmentConfig:
    """Get base configuration for Linux systems."""
    return EnvironmentConfig(
        config_dirs=[
            ("alacritty", "alacritty"),
            ("direnv", "direnv"),
            ("fish", "fish"),
            ("lazy_nvim", "nvim"),
            ("tmux", "tmux"),
            ("git", "git"),
        ],
        local_bin_files=["*"],  # Link all files from local_bin/
        ssh_key_email="sshkeys@patrick-gerken.de",
    )
```

**Step 4: Run compilation test**

Run: `make test-compile`
Expected: PASS (all tools can import and show help)

**Step 5: Commit dataclass changes**

```bash
git add src/dotfiles/init.py
git commit -m "feat: add local_bin_files field to EnvironmentConfig"
```

---

## Task 2: Implement link_local_bin Method

**Files:**

- Modify: `src/dotfiles/init.py:279-378` (add new method after link_configs)

**Step 1: Add link_local_bin method to Linux class**

Add the new method after the `link_configs()` method in the `Linux` class (around line 378):

```python
def link_local_bin(self, logger: LoggingHelpers, output: ConsoleOutput):
    """Create symlinks for local_bin files with comprehensive error handling"""

    # Ensure ~/.local/bin exists
    local_bin_dir = self.homedir / ".local/bin"
    logger = logger.bind(local_bin_dir=local_bin_dir)
    try:
        local_bin_dir.mkdir(parents=True, exist_ok=True)
        logger.log_info("local_bin_directory_created")
    except OSError as e:
        logger.log_exception(e, "local_bin_directory_creation_failed")
        output.error(
            f"Cannot create {local_bin_dir} directory: {e}", logger=logger
        )
        output.info("Try: Check home directory permissions", emoji="💡")
        raise

    # Determine source directory
    # Assuming we're in the dotfiles directory or can find it via path resolution
    # Get the project root by finding where local_bin/ directory exists
    dotfiles_dir = Path(__file__).parent.parent.parent  # Go up from src/dotfiles/
    source_dir = dotfiles_dir / "local_bin"
    logger = logger.bind(source_dir=source_dir, dotfiles_dir=dotfiles_dir)

    # Handle "*" pattern (all files) or specific file list
    if "*" in self.config.local_bin_files:
        # Link all files in local_bin/
        if not source_dir.exists():
            logger.log_warning("local_bin_source_not_found")
            output.warning(
                f"local_bin directory not found: {source_dir}", logger=logger
            )
            return

        try:
            files_to_link = [f.name for f in source_dir.iterdir() if f.is_file()]
            logger = logger.bind(files_count=len(files_to_link), files=files_to_link)
            logger.log_info("local_bin_files_discovered")
        except OSError as e:
            logger.log_exception(e, "local_bin_directory_read_failed")
            output.error(f"Cannot read local_bin directory: {e}", logger=logger)
            return
    else:
        # Link only specified files
        files_to_link = self.config.local_bin_files
        logger = logger.bind(files_count=len(files_to_link), files=files_to_link)
        logger.log_info("local_bin_files_from_config")

    if not files_to_link:
        output.success("No files to link in local_bin/", logger=logger)
        return

    # Link each file
    for filename in files_to_link:
        source_path = source_dir / filename
        target_path = local_bin_dir / filename
        logger_bound = logger.bind(
            filename=filename, source_path=source_path, target_path=target_path
        )

        # Check if source exists
        if not source_path.exists():
            logger_bound.log_warning("local_bin_source_file_not_found")
            output.warning(f"Source file not found: {source_path}", logger=logger_bound)
            continue

        # Check if target already exists
        if target_path.exists():
            if target_path.is_symlink():
                # Check if it points to the right place
                try:
                    current_target = os.readlink(target_path)
                    if Path(current_target) == source_path:
                        logger_bound.log_info("local_bin_link_already_correct")
                        output.success(
                            f"{filename} already correctly linked", logger=logger_bound
                        )
                    else:
                        logger_bound = logger_bound.bind(current_target=current_target)
                        logger_bound.log_warning("local_bin_link_incorrect_target")
                        output.warning(
                            f"{filename} is linked to {current_target}, but should link to {source_path}",
                            logger=logger_bound,
                        )
                except OSError as e:
                    logger_bound.log_exception(e, "local_bin_readlink_failed")
                    output.warning(
                        f"Cannot read symlink for {filename}: {e}", logger=logger_bound
                    )
            else:
                # It's a regular file - conflict!
                logger_bound.log_warning("local_bin_file_conflict")
                output.warning(
                    f"{filename} exists as a regular file in ~/.local/bin, skipping symlink",
                    logger=logger_bound,
                )
        else:
            # Create the symlink
            try:
                os.symlink(source_path, target_path)
                logger_bound.log_info("local_bin_link_created")
                output.success(f"Linked {filename}", logger=logger_bound)
                self.restart_required = True
            except OSError as e:
                logger_bound.log_exception(e, "local_bin_symlink_creation_failed")
                output.error(f"Failed to link {filename}: {e}", logger=logger_bound)
                output.info("Try: Check permissions on ~/.local/bin", emoji="💡")
                continue
```

**Step 2: Run compilation test**

Run: `make test-compile`
Expected: PASS

**Step 3: Commit implementation**

```bash
git add src/dotfiles/init.py
git commit -m "feat: implement link_local_bin method for symlinking scripts"
```

---

## Task 3: Integrate into Installation Flow

**Files:**

- Modify: `src/dotfiles/init.py:1767-1791` (main function steps)

**Step 1: Add link_local_bin step to installation flow**

In the `main()` function, add the new step after "Linking configurations":

```python
steps: list[tuple[str, Callable[[LoggingHelpers], None | bool]]] = [
    (
        "Installing dependencies",
        lambda logger: operating_system.install_dependencies(logger, output),
    ),
    (
        "Linking configurations",
        lambda logger: operating_system.link_configs(logger, output),
    ),
    (
        "Linking local bin scripts",
        lambda logger: operating_system.link_local_bin(logger, output),
    ),
    (
        "Validating git credential helper",
        lambda logger: operating_system.validate_git_credential_helper(
            logger, output
        ),
    ),
    (
        "Setting up shell",
        lambda logger: operating_system.setup_shell(logger, output),
    ),
    (
        "Setting up accounts",
        lambda logger: operating_system.link_accounts(logger, output),
    ),
]
```

**Step 2: Run compilation test**

Run: `make test-compile`
Expected: PASS

**Step 3: Commit integration**

```bash
git add src/dotfiles/init.py
git commit -m "feat: integrate link_local_bin into installation flow"
```

---

## Task 4: Manual Testing

**Files:**

- No file changes, testing only

**Step 1: Test with existing local_bin/run-claude.sh**

Run the init script and verify symlinks are created:

```bash
# Run init (use minimal environment, no-remote to avoid side effects)
export DOTFILES_ENVIRONMENT=minimal
uv run dotfiles-init --no-remote

# Verify symlink was created
ls -la ~/.local/bin/run-claude.sh
```

Expected output: Symlink pointing to `/home/do3cc/projects/dotfiles/local_bin/run-claude.sh`

**Step 2: Test idempotency (re-run init)**

```bash
# Re-run init
uv run dotfiles-init --no-remote
```

Expected: Should report "run-claude.sh already correctly linked" without errors

**Step 3: Test conflict detection**

```bash
# Create a regular file that conflicts
echo "test" > ~/.local/bin/test-conflict.sh

# Create matching file in local_bin
echo "original" > local_bin/test-conflict.sh

# Run init
uv run dotfiles-init --no-remote
```

Expected: Should warn about conflict and skip creating symlink

**Step 4: Clean up test files**

```bash
rm ~/.local/bin/test-conflict.sh
rm local_bin/test-conflict.sh
```

**Step 5: Document test results**

Create a commit message summarizing test results:

```bash
# No files to commit, but document in commit message for next commit
# or create a test log if needed
```

---

## Task 5: Run Pre-commit Checks

**Files:**

- All modified files

**Step 1: Run pre-commit on all changed files**

```bash
pre-commit run --files src/dotfiles/init.py
```

Expected: All checks pass (markdownlint, pyright, ruff, etc.)

**Step 2: Fix any issues**

If pre-commit finds issues, fix them and re-run:

```bash
# Fix issues manually or use auto-fixers
ruff check --fix src/dotfiles/init.py
pyright src/dotfiles/init.py

# Re-run pre-commit
pre-commit run --files src/dotfiles/init.py
```

**Step 3: Commit any formatting fixes**

```bash
git add src/dotfiles/init.py
git commit -m "style: apply pre-commit fixes to init.py"
```

---

## Task 6: Final Verification

**Files:**

- No file changes

**Step 1: Run full compilation test**

```bash
make test-compile
```

Expected: PASS

**Step 2: Verify git status is clean**

```bash
git status
```

Expected: All changes committed, working tree clean

**Step 3: Review commit history**

```bash
git log --oneline origin/main..HEAD
```

Expected: Should see 3-4 commits following conventional commit format

---

## Next Steps

After completing this plan:

1. **Push branch**: `git push -u origin feature/link-local-bin`
2. **Create PR**: Use `gh pr create` or GitHub web interface
3. **Request review**: Tag appropriate reviewers
4. **Integration testing**: Run `make test` to test on all container environments (optional but recommended)

## References

- **Existing patterns**: See `link_configs()` method in `src/dotfiles/init.py:279-377`
- **Error handling**: Follow patterns in `install_dependencies()` for comprehensive logging
- **Output formatting**: Use `ConsoleOutput` class methods (success, error, warning, info)
- **Logging**: Use event-based logging with `logger.log_info()`, `logger.log_warning()`, `logger.log_exception()`
