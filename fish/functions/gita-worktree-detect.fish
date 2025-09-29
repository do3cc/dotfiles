function gita-worktree-detect --description "Check if repository uses worktrees"
    # Require repository argument
    if test (count $argv) -eq 0
        return 1
    end

    set --local repo_name $argv[1]

    # Get repository path from gita
    set --local repo_path (gita ll $repo_name 2>/dev/null)
    if test $status -ne 0
        return 1
    end

    # Change to repository directory and check worktrees
    pushd $repo_path >/dev/null 2>&1
    if test $status -ne 0
        return 1
    end

    # Get worktree list and count lines
    set --local worktree_count (git worktree list 2>/dev/null | wc -l)
    popd >/dev/null 2>&1

    # If there's more than one line, there are additional worktrees
    # (first line is always the main repository)
    if test $worktree_count -gt 1
        return 0
    else
        return 1
    end
end