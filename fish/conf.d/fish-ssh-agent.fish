if test -z "$SSH_ENV"
    set -xg SSH_ENV $HOME/.ssh/environment
end

if not __ssh_agent_is_started
    __ssh_agent_start
end

# Auto-load default SSH key (symlink created by init script)
set default_key_path $HOME/.ssh/id_ed25519_default
if test -f $default_key_path
    ssh-add $default_key_path 2>/dev/null
end
