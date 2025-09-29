function gita-batch-fetch --description "Silent background fetching across repositories"
    # Parse command line arguments
    set --local silent_mode false
    set --local timeout_seconds 30

    for arg in $argv
        switch $arg
            case '--silent'
                set silent_mode true
            case '--timeout'
                set timeout_seconds $argv[2]
                set argv $argv[3..-1]  # Remove processed arguments
        end
    end

    # Get all repositories from discovery
    set --local repos (gita-repo-discovery)
    if test $status -ne 0 -o (count $repos) -eq 0
        return 0
    end

    # Fetch repositories in parallel
    set --local fetch_pids

    for repo in $repos
        if test $silent_mode = true
            # Silent mode - suppress all output
            gita fetch $repo >/dev/null 2>&1 &
        else
            # Normal mode - show output
            gita fetch $repo &
        end

        set --append fetch_pids $last_pid
    end

    # Wait for all background processes to complete
    for pid in $fetch_pids
        wait $pid
    end

    return 0
end