# Implement Command

**Usage**: `/implement <issue_number>`

**Description**: Automatically implement an issue based on an existing implementation plan in a worktree.

## Implementation Prompt

When this command is executed, use the following comprehensive workflow:

```
I need to implement issue #{issue_number} following the existing plan. Please execute this automated workflow:

STEP 1: LOCATE WORKTREE
- Find the worktree for issue #{issue_number} by checking `git worktree list`
- Look for patterns like `issue-{issue_number}-*` in worktree names
- If multiple matches, prioritize `review/` or `feature/` directories
- If no worktree found, list available worktrees and error

STEP 2: NAVIGATE AND STATUS CHECK
- Navigate to the identified worktree directory
- Check git status and current branch
- Verify we're on the correct issue branch

STEP 3: SYNC WITH MAIN
- Fetch latest changes: `git fetch origin main`
- Check if branch is behind main: `git rev-list --count HEAD..origin/main`
- If behind, rebase onto main: `git rebase origin/main`
- Handle any rebase conflicts if they occur

STEP 4: PLAN VALIDATION
- Look for implementation plan files (e.g., `issue-{issue_number}-plan.md`, `issue-{issue_number}-updated-plan.md`)
- Read the plan and analyze if it needs updates based on current codebase state
- If plan needs updates, modify it accordingly
- Verify all prerequisites mentioned in the plan are satisfied

STEP 5: IMPLEMENTATION EXECUTION
- Follow the plan step by step, creating todo items for tracking
- For each step in the plan:
  - Mark as in_progress
  - Execute the required changes (file edits, additions, etc.)
  - Mark as completed when done
- Run pre-commit checks after each significant change
- Run `make test-compile` to ensure functionality

STEP 6: QUALITY ASSURANCE
- Run full pre-commit checks on all modified files
- Execute `make test-compile` to verify all tools work
- Test any specific functionality mentioned in the plan
- Verify no regressions were introduced

STEP 7: CLEANUP PLAN FILES
- Remove implementation plan files (e.g., `issue-{issue_number}-plan.md`, `issue-{issue_number}-updated-plan.md`)
- These are no longer needed once implementation is complete
- Stage the removal of these files

STEP 8: COMMIT CHANGES
- Stage all implementation changes and plan file removals
- Create a conventional commit following the repository standards
- Include proper co-authoring with Claude
- Reference the issue number and plan in commit message

STEP 9: CREATE PULL REQUEST
- Push the branch to origin
- Create a comprehensive PR using `gh pr create`
- Include implementation summary, changes made, testing performed
- Reference the original issue and implementation plan

STEP 10: COMPLETION REPORT
- Provide summary of what was implemented
- List all files that were modified
- Include link to created PR
- Report any issues or deviations from the plan

Please execute this workflow for issue #{issue_number} now.
```

## Workflow

The command performs the following automated steps:

1. **Find Existing Worktree**: Locate the worktree for the given issue number
2. **Check Branch Status**: Verify if the branch is up to date with main
3. **Rebase if Needed**: Automatically rebase the branch if it's behind main
4. **Plan Validation**: Check if the implementation plan needs updates
5. **Implementation**: Execute the plan step by step
6. **Quality Assurance**: Run pre-commit checks and tests
7. **Cleanup Plan Files**: Remove implementation plan files (no longer needed)
8. **Commit Changes**: Create a conventional commit with proper formatting
9. **Create Pull Request**: Generate a comprehensive PR with implementation details

## Input Parameters

- `issue_number`: The GitHub issue number (e.g., `7` for issue #7)

## Prerequisites

- Issue worktree must exist (typically in `worktrees/review/issue-X-*` or `worktrees/feature/issue-X-*`)
- Implementation plan file must exist in the worktree (e.g., `issue-X-plan.md` or `issue-X-updated-plan.md`)
- Working git repository with proper remotes configured

## Error Handling

- **No worktree found**: Command will list available worktrees and suggest creating one
- **No plan found**: Command will prompt to create a plan first using `/plan` command
- **Branch conflicts**: Command will attempt automatic resolution or prompt for manual intervention
- **Test failures**: Command will report failures and halt implementation

## Output

- Real-time progress updates during each step
- Summary of changes made
- Link to created pull request
- Test results and quality metrics

## Example

```
/implement 7
```

This would:

1. Find worktree for issue #7 (e.g., `worktrees/review/issue-7-logging-refactor`)
2. Navigate to the worktree
3. Check if branch is up to date with main
4. Read and validate the implementation plan
5. Execute each step in the plan
6. Run tests and quality checks
7. Commit changes with conventional commit format
8. Create pull request with comprehensive description

## Integration

This command integrates with:

- Git worktree management
- GitHub CLI for issue lookup and PR creation
- Pre-commit hooks for code quality
- Project test suite (`make test-compile`)
- Conventional commit standards
