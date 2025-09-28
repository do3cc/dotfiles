if test -z "$SSH_ENV"
    set -xg SSH_ENV $HOME/.ssh/environment
end

if not __ssh_agent_is_started
    __ssh_agent_start
end

# Auto-load environment-specific SSH key
if test -n "$DOTFILES_ENVIRONMENT"
    set ssh_key_path $HOME/.ssh/id_ed25519_(hostname)_$DOTFILES_ENVIRONMENT
    if test -f $ssh_key_path
        ssh-add $ssh_key_path 2>/dev/null
    end
end
