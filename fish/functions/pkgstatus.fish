function pkgstatus -d "Show package and system status"
    # Configuration with defaults
    set -q pkgstatus_enabled; or set -U pkgstatus_enabled true

    # Exit early if disabled
    if test "$pkgstatus_enabled" != "true"
        return 0
    end

    # Check if we're in the dotfiles repo directory
    set -l dotfiles_dir (dirname (dirname (status -f)))

    # Use the proper entry point if available, otherwise try uv run
    if command -v dotfiles-pkgstatus >/dev/null 2>&1
        # Use the installed entry point
        dotfiles-pkgstatus $argv
    else if test -f "$dotfiles_dir/pyproject.toml"
        # We're in the dotfiles repo, use uv run
        cd "$dotfiles_dir" && uv run dotfiles-pkgstatus $argv
    else
        # Try direct uv run as fallback
        uv run dotfiles-pkgstatus $argv
    end
end