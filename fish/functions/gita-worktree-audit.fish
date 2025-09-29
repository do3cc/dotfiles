function gita-worktree-audit --description "Full analysis and reporting of worktree repositories"
    echo "🔍 Comprehensive Worktree Audit"
    echo "==============================="

    # Get all repositories with worktrees
    set --local repos (gita-repo-discovery)
    set --local worktree_repos
    set --local total_worktrees 0
    set --local repos_with_issues 0

    for repo in $repos
        if gita-worktree-detect $repo
            set --append worktree_repos $repo
        end
    end

    if test (count $worktree_repos) -eq 0
        echo ""
        echo "No gita repositories with worktrees found."
        return 0
    end

    # Audit each repository
    for repo in $worktree_repos
        echo ""
        echo "Repository: $repo"
        echo "$(string repeat - (math 12 + (string length $repo)))"

        gita-worktree-audit-repo $repo

        # Check if repository has issues
        set --local issues (gita-worktree-detect-issues $repo)
        if test (count $issues) -gt 0
            set repos_with_issues (math $repos_with_issues + 1)
        end
    end

    # Summary statistics
    echo ""
    echo "📊 Audit Summary"
    echo "================"
    echo "  Total repositories with worktrees: "(count $worktree_repos)
    echo "  Repositories needing attention:    $repos_with_issues"
    echo "  Repositories in good condition:    "(math (count $worktree_repos) - $repos_with_issues)

    if test $repos_with_issues -gt 0
        echo ""
        echo "💡 Run 'gita-worktree-cleanup' to see specific cleanup actions."
    else
        echo ""
        echo "✨ All worktree repositories are in excellent condition!"
    end
end