function wt-clean --description "Cleanup merged and stale worktrees"
    echo "Pruning removed worktrees..."
    git worktree prune

    echo ""
    echo "Current worktrees (excluding main):"
    git worktree list | grep -v "main"

    echo ""
    echo "To remove a worktree: git worktree remove <path>"
    echo "To remove a worktree safely: wt-remove <name>"
end