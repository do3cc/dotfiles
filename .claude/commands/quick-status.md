---
description: Quick status check - just the essentials for immediate decision making
allowed-tools: ["Bash"]
---

Provide a quick, actionable status summary focusing on immediate priorities.

Run `uv run dotfiles-status --no-github` for fast local analysis and present only:

1. **Immediate Action Items** (top 3 priorities)
2. **Uncommitted Work** (worktrees that need attention)
3. **Ready to Merge** (branches that look complete)
4. **Next Recommended Task** (based on current state)

Keep it concise - max 10 lines. Focus on what to do next, not comprehensive analysis.
