function _wt_root --description "Print the root of the main worktree of the current repository"
    # --git-common-dir is the main repository's .git directory, also when called
    # from inside a linked worktree or a subdirectory
    set -l common (git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
    or return 1
    dirname $common
end
