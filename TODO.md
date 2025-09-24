# TODOS

- ✅ COMPLETED: Created pkgstatus tool - Fish shell startup integration that shows package updates, git status, and init script status with intelligent caching. Implemented as Python backend with Fish wrapper for maintainability.
- ✅ COMPLETED: Resolved ruff and pyright unused variable conflicts by using single underscore (_) for unused exception variables and subprocess results. Both tools respect this convention without requiring configuration changes.
- ✅ COMPLETED: Fixed markdown MD013 warning in LazyVim
- There is a false error shown in lazyvim about urllib.error from pyright, that it is possible unbound. Please think hard and analyze this.multiple
- ✅ COMPLETED: Implemented structlog across all Python tools (init.py, swman.py, pkgstatus.py) with central JSON logging to ~/.cache/dotfiles/logs/dotfiles.log. Added context binding for operation tracking and log_unused_variables() helper for linter-friendly variable logging. Configured automatic log rotation (10MB, 5 backups) and documented requirements in CLAUDE.md for future tools.
- ✅ COMPLETED: Switched to permanent SSH keys instead of monthly rotation. Keys now use format `id_ed25519_hostname_environment` (e.g., `id_ed25519_myhost_private`) eliminating deployment burden while maintaining per-system/environment isolation. This reduces operational overhead without meaningful security trade-offs since Ed25519 keys are computationally secure for decades.
- Check github failures
- ✅ COMPLETED: Updated swman to show full package manager output instead of hiding it. All package update operations (pacman, yay, uv tools, lazy.nvim, fisher) now display real-time progress using streaming subprocess calls instead of capture_output=True.
