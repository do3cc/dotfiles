if status is-interactive
    # Commands to run in interactive sessions can go here
    # Set default value for fish_prompt_pwd_dir_length to avoid errors
    set -q fish_prompt_pwd_dir_length; or set -g fish_prompt_pwd_dir_length 1
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
    # Dotfiles repository location for tools like pkgstatus
    export DOTFILES_DIR="$HOME/projects/dotfiles"
    nvm use lts

    # Show package/system status on startup
    pkgstatus --quiet
end

# uv
