function wt-list --description "Enhanced worktree listing with structure"
    echo "=== Current Worktrees ==="
    git worktree list
    echo ""
    echo "=== Worktree Structure ==="
    if test -d worktrees
        if command -v tree >/dev/null
            tree worktrees -L 2
        else
            # Fallback to ls if tree is not available
            echo "worktrees/"
            for type_dir in worktrees/*
                if test -d "$type_dir"
                    set type_name (basename "$type_dir")
                    echo "├── $type_name/"
                    for worktree in "$type_dir"/*
                        if test -d "$worktree"
                            set wt_name (basename "$worktree")
                            echo "│   └── $wt_name"
                        end
                    end
                end
            end
        end
    else
        echo "No worktrees directory found"
    end
end