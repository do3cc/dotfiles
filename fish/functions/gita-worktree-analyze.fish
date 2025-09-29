function gita-worktree-analyze --description "Analyze worktree status for a repository"
    if test (count $argv) -eq 0
        return 1
    end

    set --local repo_name $argv[1]

    # Get repository path from gita
    set --local repo_path (gita ll $repo_name 2>/dev/null)
    if test $status -ne 0
        echo "  ❌ Repository not found in gita"
        return 1
    end

    # Change to repository directory
    pushd $repo_path >/dev/null 2>&1
    if test $status -ne 0
        echo "  ❌ Cannot access repository directory"
        return 1
    end

    # Count worktrees
    set --local worktree_count (git worktree list 2>/dev/null | wc -l)
    set --local additional_worktrees (math $worktree_count - 1)

    # Count worktrees behind main
    set --local behind_count 0
    set --local uncommitted_count 0

    set --local worktree_paths (git worktree list 2>/dev/null | awk '{print $1}' | tail -n +2)
    for worktree_path in $worktree_paths
        if test -d "$worktree_path"
            pushd "$worktree_path" >/dev/null 2>&1
            if test $status -eq 0
                # Check if behind main
                set --local behind (git rev-list --count HEAD..main 2>/dev/null)
                if test "$behind" -gt 0 2>/dev/null
                    set behind_count (math $behind_count + 1)
                end

                # Check for uncommitted changes
                if not git diff-index --quiet HEAD 2>/dev/null
                    set uncommitted_count (math $uncommitted_count + 1)
                end
                popd >/dev/null 2>&1
            end
        end
    end

    popd >/dev/null 2>&1

    # Display analysis
    if test $additional_worktrees -eq 0
        echo "  ❓ No additional worktrees found"
    else
        if test $behind_count -eq 0 -a $uncommitted_count -eq 0
            echo "  ✅ $additional_worktrees worktrees, all up to date and clean"
        else
            echo "  ⚠️  $additional_worktrees worktrees, $behind_count behind main, $uncommitted_count with uncommitted changes"
        end
    end

    return 0
end