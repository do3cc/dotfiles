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
- **Terminal**: Alacritty with comprehensive themes
- **Multiplexer**: Tmux with vim integration
- **Version Managers**: NVM (Node.js), Pyenv (Python)

### Configuration Structure

- Each tool has its own directory (e.g., `alacritty/`, `fish/`, `tmux/`)
- Configurations symlinked to `~/.config/`
- XDG Base Directory compliant

## Testing

### Quick Verification

```bash
make test-compile    # Fast compilation test (~10 seconds)
```

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
