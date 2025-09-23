# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a personal dotfiles repository for Linux systems (primarily Arch/Garuda) containing configuration files for development tools and shell environments. The repository is structured to support multiple Linux distributions through a Python-based installation system.

## Installation and Setup

The main installation script is `init.py`, which:
- Detects the operating system (supports Arch/Garuda and Debian-based systems)
- Installs required packages via package managers (pacman/yay for Arch, apt for Debian)
- Creates symlinks for configuration directories to `~/.config/`
- Sets up development tools like NVM and Pyenv
- Configures authentication for GitHub and Tailscale

To run the installation:
```bash
uv run init.py
```

With environment options:
```bash
# Minimal environment (default)
uv run init.py

# Work environment
uv run init.py --environment work

# Private environment
uv run init.py --environment private
```

The script handles:
- Package installation (see `pacman_packages` and `apt_packages` lists in init.py)
- Configuration linking for: alacritty, direnv, fish, irssi, nvim, tmux, byobu, git
- Shell setup (defaults to fish shell)
- SSH key generation and GitHub authentication
- Tailscale setup

## Architecture

### Configuration Structure
- Each major tool has its own directory (e.g., `alacritty/`, `fish/`, `tmux/`)
- Configurations are symlinked to appropriate locations in `~/.config/`
- The `lazy_nvim/` directory contains a LazyVim-based Neovim configuration

### Key Components

**Fish Shell (`fish/`)**:
- Main config in `config.fish` with starship prompt, direnv integration
- Custom functions for Git shortcuts and tool integration
- NVM integration for Node.js version management

**Neovim (`lazy_nvim/`)**:
- LazyVim-based configuration with plugin management
- Configuration split into `config/` (core settings) and `plugins/` (plugin configurations)

**Tmux (`tmux/`)**:
- Extensive key bindings for pane/window management
- Vim-tmux integration for seamless navigation
- Plugin system with resurrect/continuum for session persistence

**Terminal (`alacritty/`)**:
- Comprehensive theme collection in `themes/` directory
- Main configuration in `alacritty.toml`

### Development Environment
- Primary shell: Fish with starship prompt
- Editor: Neovim with LazyVim
- Terminal multiplexer: Tmux with custom key bindings
- Terminal emulator: Alacritty
- Version managers: NVM (Node.js), Pyenv (Python)
- Package managers: UV (Python), NPM/Yarn (Node.js)

## Commit Guidelines

- **ALWAYS use `cog commit` instead of `git commit`** for creating commits
- This repository uses conventional commits with cog for automatic changelog generation
- When creating commits, use the interactive `cog commit` command to ensure proper formatting

## Package Management

The repository includes **swman.py** (Software Manager Orchestrator), a unified tool for managing updates across multiple package managers:

```bash
# Check for updates across all systems
python swman.py --check

# Update specific categories
python swman.py --system    # pacman, yay
python swman.py --tools     # uv tools
python swman.py --plugins   # neovim, fish plugins

# Update everything with preview
python swman.py --all --dry-run
```

Supported managers: pacman, yay, uv-tools, lazy.nvim, fisher

## Important Notes

- The system assumes XDG base directory compliance
- Configuration files are designed for Wayland environments (Hyprland)
- Git configuration includes global gitignore patterns
- Shell integration includes direnv for project-specific environments
- SSH key rotation is automated (monthly keys based on hostname)