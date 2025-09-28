---
description: Get comprehensive project status including GitHub issues, PRs, branches, and worktrees
allowed-tools: ["Bash", "Read"]
---

Please provide a comprehensive status overview of the dotfiles project including:

1. **GitHub Issues & Pull Requests**: Check open issues and PRs using the dotfiles-status tool
2. **Active Worktrees**: Show current worktree organization and any uncommitted work
3. **Branch Analysis**: Display active branches with ahead/behind status
4. **Work in Progress**: Highlight any immediate attention items

Use the dotfiles-status tool to gather this information and present it in a concise, actionable format that helps prioritize next steps.

Focus on:

- Issues that need immediate attention
- Worktrees with uncommitted changes
- Branches that are ready for merging or need syncing
- Any blocked or stale work

Run: `uv run dotfiles-status` to get the raw data, then summarize the key insights.
