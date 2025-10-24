function wt-new --description "Create new worktree with proper organization"
    set type $argv[1]    # review, feature, bugfix, experimental
    set name $argv[2]    # descriptive name

    if test (count $argv) -lt 2
        echo "Usage: wt-new <type> <name>"
        echo "Types: review, feature, bugfix, experimental"
        echo "Example: wt-new feature issue-25-logging"
        return 1
    end

    if not test -d ".worktrees/$type"
        echo "Error: Invalid type '$type'. Use: review, feature, bugfix, experimental"
        return 1
    end

    git worktree add ".worktrees/$type/$name" -b "$name"
    if test $status -eq 0
        echo "Created worktree: .worktrees/$type/$name"
        cd ".worktrees/$type/$name"
    end
end