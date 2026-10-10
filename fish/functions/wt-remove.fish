function wt-remove --description "Safely remove a worktree after checking for uncommitted work"
    if test (count $argv) -eq 0
        echo "Usage: wt-remove <worktree-name>"
        echo "Example: wt-remove issue-25-logging"
        wt-list
        return 1
    end

    set -l root (_wt_root)
    or begin
        echo "Error: Not in a git repository"
        return 1
    end

    if not test -d "$root/.worktrees"
        echo "No worktrees yet. Create one with: wt-new <type> <name>"
        return 1
    end

    set -l target $argv[1]
    set -l found (find "$root/.worktrees" -name "*$target*" -type d 2>/dev/null | head -1)

    if test -z "$found"
        echo "Worktree matching '$target' not found"
        wt-list
        return 1
    end

    echo "Checking worktree: $found"

    # Check for uncommitted changes
    if git -C "$found" status --porcelain | grep -q .
        echo "⚠️  Warning: Worktree has uncommitted changes:"
        git -C "$found" status --short
        echo ""
        echo "Please commit or stash changes before removing:"
        echo "  git add . && git commit -m \"Save work before removing worktree\""
        echo "  git stash push -m \"Work in progress\""
        return 1
    end

    echo "Removing clean worktree: $found"
    git worktree remove "$found"

    if test $status -eq 0
        echo "✅ Successfully removed worktree: $found"
    else
        echo "❌ Failed to remove worktree: $found"
        return 1
    end
end
