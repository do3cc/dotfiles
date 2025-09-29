function gita-worktree-audit-repo --description "Audit a single repository's worktree status"
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

    # Count worktrees and analyze
    set --local worktree_list (git worktree list 2>/dev/null)
    set --local worktree_count (echo "$worktree_list" | wc -l)
    set --local additional_worktrees (math $worktree_count - 1)

    echo "  📊 $additional_worktrees worktrees total"

    # Analyze each worktree
    set --local behind_count 0
    set --local uncommitted_count 0
    set --local stale_count 0
    set --local healthy_count 0

    set --local worktree_paths (echo "$worktree_list" | awk '{print $1}' | tail -n +2)
    for worktree_path in $worktree_paths
        if test -d "$worktree_path"
            pushd "$worktree_path" >/dev/null 2>&1
            if test $status -eq 0
                set --local is_healthy true

                # Check if behind main
                set --local behind (git rev-list --count HEAD..main 2>/dev/null)
                if test "$behind" -gt 0 2>/dev/null
                    set behind_count (math $behind_count + 1)
                    set is_healthy false
                end

                # Check for uncommitted changes
                if not git diff-index --quiet HEAD 2>/dev/null
                    set uncommitted_count (math $uncommitted_count + 1)
                    set is_healthy false
                end

                if test $is_healthy = true
                    set healthy_count (math $healthy_count + 1)
                end

                popd >/dev/null 2>&1
            end
        else
            set stale_count (math $stale_count + 1)
        end
    end

    popd >/dev/null 2>&1

    # Report findings
    set --local issues_total (math $behind_count + $uncommitted_count + $stale_count)

    if test $issues_total -eq 0
        echo "  ✅ All worktrees healthy"
    else
        echo "  ⚠️  $issues_total worktrees need attention"
        if test $behind_count -gt 0
            echo "    • $behind_count behind main"
        end
        if test $uncommitted_count -gt 0
            echo "    • $uncommitted_count with uncommitted changes"
        end
        if test $stale_count -gt 0
            echo "    • $stale_count stale references"
        end
    end

    # Show cleanup actions available
    set --local cleanup_actions (gita-worktree-detect-issues $repo_name | wc -l)
    if test $cleanup_actions -gt 0
        echo "  🔧 $cleanup_actions cleanup actions available"
    end

    return 0
end