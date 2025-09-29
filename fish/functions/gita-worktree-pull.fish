function gita-worktree-pull --description "Interactive pull operations for worktree repositories"
    echo "🔄 Interactive Worktree Pull"
    echo "============================"

    # Get all repositories with worktrees
    set --local repos (gita-repo-discovery)
    set --local worktree_repos

    for repo in $repos
        if gita-worktree-detect $repo
            set --append worktree_repos $repo
        end
    end

    if test (count $worktree_repos) -eq 0
        echo "No gita repositories with worktrees found."
        return 0
    end

    # Process each repository
    for repo in $worktree_repos
        echo ""
        echo "Repository: $repo"

        set --local behind_count (gita-check-behind $repo)
        if test "$behind_count" -gt 0 2>/dev/null
            echo "  Behind by $behind_count commits"
            read -P "  Pull changes? [y/N] " -l choice

            if test "$choice" = "y" -o "$choice" = "Y"
                echo "  Running: gita pull $repo"
                gita pull $repo
            else
                echo "  Skipped"
            end
        else
            echo "  Up to date"
        end
    end

    echo ""
    echo "Interactive pull completed."
end