if test -z "$SSH_ENV"
    set -xg SSH_ENV $HOME/.ssh/environment
end

if not __ssh_agent_is_started
    __ssh_agent_start
end

# Auto-load default SSH key (symlink created by init script)
if test -f $HOME/.ssh/id_ed25519_default
    ssh-add $HOME/.ssh/id_ed25519_default 2>/dev/null
end
