---
description: Evaluate and label GitHub issues with complexity, plan status, and branch sync
tags: [project]
---

You are tasked with evaluating all open GitHub issues in this repository. For each issue:

## 1. Complexity Assessment

Add `complexity` label if missing (NEVER change existing complexity labels):

- **complexity: easy** - Simple, straightforward changes:
  - Documentation updates
  - Removing unused code
  - Simple configuration changes
  - Adding missing imports
  - Fixing typos or formatting
  - Quick one-file changes

- **complexity: medium** - Moderate complexity:
  - Refactoring with tests
  - Adding features to existing modules
  - Error handling improvements
  - Test suite additions
  - Multi-file coordinated changes

- **complexity: hard** - Complex implementation:
  - Architectural changes
  - New subsystems or modules
  - Complex algorithm implementations
  - Breaking API changes requiring migration
  - Cross-cutting concerns affecting many files

## 2. Plan Status Assessment

Determine if the issue has an implementation plan:

1. **Check for branch**: Use `gh api` to see if there's a branch for this issue (e.g., `issue-53-plan`, `issue-54-...`)
2. **Check for plan file**: If branch exists, check if it contains a plan file (usually `docs/issue-<number>-plan.md` or similar)
3. **Label accordingly**:
   - Add `has-plan` if branch exists with plan file
   - Add `needs-plan` if no branch or no plan file exists
4. **Remove opposite label** (if has-plan, remove needs-plan and vice versa)

## 3. Worktree and Branch Sync

For each issue that has a branch:

1. **Check worktree exists**: Use `git worktree list` to see if worktree already exists
2. **Create worktree if missing**:
   - Determine worktree type from branch name (feature/issue-X, bugfix/issue-X, etc.)
   - Create in appropriate `worktrees/` subdirectory: `git worktree add worktrees/<type>/issue-<number>-<description> <branch-name>`
3. **Ensure branch is up to date**:
   - Fetch latest: `git fetch origin`
   - Check if branch is behind origin/main: `git rev-list --count <branch>..origin/main`
   - If behind, report which branches need rebasing (DO NOT automatically rebase)

## 4. Output Format

Provide a summary table showing:

- Issue number and title
- Current complexity (or "ADDED: <complexity>" if just added)
- Plan status (has-plan/needs-plan)
- Branch status (none/exists/behind/up-to-date)
- Worktree status (none/exists/created)

Then provide actionable recommendations:

- Issues needing complexity labels
- Issues needing plan files
- Branches that need rebasing
- Any issues blocking progress

## Execution Steps

1. Fetch all open issues: `gh issue list --state open --json number,title,labels`
2. For each issue, check and update labels as needed
3. Check for branches: `gh api repos/:owner/:repo/branches`
4. For branches found, verify worktrees and sync status
5. Generate comprehensive report

Remember: DO NOT change existing complexity labels, only add them if missing.
