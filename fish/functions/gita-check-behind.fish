function gita-check-behind --description "Check how many commits a repository is behind main"
    if test (count $argv) -eq 0
        return 1
    end

    set --local repo_name $argv[1]

    # Get repository path from gita
    set --local repo_path (gita ll $repo_name 2>/dev/null)
    if test $status -ne 0
        echo "0"
        return 1
    end

    # Change to repository directory
    pushd $repo_path >/dev/null 2>&1
    if test $status -ne 0
        echo "0"
        return 1
    end

    # Count commits behind origin/main
    set --local behind_count (git rev-list --count HEAD..origin/main 2>/dev/null)
    if test $status -ne 0
        # Fallback to local main
        set behind_count (git rev-list --count HEAD..main 2>/dev/null)
        if test $status -ne 0
            set behind_count "0"
        end
    end

    popd >/dev/null 2>&1

    echo $behind_count
    return 0
end