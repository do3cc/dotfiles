function gita-worktree-status --description "Detailed status of all gita repos with worktrees"
    echo "📊 Worktree Status Report"
    echo "========================"

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

    # Show detailed status for each repository
    for repo in $worktree_repos
        echo ""
        echo "Repository: $repo"
        echo "$(string repeat - (math 12 + (string length $repo)))"

        gita-worktree-analyze $repo
    end

    echo ""
    echo "Summary: "(count $worktree_repos)" repositories using worktrees"
end