# TODOS

- ✅ COMPLETED: Created pkgstatus tool - Fish shell startup integration that shows package updates, git status, and init script status with intelligent caching. Implemented as Python backend with Fish wrapper for maintainability.
- Please have a look at the init script, ruff and pyright seem to have different definitions on what unused variables get ignored. Is there a way to use a variable name that both ruff and pyright ignore? I would like to avoid to configure ruff and pyright, but if needed, this can be done too. please think hard about it and only make a plan.
- Please make a plan for markdown MD013 warning that gets shown in lazyvim, I tried multiple fixes that seemed to work but the error is back
- There is a false error shown in lazyvim about urllib.error from pyright, that it is possible unbound. Please think hard and analyze this.multiple
- Please add structlog to all python tools and use a central log file to store information, use structlogs context heavily, especially to for currently unused variables that might make sense to add to the context of structlog in case of logging something. make a plan for it and also consider the best practices for log rotation. Help me understand what is the right way to tell you that all future tools in this project should use the central log. Tool, agent, local memory?
- I start to detest my solution for ssh keys, I keep rotating them manually, but it seems to be a burden. please think harder and tell me if this is a good idea or if there is a better solution that is commonly used. should I just dump it and stick to one permanent key for each system I use? The problem is that some of my systems do not know the new keys. I think automatic key deployment might actually be a liability
- Check github failures
