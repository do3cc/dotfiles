function gita-worktree-check --description "Silent background worktree maintenance check"
    # Only run if gita is available
    if not command -q gita
        return 0
    end

    # Get all gita-managed repositories
    set --local repos (gita-repo-discovery)
    if test $status -ne 0
        return 0
    end

    set --local issues_found false
    set --local blacklist_file ~/.config/gita-worktree-blacklist

    # Start background fetch for all repositories
    gita-batch-fetch --silent &

    for repo in $repos
        # Skip blacklisted repositories
        if test -f $blacklist_file
            if grep -q "^$repo\$" $blacklist_file 2>/dev/null
                continue
            end
        end

        # Skip repositories without worktrees
        if not gita-worktree-detect $repo
            continue
        end

        # Check for issues (merged branches, stale worktrees)
        set --local issues (gita-worktree-detect-issues $repo)
        if test (count $issues) -gt 0
            if not $issues_found
                echo "🔧 Worktree maintenance suggestions:"
                set issues_found true
            end

            echo "  Repository: $repo"
            for issue in $issues
                echo "    $issue"
            end
        end
    end

    # Wait for background fetches to complete
    wait

    return 0
end