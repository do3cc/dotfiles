function gita-worktree-cleanup --description "Show cleanup commands for worktree repositories"
    echo "🧹 Worktree Cleanup Analysis"
    echo "============================"

    # Get all repositories with worktrees
    set --local repos (gita-repo-discovery)
    set --local cleanup_found false

    for repo in $repos
        if not gita-worktree-detect $repo
            continue
        end

        # Get cleanup suggestions for this repository
        set --local issues (gita-worktree-detect-issues $repo)
        if test (count $issues) -gt 0
            if not $cleanup_found
                set cleanup_found true
            end

            echo ""
            echo "Repository: $repo"
            echo "$(string repeat - (math 12 + (string length $repo)))"

            for issue in $issues
                echo "  $issue"
            end
        end
    end

    if not $cleanup_found
        echo ""
        echo "✨ No cleanup actions needed. All worktree repositories are clean!"
    else
        echo ""
        echo "💡 Run the suggested commands above to clean up your worktrees."
        echo "   Review each command carefully before executing."
    end
end