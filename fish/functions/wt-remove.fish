function wt-remove --description "Safely remove a worktree after checking for uncommitted work"
    if test (count $argv) -eq 0
        echo "Usage: wt-remove <worktree-name>"
        echo "Example: wt-remove issue-25-logging"
        wt-list
        return 1
    end

    set target $argv[1]
    set found (find worktrees -name "*$target*" -type d 2>/dev/null | head -1)

    if test -z "$found"
        echo "Worktree matching '$target' not found"
        wt-list
        return 1
    end

    echo "Checking worktree: $found"

    # Check for uncommitted changes
    set -l original_pwd (pwd)
    cd "$found"

    if git status --porcelain | grep -q .
        echo "⚠️  Warning: Worktree has uncommitted changes:"
        git status --short
        echo ""
        echo "Please commit or stash changes before removing:"
        echo "  git add . && git commit -m \"Save work before removing worktree\""
        echo "  git stash push -m \"Work in progress\""
        cd "$original_pwd"
        return 1
    end

    cd "$original_pwd"

    echo "Removing clean worktree: $found"
    git worktree remove "$found"

    if test $status -eq 0
        echo "✅ Successfully removed worktree: $found"
    else
        echo "❌ Failed to remove worktree: $found"
        return 1
    end
end