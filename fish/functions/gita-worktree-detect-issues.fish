function gita-worktree-detect-issues --description "Detect worktree maintenance issues for a repository"
    if test (count $argv) -eq 0
        return 1
    end

    set --local repo_name $argv[1]

    # Get repository path from gita
    set --local repo_path (gita ll $repo_name 2>/dev/null)
    if test $status -ne 0
        return 1
    end

    # Change to repository directory
    pushd $repo_path >/dev/null 2>&1
    if test $status -ne 0
        return 1
    end

    set --local issues

    # Check for merged branches that can be cleaned up
    set --local merged_branches (git branch --merged main 2>/dev/null | grep -v '^\*\|main' | string trim)
    for branch in $merged_branches
        if test -n "$branch"
            set --append issues "gita branch delete $repo_name $branch  # Merged branch can be cleaned up"
        end
    end

    # Check for worktrees with uncommitted changes
    set --local worktree_paths (git worktree list 2>/dev/null | awk '{print $1}' | tail -n +2)
    for worktree_path in $worktree_paths
        if test -d "$worktree_path"
            pushd "$worktree_path" >/dev/null 2>&1
            if test $status -eq 0
                # Check for uncommitted changes
                if not git diff-index --quiet HEAD 2>/dev/null
                    set --local worktree_branch (git branch --show-current 2>/dev/null)
                    set --append issues "Uncommitted changes in worktree: $worktree_path ($worktree_branch)"
                end

                # Check if worktree branch is behind main
                set --local behind_count (git rev-list --count HEAD..main 2>/dev/null)
                if test "$behind_count" -gt 0 2>/dev/null
                    set --local worktree_branch (git branch --show-current 2>/dev/null)
                    set --append issues "Worktree behind main by $behind_count commits: $worktree_path ($worktree_branch)"
                end
                popd >/dev/null 2>&1
            end
        else
            set --append issues "gita worktree prune $repo_name  # Remove stale worktree reference: $worktree_path"
        end
    end

    popd >/dev/null 2>&1

    # Output issues
    for issue in $issues
        echo $issue
    end

    return 0
end