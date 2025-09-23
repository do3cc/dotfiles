# TODOS

- ✅ COMPLETED: Created pkgstatus tool - Fish shell startup integration that shows package updates, git status, and init script status with intelligent caching. Implemented as Python backend with Fish wrapper for maintainability.
- ✅ COMPLETED: Resolved ruff and pyright unused variable conflicts by using single underscore (_) for unused exception variables and subprocess results. Both tools respect this convention without requiring configuration changes.
- ✅ COMPLETED: Fixed markdown MD013 warning in LazyVim
- There is a false error shown in lazyvim about urllib.error from pyright, that it is possible unbound. Please think hard and analyze this.multiple
- ✅ COMPLETED: Implemented structlog across all Python tools (init.py, swman.py, pkgstatus.py) with central JSON logging to ~/.cache/dotfiles/logs/dotfiles.log. Added context binding for operation tracking and log_unused_variables() helper for linter-friendly variable logging. Configured automatic log rotation (10MB, 5 backups) and documented requirements in CLAUDE.md for future tools.
- I start to detest my solution for ssh keys, I keep rotating them manually, but it seems to be a burden. please think harder and tell me if this is a good idea or if there is a better solution that is commonly used. should I just dump it and stick to one permanent key for each system I use? The problem is that some of my systems do not know the new keys. I think automatic key deployment might actually be a liability
- Check github failures
- Update swman program to give full output of the package update tools. I want to see it.
