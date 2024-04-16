if status is-interactive
    # Commands to run in interactive sessions can go here
    starship init fish | source
    pyenv init - | source
    direnv hook fish | source
    fzf --fish | source
    fish_ssh_agent
    export XDG_DATA_HOME=$HOME/.local/share
    export XDG_CONFIG_HOME=$HOME/.config
    export XDG_STATE_HOME=$HOME/.local/state
    export XDG_CACHE_HOME=$HOME/.cache
    export XINITRC="$XDG_CONFIG_HOME"/X11/xinitrc
    export SQLITE_HISTORY="$XDG_CACHE_HOME"/sqlite_history
    export PYENV_ROOT="$XDG_DATA_HOME"/pyenv
    export NVM_DIR="$XDG_DATA_HOME"/nvm
    export LESSHISTFILE="$XDG_STATE_HOME"/less/history
    export ANSIBLE_HOME="$XDG_DATA_HOME"/ansible
end
