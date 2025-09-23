function pkgstatus -d "Show package and system status"
    # Configuration with defaults
    set -q pkgstatus_enabled; or set -U pkgstatus_enabled true

    # Exit early if disabled
    if test "$pkgstatus_enabled" != "true"
        return 0
    end

    # Find the Python script
    set -l script_path
    if test -x "./pkgstatus.py"
        set script_path "./pkgstatus.py"
    else if test -x (dirname (status -f))"/../../pkgstatus.py"
        set script_path (dirname (status -f))"/../../pkgstatus.py"
    else
        echo "❌ pkgstatus.py not found" >&2
        return 1
    end

    # Pass all arguments directly to Python script
    $script_path $argv
end