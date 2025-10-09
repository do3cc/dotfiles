function wt-root --description "Navigate back to project root from any worktree"
    # Get the current directory
    set current_dir (pwd)

    # Check if we're in a git repository
    if not git rev-parse --git-dir >/dev/null 2>&1
        echo "Error: Not in a git repository"
        return 1
    end

    # Get the root of the git repository (main worktree)
    set git_common_dir (git rev-parse --git-common-dir)
    set project_root (dirname "$git_common_dir")

    # Check if we're already at the project root
    if test "$current_dir" = "$project_root"
        echo "Already at project root: $project_root"
        return 0
    end

    # Navigate to the project root
    cd "$project_root"
    if test $status -eq 0
        echo "📁 Navigated to project root: $project_root"
    else
        echo "Error: Failed to navigate to project root"
        return 1
    end
end
