# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a personal dotfiles repository for Linux systems (primarily Arch/Garuda) containing configuration files for development tools and shell environments. The repository is structured to support multiple Linux distributions through a Python-based installation system.

## Installation and Setup

This repository is structured as a Python package with entry points for all tools. First, install the project dependencies:

```bash
# Install the project and its dependencies
uv sync
```

### Main Installation Script

The main installation script detects the operating system and sets up the entire environment:

```bash
# Using the entry point (recommended)
uv run dotfiles-init

# Or directly (legacy)
uv run init.py
```

**Environment Configuration:**
The script requires the `DOTFILES_ENVIRONMENT` environment variable to be set:

```bash
# Minimal environment (default)
export DOTFILES_ENVIRONMENT=minimal && uv run dotfiles-init

# Work environment
export DOTFILES_ENVIRONMENT=work && uv run dotfiles-init

# Private environment
export DOTFILES_ENVIRONMENT=private && uv run dotfiles-init

# Test mode (skip remote activities)
export DOTFILES_ENVIRONMENT=minimal && uv run dotfiles-init --test
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

## Python Tools and Entry Points

The repository includes several Python tools accessible via entry points:

### Software Manager Orchestrator (swman)
Unified tool for managing updates across multiple package managers:

```bash
# Using entry point (recommended)
uv run dotfiles-swman --check

# Update specific categories
uv run dotfiles-swman --system    # pacman, yay
uv run dotfiles-swman --tools     # uv tools
uv run dotfiles-swman --plugins   # neovim, fish plugins

# Update everything with preview
uv run dotfiles-swman --all --dry-run

# Legacy direct execution
./swman.py --check
```

### Package Status Checker (pkgstatus)
System status monitoring for packages, git, and init script status:

```bash
# Using entry point (recommended)
uv run dotfiles-pkgstatus --quiet

# JSON output
uv run dotfiles-pkgstatus --json

# Force cache refresh
uv run dotfiles-pkgstatus --refresh

# Legacy direct execution
./pkgstatus.py --quiet
```

**Supported package managers:** pacman, yay, uv-tools, lazy.nvim, fisher

## Logging Requirements for Python Tools

All Python tools in this repository must use structured logging via the shared `logging_config.py` module:

### Standard Setup
```python
from logging_config import setup_logging, bind_context, log_unused_variables

# Initialize logging with script name
logger = setup_logging("script_name")  # e.g. "init", "swman", "pkgstatus"
```

### Enhanced Logging Abstractions
The logging system provides comprehensive abstractions for production debugging:

- **`log_error()`, `log_warning()`, `log_info()`** - Simple severity-based logging
- **`log_progress()`** - Track operation progress and status
- **`log_subprocess_result()`** - Comprehensive command execution logging with stdout/stderr
- **`log_exception()`** - Full exception context with traceback information
- **`log_file_operation()`** - File system operations tracking
- **`log_package_operation()`** - Package manager operations logging

### Logging Conventions
- **JSON format**: All logs are structured JSON written to `~/.cache/dotfiles/logs/dotfiles.log`
- **User interaction**: Use `print()` for user-facing messages, logs are for debugging/monitoring
- **Context binding**: Use `bind_context()` to set operation-wide context variables
- **Unused variables**: Use `log_unused_variables(logger, **vars)` to capture variables that would otherwise trigger linter warnings
- **Global logger**: All abstractions automatically use the global logger set by `setup_logging()`

### Log File Management
- **Location**: `~/.cache/dotfiles/logs/dotfiles.log`
- **Rotation**: Automatic via Python's RotatingFileHandler (10MB, 5 backups)
- **Format**: JSON with timestamp, log level, message, context, and metadata

### Enhanced Logging Examples
```python
from logging_config import (
    setup_logging, bind_context,
    log_progress, log_error, log_subprocess_result, log_exception
)

# Initialize logging (sets global logger)
logger = setup_logging("mytool")
bind_context(environment="minimal", operation="check")

# Progress tracking
log_progress("starting package installation")

# Error logging with context
log_error("package not found", package="nonexistent", manager="pacman")

# Comprehensive subprocess logging (includes stdout/stderr)
result = subprocess.run(["pacman", "-Q", "git"], capture_output=True)
log_subprocess_result("check git package", ["pacman", "-Q", "git"], result)

# Exception logging with full context
try:
    risky_operation()
except Exception as e:
    log_exception(e, "package installation failed", package="problematic-pkg")
```

This enhanced logging provides complete observability into every operation, error, and progress step for production debugging.

## Important Notes

- The system assumes XDG base directory compliance
- Configuration files are designed for Wayland environments (Hyprland)
- Git configuration includes global gitignore patterns
- Shell integration includes direnv for project-specific environments
- SSH key rotation is automated (monthly keys based on hostname)