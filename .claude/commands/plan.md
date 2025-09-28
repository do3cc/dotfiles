# Plan Command

**Usage**: `/plan <issue_number>`

**Description**: Automatically create an implementation plan for a GitHub issue by analyzing the issue, comments, and codebase.

## Implementation Prompt

When this command is executed, use the following comprehensive workflow:

```
I need to create an implementation plan for issue #{issue_number}. Please execute this automated workflow:

STEP 1: FETCH ISSUE DETAILS
- Use `gh api repos/:owner/:repo/issues/{issue_number}` to get issue details
- Extract title, description, labels, and current status
- Use `gh api repos/:owner/:repo/issues/{issue_number}/comments` to get all comments
- Analyze the full conversation thread for implementation insights

STEP 2: CREATE WORKTREE AND BRANCH
- Create new branch: `issue-{issue_number}-plan`
- Create feature worktree: `git worktree add worktrees/feature/issue-{issue_number}-plan issue-{issue_number}-plan`
- Navigate to the new worktree directory

STEP 3: CODEBASE ANALYSIS
- Analyze the current codebase to understand:
  - Existing architecture and patterns
  - Related files and components that might be affected
  - Dependencies and integration points
  - Testing patterns and requirements
- Use search tools (Grep, Glob) to understand relevant code sections

STEP 4: PLAN GENERATION
- Create file: `issue-{issue_number}-plan.md`
- Structure the plan with these sections:
  1. **Issue Summary** - Brief description from GitHub issue
  2. **Requirements Analysis** - What needs to be implemented based on issue and comments
  3. **Current State Analysis** - How the codebase currently works
  4. **Implementation Approach** - Detailed step-by-step implementation plan
  5. **Files to Modify** - List of files that need changes
  6. **Testing Strategy** - How to verify the implementation works
  7. **Dependencies** - Any prerequisites or blockers
  8. **Open Questions** - Identified questions or uncertainties

STEP 5: IDENTIFY OPEN QUESTIONS
- Review the plan and identify:
  - Technical uncertainties or ambiguities
  - Missing information from the issue description
  - Potential implementation conflicts or challenges
  - Areas requiring clarification or decision
- Add these to the "Open Questions" section with clear descriptions

STEP 6: COMMIT THE PLAN
- Stage the plan file: `git add issue-{issue_number}-plan.md`
- Create conventional commit: `git commit -m "feat: add implementation plan for issue #{issue_number}"`
- Include proper co-authoring with Claude

STEP 7: COMPLETION REPORT
- Provide summary of the created plan
- List the main implementation steps identified
- Highlight any critical open questions that need resolution
- Suggest next steps for proceeding with implementation

Please execute this workflow for issue #{issue_number} now.
```

## Workflow

The command performs the following automated steps:

1. **Fetch Issue Details**: Get issue and all comments from GitHub API
2. **Create Worktree**: New feature worktree with `issue-{number}-plan` branch
3. **Codebase Analysis**: Understand current architecture and affected components
4. **Plan Generation**: Create comprehensive `issue-{number}-plan.md` file
5. **Identify Open Questions**: Add uncertainties and clarifications needed
6. **Commit Plan**: Save the plan with conventional commit format

## Input Parameters

- `issue_number`: The GitHub issue number (e.g., `7` for issue #7)

## Prerequisites

- GitHub CLI (`gh`) configured with repository access
- Working git repository with proper remotes configured
- Issue must exist and be accessible in the repository

## Plan File Structure

The generated plan file includes:

- **Issue Summary**: Brief description from GitHub
- **Requirements Analysis**: Implementation requirements from issue and comments
- **Current State Analysis**: How codebase currently works
- **Implementation Approach**: Detailed step-by-step plan
- **Files to Modify**: List of files needing changes
- **Testing Strategy**: Verification approach
- **Dependencies**: Prerequisites and blockers
- **Open Questions**: Uncertainties requiring clarification

## Error Handling

- **Issue not found**: Command will report error and suggest checking issue number
- **GitHub API issues**: Command will attempt retry or suggest manual lookup
- **Worktree conflicts**: Command will handle existing worktrees appropriately
- **Branch exists**: Command will either use existing or create new variant

## Output

- New worktree created in `worktrees/feature/issue-{number}-plan/`
- Comprehensive implementation plan file
- Committed plan ready for review and implementation
- Summary of identified open questions

## Example

```
/plan 7
```

This would:

1. Fetch issue #7 details and all comments from GitHub
2. Create worktree `worktrees/feature/issue-7-plan/`
3. Analyze codebase for logging-related components
4. Generate `issue-7-plan.md` with comprehensive implementation plan
5. Identify open questions about logging architecture
6. Commit the plan with conventional commit format

## Integration

This command integrates with:

- GitHub CLI for issue and comment fetching
- Git worktree management for isolated planning
- Codebase analysis tools (Grep, Glob, Read)
- Conventional commit standards
- Repository file patterns and conventions
