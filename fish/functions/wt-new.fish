function wt-new --description "Create new worktree with proper organization"
    set -l types review feature bugfix experimental
    set -l type $argv[1] # review, feature, bugfix, experimental
    set -l name $argv[2] # descriptive name

    if test (count $argv) -lt 2
        echo "Usage: wt-new <type> <name>"
        echo "Types: $types"
        echo "Example: wt-new feature issue-25-logging"
        return 1
    end

    if not contains -- $type $types
        echo "Error: Invalid type '$type'. Use: $types"
        return 1
    end

    set -l root (_wt_root)
    or begin
        echo "Error: Not in a git repository"
        return 1
    end

    # The type directories are created on first use
    mkdir -p "$root/.worktrees/$type"
    or return 1

    # Branches off the current HEAD, wherever the command is run from
    git worktree add "$root/.worktrees/$type/$name" -b "$name"
    if test $status -eq 0
        echo "Created worktree: $root/.worktrees/$type/$name"
        cd "$root/.worktrees/$type/$name"
    end
end
