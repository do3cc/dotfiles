# Dotfiles

Personal dotfiles repository for Linux systems (primarily Arch/Garuda) containing configuration files for development tools and shell environments.

## Quick Start

First, install the project and its dependencies:

```bash
# Install project dependencies
uv sync
```

Then run the installation with the required environment variable:

```bash
# Minimal environment (default)
export DOTFILES_ENVIRONMENT=minimal && uv run dotfiles-init

# Work environment with additional packages
export DOTFILES_ENVIRONMENT=work && uv run dotfiles-init

# Private environment with full desktop setup
export DOTFILES_ENVIRONMENT=private && uv run dotfiles-init

# Test mode (skip remote activities like GitHub auth)
export DOTFILES_ENVIRONMENT=minimal && uv run dotfiles-init --no-remote
```

**Alternative using entry points:**

```bash
# Using the new entry points (recommended)
uv run dotfiles-init

# Or legacy direct execution
uv run init.py
```

## Package Management

This repository includes **swman** (Software Manager Orchestrator), a unified interface to manage updates across multiple package managers:

```bash
# Using entry points (recommended)
uv run dotfiles-swman --check              # Check status across all package managers
uv run dotfiles-swman --system             # Update system packages (pacman, yay)
uv run dotfiles-swman --tools              # Update development tools (uv tools)
uv run dotfiles-swman --plugins            # Update plugins (neovim, fish shell)
uv run dotfiles-swman --all                # Update everything
uv run dotfiles-swman --all --dry-run      # Preview changes without applying

# Legacy direct execution
./swman.py --check
./swman.py --system
./swman.py --all --dry-run
```

### Package Status Monitoring

The **pkgstatus** tool provides system status monitoring:

```bash
# Using entry points (recommended)
uv run dotfiles-pkgstatus --quiet          # Show only if issues exist
uv run dotfiles-pkgstatus --json           # JSON output format
uv run dotfiles-pkgstatus --refresh        # Force cache refresh

# Legacy direct execution
./pkgstatus.py --quiet
```

### Supported Package Managers

- **System**: pacman, yay (AUR)
- **Tools**: uv tools (Python development tools)
- **Plugins**: Lazy.nvim (Neovim), Fisher (Fish shell)

## Key Components

### Development Environment

- **Shell**: Fish with Starship prompt
- **Editor**: Neovim with LazyVim configuration
- **Version Managers**: NVM (Node.js), Pyenv (Python)

### Configuration Structure

- Each tool has its own directory (e.g., `ghostty/`, `fish/`)
- Configurations symlinked to `~/.config/`
- XDG Base Directory compliant
- Ghostty (`ghostty/config`, private environment) is the primary terminal; its
  splits and tabs replace tmux. `ghostty` is installed from the Arch repos only,
  as it is not packaged for Debian/Ubuntu.

## SSH Keys

`dotfiles-init` (step "link accounts", skipped with `--no-remote`) sets up one
SSH key per machine at the OpenSSH default path `~/.ssh/id_ed25519`:

1. Logs in to GitHub via `gh auth login` if needed, and refreshes the token with
   the `admin:public_key` scope.
2. Creates the key if it is missing (`ssh-keygen -t ed25519`, interactive, so
   you may set a passphrase or leave it empty). Host, email and environment are
   stored in the key comment.
3. Adds `Host *` / `AddKeysToAgent yes` to `~/.ssh/config` if `AddKeysToAgent`
   is not set anywhere there, so the first use caches the key in the agent.
4. Uploads the public key to GitHub with `gh ssh-key add`, titled
   `"<hostname> <environment>"`, unless `gh ssh-key list` already has it.

Every step is idempotent. Re-running init repairs a missing config entry or a
missing GitHub upload.

The `ssh-agent` is started by the fish plugin `danhper/fish-ssh-agent`
(`fish/conf.d/fish-ssh-agent.fish`), which keeps its environment in
`~/.ssh/environment`. No dotfiles code loads the key: with `AddKeysToAgent`
ssh asks for the passphrase once per agent lifetime.

Troubleshooting: `ssh-add -l` lists cached keys and `ssh -T git@github.com`
tests the connection.

## Syncthing

In the `private` environment `dotfiles-init`:

1. Installs the `syncthing` package (see `packages.yaml`).
2. Enables the packaged `syncthing.service` as a systemd user service.
3. Adds `#include dotfiles/syncthing/stignore` to `~/projects/.stignore`
   (keeping any lines already there). `.stignore` is per device and is not
   synced by Syncthing, so the shared ignore rules (`.git`, `.venv`,
   `.direnv`, caches, ...) live in `syncthing/stignore` in this repo.

Pairing devices and sharing the `~/projects` folder are still done in the web UI
(`http://127.0.0.1:8384`). Because `.git` is ignored, treat git as the transport
for repositories: commit and push before switching machines.

## Testing

### Quick Verification

```bash
make test-compile    # Fast compilation test (~10 seconds)
```

### Unit Tests

```bash
make test-unit       # uv run --group test pytest
```

Test dependencies (`pytest`, `pytest-cov`, `hypothesis`, `faker`) live in the
`test` dependency group, which a plain `uv sync` does not install. Use
`uv run --group test ...` to run them.

### Full Integration Testing

```bash
make test           # Test on all OS containers (Arch, Debian)
make test-arch      # Test Arch Linux only
make test-debian    # Test Debian only
```

### With Caching (Faster Development)

```bash
make cache-start    # Set up local build cache
make test           # Run tests with cache
make cache-stats    # Show cache statistics
```

## Commit Guidelines

**Always use `cog commit` instead of `git commit`** for conventional commits with automatic changelog generation.

## Architecture

The installation system (`init.py`) detects the operating system and:

- Installs packages via system package managers
- Creates configuration symlinks
- Sets up development environments
- Configures authentication for services

Supports Arch/Garuda (pacman/yay) and Debian-based systems (apt).

# Trigger PR update
