function wt-clean --description "Cleanup merged and stale worktrees"
    echo "Pruning removed worktrees..."
    git worktree prune

    echo ""
    echo "Current worktrees (excluding main):"
    # The first entry is the main worktree
    git worktree list | tail -n +2

    echo ""
    echo "To remove a worktree: git worktree remove <path>"
    echo "To remove a worktree safely: wt-remove <name>"
end
