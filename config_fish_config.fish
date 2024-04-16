if status is-interactive
    # Commands to run in interactive sessions can go here
    fish_add_path /home/do3cc/bin
    fish_ssh_agent
    direnv hook fish | source
    export NODE_VERSIONS=/home/do3cc/.local/share/nvm
end
