function wt-goto --description "Quick navigation to worktrees"
    if test (count $argv) -eq 0
        echo "Usage: wt-goto <search-term>"
        echo "Example: wt-goto issue-25"
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

    if test -n "$found"
        echo "Navigating to: $found"
        cd "$found"
    else
        echo "Worktree matching '$target' not found"
        echo ""
        wt-list
        return 1
    end
end
