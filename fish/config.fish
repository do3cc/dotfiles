if status is-interactive
    # Commands to run in interactive sessions can go here
    starship init fish | source
    direnv hook fish | source
    uv generate-shell-completion fish | source
    fish_add_path "/home/do3cc/.local/share/../bin"
    export XDG_DATA_HOME=$HOME/.local/share
    export XDG_CONFIG_HOME=$HOME/.config
    export XDG_STATE_HOME=$HOME/.local/state
    export XDG_CACHE_HOME=$HOME/.cache
    export XINITRC="$XDG_CONFIG_HOME"/X11/xinitrc
    export SQLITE_HISTORY="$XDG_CACHE_HOME"/sqlite_history
    export NVM_DIR="$XDG_DATA_HOME"/nvm
    export LESSHISTFILE="$XDG_STATE_HOME"/less/history
    export ANSIBLE_HOME="$XDG_DATA_HOME"/ansible
    export NODE_VERSIONS="$XDG_DATA_HOME/nvm"
    export NODE_VERSION_PREFIX=""
    nvm use lts
end

# uv
