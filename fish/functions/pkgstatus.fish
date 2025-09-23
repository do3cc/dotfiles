function pkgstatus -d "Show package and system status with caching"
    # Configuration with defaults
    set -q pkgstatus_enabled; or set -U pkgstatus_enabled true
    set -q pkgstatus_cache_hours; or set -U pkgstatus_cache_hours 6
    set -q pkgstatus_show_on_startup; or set -U pkgstatus_show_on_startup quiet
    set -q pkgstatus_git_enabled; or set -U pkgstatus_git_enabled true
    set -q pkgstatus_init_enabled; or set -U pkgstatus_init_enabled true

    # Exit early if disabled
    if test "$pkgstatus_enabled" != "true"
        return 0
    end

    # Parse arguments
    set -l mode "interactive"
    set -l force_refresh false

    for arg in $argv
        switch $arg
            case --json
                set mode "json"
            case --quiet
                set mode "quiet"
            case --refresh
                set force_refresh true
            case --help -h
                _pkgstatus_help
                return 0
        end
    end

    # Cache directory setup
    set -l cache_dir "$XDG_CACHE_HOME/dotfiles/status"
    set -l packages_cache "$cache_dir/packages.json"
    set -l git_cache "$cache_dir/git.json"
    set -l init_cache "$cache_dir/init.json"

    # Ensure cache directory exists
    mkdir -p "$cache_dir"

    # Get status data
    set -l pkg_data (_pkgstatus_get_packages $packages_cache $force_refresh)
    set -l git_data (_pkgstatus_get_git $git_cache $force_refresh)
    set -l init_data (_pkgstatus_get_init $init_cache $force_refresh)

    # Output based on mode
    switch $mode
        case "json"
            _pkgstatus_output_json $pkg_data $git_data $init_data
        case "quiet"
            _pkgstatus_output_quiet $pkg_data $git_data $init_data
        case "interactive"
            _pkgstatus_output_interactive $pkg_data $git_data $init_data
    end
end

function _pkgstatus_help
    echo "pkgstatus - Show package and system status"
    echo ""
    echo "Usage:"
    echo "  pkgstatus              Interactive display (default)"
    echo "  pkgstatus --quiet      Only show if issues exist"
    echo "  pkgstatus --json       Machine readable output"
    echo "  pkgstatus --refresh    Force cache refresh"
    echo "  pkgstatus --help       Show this help"
    echo ""
    echo "Configuration (fish universal variables):"
    echo "  set -U pkgstatus_enabled true/false"
    echo "  set -U pkgstatus_cache_hours 6"
    echo "  set -U pkgstatus_show_on_startup quiet/always/never"
    echo "  set -U pkgstatus_git_enabled true/false"
    echo "  set -U pkgstatus_init_enabled true/false"
end

function _pkgstatus_get_packages -a cache_file force_refresh
    set -l max_age_seconds (math "$pkgstatus_cache_hours * 3600")

    # Check if we need to refresh cache
    if test "$force_refresh" = "true"; or not test -f "$cache_file"; or _pkgstatus_cache_expired "$cache_file" $max_age_seconds
        # Background refresh for packages (can be slow)
        _pkgstatus_refresh_packages_async "$cache_file" &

        # If cache exists but expired, use stale data and mark as stale
        if test -f "$cache_file"
            set -l data (cat "$cache_file" 2>/dev/null)
            if test -n "$data"
                echo "$data" | jq -c '. + {"stale": true}'
                return
            end
        end

        # No cache exists, create minimal placeholder
        echo '{"packages": {}, "total_updates": 0, "last_check": 0, "error": "Initial check in progress..."}'
    else
        # Use fresh cache
        cat "$cache_file" 2>/dev/null; or echo '{"packages": {}, "total_updates": 0, "last_check": 0, "error": "Cache read failed"}'
    end
end

function _pkgstatus_get_git -a cache_file force_refresh
    if test "$pkgstatus_git_enabled" != "true"
        echo '{"enabled": false}'
        return
    end

    set -l max_age_seconds 3600  # 1 hour for git status

    if test "$force_refresh" = "true"; or not test -f "$cache_file"; or _pkgstatus_cache_expired "$cache_file" $max_age_seconds
        _pkgstatus_refresh_git "$cache_file"
    end

    cat "$cache_file" 2>/dev/null; or echo '{"enabled": true, "error": "Git status unavailable"}'
end

function _pkgstatus_get_init -a cache_file force_refresh
    if test "$pkgstatus_init_enabled" != "true"
        echo '{"enabled": false}'
        return
    end

    set -l max_age_seconds 86400  # 24 hours for init status

    if test "$force_refresh" = "true"; or not test -f "$cache_file"; or _pkgstatus_cache_expired "$cache_file" $max_age_seconds
        _pkgstatus_refresh_init "$cache_file"
    end

    cat "$cache_file" 2>/dev/null; or echo '{"enabled": true, "error": "Init status unavailable"}'
end

function _pkgstatus_cache_expired -a file max_age
    if not test -f "$file"
        return 0  # File doesn't exist, consider expired
    end

    set -l file_age (math (date +%s) - (stat -c %Y "$file" 2>/dev/null; or echo 0))
    test $file_age -gt $max_age
end

function _pkgstatus_refresh_packages_async -a cache_file
    # Run swman in background and update cache
    set -l temp_file "$cache_file.tmp"

    # Create status object
    set -l timestamp (date +%s)

    # Try to get package status
    set -l swman_cmd ""
    if test -x "./swman.py"
        set swman_cmd "./swman.py"
    else if command -v swman.py >/dev/null 2>&1
        set swman_cmd "swman.py"
    end

    if test -n "$swman_cmd"
        set -l swman_output (timeout 30s $swman_cmd --check --json 2>/dev/null)
        if test $status -eq 0; and test -n "$swman_output"
            # Parse swman output and calculate totals (extract JSON block)
            set -l total_updates 0
            set -l packages_data (echo "$swman_output" | sed -n '/^{/,/^}$/p' | string join '')

            # Validate JSON and handle it properly
            if test -n "$packages_data"; and echo "$packages_data" | jq empty 2>/dev/null
                # Transform and calculate totals
                set -l pkg_obj (echo "$packages_data" | jq -c 'to_entries | map({key, value: {has_updates: .value[0], count: .value[1]}}) | from_entries')

                # Calculate total updates safely
                set total_updates (echo "$packages_data" | jq -r '[to_entries[] | select(.value[0] == true and (.value[1] | type == "number") and .value[1] > 0) | .value[1]] | add // 0')

                echo "{\"packages\":$pkg_obj,\"total_updates\":$total_updates,\"last_check\":$timestamp,\"stale\":false}" > "$temp_file"
            else
                echo "{\"packages\":{},\"total_updates\":0,\"last_check\":$timestamp,\"error\":\"invalid swman output\"}" > "$temp_file"
            end
        else
            echo "{\"packages\":{},\"total_updates\":0,\"last_check\":$timestamp,\"error\":\"swman check failed\"}" > "$temp_file"
        end
    else
        echo "{\"packages\":{},\"total_updates\":0,\"last_check\":$timestamp,\"error\":\"swman not available\"}" > "$temp_file"
    end

    # Atomically update cache
    mv "$temp_file" "$cache_file" 2>/dev/null
end

function _pkgstatus_refresh_git -a cache_file
    set -l temp_file "$cache_file.tmp"
    set -l timestamp (date +%s)

    # Initialize git status object
    set -l git_status '{"enabled":true,"last_check":'$timestamp

    if git rev-parse --git-dir >/dev/null 2>&1
        # We're in a git repository
        set -l uncommitted 0
        set -l unpushed 0
        set -l branch (git branch --show-current 2>/dev/null; or echo "detached")
        set -l behind 0
        set -l ahead 0

        # Count uncommitted changes
        set uncommitted (git status --porcelain 2>/dev/null | wc -l)

        # Count commits ahead/behind
        if test "$branch" != "detached"
            set -l upstream (git rev-parse --abbrev-ref "@{upstream}" 2>/dev/null)
            if test -n "$upstream"
                set -l counts (git rev-list --left-right --count "$upstream...HEAD" 2>/dev/null)
                if test -n "$counts"
                    set behind (echo "$counts" | cut -f1)
                    set ahead (echo "$counts" | cut -f2)
                end
            end
        end

        set git_status "$git_status"',"in_repo":true,"branch":"'"$branch"'","uncommitted":'$uncommitted',"ahead":'$ahead',"behind":'$behind
    else
        set git_status "$git_status"',"in_repo":false'
    end

    set git_status "$git_status"'}'
    echo "$git_status" > "$temp_file"
    mv "$temp_file" "$cache_file" 2>/dev/null
end

function _pkgstatus_refresh_init -a cache_file
    set -l temp_file "$cache_file.tmp"
    set -l timestamp (date +%s)

    # Check if init script would make changes (simplified check)
    set -l init_status '{"enabled":true,"last_check":'$timestamp

    # Check if we're in dotfiles directory
    if test -f "./init.py"
        set -l last_run_file "$XDG_CACHE_HOME/dotfiles_last_update"
        set -l last_run 0

        if test -f "$last_run_file"
            set last_run (date -d (cat "$last_run_file" 2>/dev/null) +%s 2>/dev/null; or echo 0)
        end

        set -l needs_update false
        set -l age_hours (math "($timestamp - $last_run) / 3600")

        # Consider update needed if more than 7 days old
        if test $age_hours -gt 168
            set needs_update true
        end

        set init_status "$init_status"',"in_dotfiles":true,"last_run":'$last_run',"needs_update":'$needs_update',"age_hours":'$age_hours
    else
        set init_status "$init_status"',"in_dotfiles":false'
    end

    set init_status "$init_status"'}'
    echo "$init_status" > "$temp_file"
    mv "$temp_file" "$cache_file" 2>/dev/null
end

function _pkgstatus_output_json -a pkg_data git_data init_data
    echo '{"packages":'$pkg_data',"git":'$git_data',"init":'$init_data'}'
end

function _pkgstatus_output_quiet -a pkg_data git_data init_data
    set -l has_issues false
    set -l messages

    # Check package updates
    set -l total_updates (echo "$pkg_data" | jq -r '.total_updates // 0')
    set -l pkg_stale (echo "$pkg_data" | jq -r '.stale // false')
    if test "$total_updates" -gt 0 2>/dev/null
        set has_issues true
        if test "$pkg_stale" = "true"
            set messages $messages "⚠️  $total_updates package updates available (stale cache)"
        else
            set -l last_check (echo "$pkg_data" | jq -r '.last_check // 0')
            set -l age (_pkgstatus_format_age $last_check)
            set messages $messages "⚠️  $total_updates package updates available ($age)"
        end
    end

    # Check git status
    if test "$pkgstatus_git_enabled" = "true"
        set -l git_enabled (echo "$git_data" | jq -r '.enabled // false')
        if test "$git_enabled" = "true"
            set -l in_repo (echo "$git_data" | jq -r '.in_repo // false')
            if test "$in_repo" = "true"
                set -l uncommitted (echo "$git_data" | jq -r '.uncommitted // 0')
                set -l ahead (echo "$git_data" | jq -r '.ahead // 0')
                if test "$uncommitted" -gt 0; or test "$ahead" -gt 0
                    set has_issues true
                    set -l git_msg "🔄 Git:"
                    if test "$uncommitted" -gt 0
                        set git_msg "$git_msg $uncommitted uncommitted"
                    end
                    if test "$ahead" -gt 0
                        set git_msg "$git_msg $ahead unpushed"
                    end
                    set messages $messages "$git_msg"
                end
            end
        end
    end

    # Check init status
    if test "$pkgstatus_init_enabled" = "true"
        set -l init_enabled (echo "$init_data" | jq -r '.enabled // false')
        if test "$init_enabled" = "true"
            set -l needs_update (echo "$init_data" | jq -r '.needs_update // false')
            if test "$needs_update" = "true"
                set has_issues true
                set -l age_hours (echo "$init_data" | jq -r '.age_hours // 0')
                set messages $messages "⚙️  Init script not run in $(math $age_hours / 24)d"
            end
        end
    end

    # Output messages if any issues
    if test "$has_issues" = "true"
        for msg in $messages
            echo "$msg"
        end
    end
end

function _pkgstatus_output_interactive -a pkg_data git_data init_data
    echo "📦 Package Status:"

    # Package status
    set -l total_updates (echo "$pkg_data" | jq -r '.total_updates // 0')
    set -l pkg_error (echo "$pkg_data" | jq -r '.error // null')
    set -l pkg_stale (echo "$pkg_data" | jq -r '.stale // false')

    if test "$pkg_error" != "null"
        echo "   ❌ $pkg_error"
    else if test "$total_updates" -gt 0 2>/dev/null
        if test "$pkg_stale" = "true"
            echo "   ⚠️  $total_updates updates available (checking for new updates...)"
        else
            set -l last_check (echo "$pkg_data" | jq -r '.last_check // 0')
            set -l age (_pkgstatus_format_age $last_check)
            echo "   ⚠️  $total_updates updates available (checked $age)"
        end

        # Show breakdown by manager
        for manager in (echo "$pkg_data" | jq -r '.packages | to_entries[] | select(.value.has_updates == true) | .key')
            set -l count (echo "$pkg_data" | jq -r ".packages.$manager.count")
            if test $count -gt 0
                echo "      • $manager: $count updates"
            else
                echo "      • $manager: updates available"
            end
        end
    else
        echo "   ✅ All packages up to date"
    end

    # Git status
    if test "$pkgstatus_git_enabled" = "true"
        echo ""
        echo "🔄 Git Status:"
        set -l git_enabled (echo "$git_data" | jq -r '.enabled // false')
        set -l git_error (echo "$git_data" | jq -r '.error // null')

        if test "$git_error" != "null"
            echo "   ❌ $git_error"
        else
            set -l in_repo (echo "$git_data" | jq -r '.in_repo // false')
            if test "$in_repo" = "true"
                set -l branch (echo "$git_data" | jq -r '.branch // "unknown"')
                set -l uncommitted (echo "$git_data" | jq -r '.uncommitted // 0')
                set -l ahead (echo "$git_data" | jq -r '.ahead // 0')
                set -l behind (echo "$git_data" | jq -r '.behind // 0')

                echo "   📁 Branch: $branch"
                if test $uncommitted -gt 0
                    echo "   ⚠️  $uncommitted uncommitted changes"
                end
                if test $ahead -gt 0
                    echo "   ⬆️  $ahead commits ahead of origin"
                end
                if test $behind -gt 0
                    echo "   ⬇️  $behind commits behind origin"
                end
                if test $uncommitted -eq 0; and test $ahead -eq 0; and test $behind -eq 0
                    echo "   ✅ Working tree clean and up to date"
                end
            else
                echo "   ℹ️  Not in a git repository"
            end
        end
    end

    # Init status
    if test "$pkgstatus_init_enabled" = "true"
        echo ""
        echo "⚙️  Init Status:"
        set -l init_enabled (echo "$init_data" | jq -r '.enabled // false')
        set -l init_error (echo "$init_data" | jq -r '.error // null')

        if test "$init_error" != "null"
            echo "   ❌ $init_error"
        else
            set -l in_dotfiles (echo "$init_data" | jq -r '.in_dotfiles // false')
            if test "$in_dotfiles" = "true"
                set -l needs_update (echo "$init_data" | jq -r '.needs_update // false')
                set -l age_hours (echo "$init_data" | jq -r '.age_hours // 0')

                if test "$needs_update" = "true"
                    echo "   ⚠️  Last run $(math $age_hours / 24)d ago - consider running"
                else
                    set -l age_desc (_pkgstatus_format_age (echo "$init_data" | jq -r '.last_run // 0'))
                    echo "   ✅ Recently run ($age_desc)"
                end
            else
                echo "   ℹ️  Not in dotfiles directory"
            end
        end
    end
end

function _pkgstatus_format_age -a timestamp
    if test $timestamp -eq 0
        echo "never"
        return
    end

    set -l age (math (date +%s) - $timestamp)

    if test $age -lt 60
        echo "just now"
    else if test $age -lt 3600
        echo "$(math $age / 60)m ago"
    else if test $age -lt 86400
        echo "$(math $age / 3600)h ago"
    else
        echo "$(math $age / 86400)d ago"
    end
end