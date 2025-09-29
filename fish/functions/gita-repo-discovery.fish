function gita-repo-discovery --description "Discover repositories managed by gita"
    # Check if gita is available
    if not command -q gita
        return 1
    end

    set --local repos_file ~/.config/gita/repo_path

    # Parse gita configuration to get repository list
    if test -f $repos_file
        # Extract repository names from the gita repo_path file
        # Format is typically: repo_name:path
        cat $repos_file | awk -F: '{print $1}' | grep -v '^$'
    else
        # Fallback to gita list command
        gita list 2>/dev/null | grep -v '^$'
    end
end