# Dotfiles

Personal dotfiles repository for Linux systems (primarily Arch/Garuda) containing configuration files for development tools and shell environments.

## Quick Start

```bash
# Install everything
uv run init.py

# Work environment with additional packages
uv run init.py --environment work

# Private environment with full setup
uv run init.py --environment private
```

## Package Management

This repository includes **swman** (Software Manager Orchestrator), a unified interface to manage updates across multiple package managers:

```bash
# Check status across all package managers
python swman.py --check

# Update system packages (pacman, yay)
python swman.py --system

# Update development tools (uv tools)
python swman.py --tools

# Update plugins (neovim, fish shell)
python swman.py --plugins

# Update everything
python swman.py --all

# Preview changes without applying
python swman.py --all --dry-run
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

## Commit Guidelines

**Always use `cog commit` instead of `git commit`** for conventional commits with automatic changelog generation.

## Architecture

The installation system (`init.py`) detects the operating system and:
- Installs packages via system package managers
- Creates configuration symlinks
- Sets up development environments
- Configures authentication for services

Supports Arch/Garuda (pacman/yay) and Debian-based systems (apt).