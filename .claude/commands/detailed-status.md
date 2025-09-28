---
description: Get detailed project status with optional filtering (usage: /detailed-status [github|local|worktrees|branches])
allowed-tools: ["Bash", "Read", "Grep"]
---

Provide a detailed status report for the dotfiles project.

$1 parameter options:

- `github`: Focus on GitHub issues and pull requests only
- `local`: Focus on local branches and worktrees only
- `worktrees`: Deep dive into worktree organization and status
- `branches`: Analyze branch relationships and sync status
- (no parameter): Full comprehensive status

Please run the appropriate commands based on the requested scope:

For GitHub focus: `uv run dotfiles-status --json` and analyze issues/PRs
For local focus: `uv run dotfiles-status --no-github` and analyze branches/worktrees
For full status: `uv run dotfiles-status` and provide complete analysis

Present the information with:

- Clear prioritization of items needing attention
- Specific action recommendations
- Context about relationships between issues, branches, and worktrees
- Any potential blockers or dependencies

Requested scope: $ARGUMENTS
