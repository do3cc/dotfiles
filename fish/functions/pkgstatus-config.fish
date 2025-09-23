function pkgstatus-config -d "Configure pkgstatus settings"
    switch $argv[1]
        case enable
            set -U pkgstatus_enabled true
            echo "✅ pkgstatus enabled"

        case disable
            set -U pkgstatus_enabled false
            echo "🚫 pkgstatus disabled"

        case startup
            if test (count $argv) -lt 2
                echo "Usage: pkgstatus-config startup [always|quiet|never]"
                return 1
            end

            switch $argv[2]
                case always quiet never
                    set -U pkgstatus_show_on_startup $argv[2]
                    echo "✅ Startup mode set to: $argv[2]"
                case '*'
                    echo "❌ Invalid startup mode. Use: always, quiet, or never"
                    return 1
            end

        case cache-hours
            if test (count $argv) -lt 2
                echo "Usage: pkgstatus-config cache-hours <hours>"
                return 1
            end

            if string match -qr '^\d+$' $argv[2]
                set -U pkgstatus_cache_hours $argv[2]
                echo "✅ Cache hours set to: $argv[2]"
            else
                echo "❌ Cache hours must be a number"
                return 1
            end

        case git
            if test (count $argv) -lt 2
                echo "Usage: pkgstatus-config git [enable|disable]"
                return 1
            end

            switch $argv[2]
                case enable
                    set -U pkgstatus_git_enabled true
                    echo "✅ Git status monitoring enabled"
                case disable
                    set -U pkgstatus_git_enabled false
                    echo "🚫 Git status monitoring disabled"
                case '*'
                    echo "❌ Use 'enable' or 'disable'"
                    return 1
            end

        case init
            if test (count $argv) -lt 2
                echo "Usage: pkgstatus-config init [enable|disable]"
                return 1
            end

            switch $argv[2]
                case enable
                    set -U pkgstatus_init_enabled true
                    echo "✅ Init script monitoring enabled"
                case disable
                    set -U pkgstatus_init_enabled false
                    echo "🚫 Init script monitoring disabled"
                case '*'
                    echo "❌ Use 'enable' or 'disable'"
                    return 1
            end

        case reset
            set -e pkgstatus_enabled
            set -e pkgstatus_cache_hours
            set -e pkgstatus_show_on_startup
            set -e pkgstatus_git_enabled
            set -e pkgstatus_init_enabled
            echo "✅ All pkgstatus settings reset to defaults"

        case clear-cache
            set -l cache_dir "$XDG_CACHE_HOME/dotfiles/status"
            if test -d "$cache_dir"
                rm -rf "$cache_dir"
                echo "✅ Cache cleared"
            else
                echo "ℹ️  Cache directory doesn't exist"
            end

        case show list ''
            echo "📦 pkgstatus Configuration:"
            echo ""

            # Show current settings with defaults
            set -l enabled (set -q pkgstatus_enabled; and echo $pkgstatus_enabled; or echo "true")
            set -l cache_hours (set -q pkgstatus_cache_hours; and echo $pkgstatus_cache_hours; or echo "6")
            set -l startup (set -q pkgstatus_show_on_startup; and echo $pkgstatus_show_on_startup; or echo "quiet")
            set -l git_enabled (set -q pkgstatus_git_enabled; and echo $pkgstatus_git_enabled; or echo "true")
            set -l init_enabled (set -q pkgstatus_init_enabled; and echo $pkgstatus_init_enabled; or echo "true")

            echo "  enabled:        $enabled"
            echo "  startup mode:   $startup"
            echo "  cache hours:    $cache_hours"
            echo "  git monitoring: $git_enabled"
            echo "  init monitoring: $init_enabled"
            echo ""

            # Show cache status
            set -l cache_dir "$XDG_CACHE_HOME/dotfiles/status"
            if test -d "$cache_dir"
                echo "📁 Cache Status ($cache_dir):"
                for file in packages.json git.json init.json
                    set -l cache_file "$cache_dir/$file"
                    if test -f "$cache_file"
                        set -l age (math (date +%s) - (stat -c %Y "$cache_file" 2>/dev/null; or echo 0))
                        if test $age -lt 60
                            echo "  $file: fresh ($(math $age)s ago)"
                        else if test $age -lt 3600
                            echo "  $file: $(math $age / 60)m ago"
                        else if test $age -lt 86400
                            echo "  $file: $(math $age / 3600)h ago"
                        else
                            echo "  $file: $(math $age / 86400)d ago"
                        end
                    else
                        echo "  $file: not cached"
                    end
                end
            else
                echo "📁 Cache: not initialized"
            end

        case help --help -h
            echo "pkgstatus-config - Configure pkgstatus settings"
            echo ""
            echo "Usage:"
            echo "  pkgstatus-config                    Show current configuration"
            echo "  pkgstatus-config enable|disable     Enable/disable pkgstatus"
            echo "  pkgstatus-config startup MODE       Set startup behavior (always|quiet|never)"
            echo "  pkgstatus-config cache-hours HOURS  Set cache duration in hours"
            echo "  pkgstatus-config git enable|disable Enable/disable git monitoring"
            echo "  pkgstatus-config init enable|disable Enable/disable init script monitoring"
            echo "  pkgstatus-config reset              Reset all settings to defaults"
            echo "  pkgstatus-config clear-cache        Clear all cached data"
            echo "  pkgstatus-config help               Show this help"
            echo ""
            echo "Startup modes:"
            echo "  always  - Always show status on startup"
            echo "  quiet   - Only show if issues exist (default)"
            echo "  never   - Never show on startup"

        case '*'
            echo "❌ Unknown command: $argv[1]"
            echo "Use 'pkgstatus-config help' for usage information"
            return 1
    end
end