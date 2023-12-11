# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

#!/bin/zsh
# vim: set foldmarker=<<,>> foldlevel=0 foldmethod=marker:

# Source the prompt <<1
#-------------------------------------------------------------------------------
# Precmd functions local array variable <<2
#-------------------------------------------------------------------------------
local -a precmd_functions
# >>2
# Precmd functions <<2
#------------------------------------------------------------------------------
# Run precmd functions so we get our pimped out prompt
#------------------------------------------------------------------------------
precmd_functions=( precmd_prompt )
# >>2
# >>1

# General Settings <<1
# Autoload tab completion <<2
#-------------------------------------------------------------------------------
autoload -U compinit
autoload -U colors && colors
compinit -C
# >> 2
# Modify default zsh directory coloring on ls commands <<2
#-------------------------------------------------------------------------------
export LSCOLORS=gxfxcxdxbxegedabagacad
# >>2
# Completion settings <<2
#-------------------------------------------------------------------------------
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=*' 'l:|=* r:|=*'
zstyle ':completion:*' list-colors "$LS_COLORS"
zstyle -e ':completion:*:(ssh|scp|sshfs|ping|telnet|nc|rsync):*' hosts '
    reply=( ${=${${(M)${(f)"$(<~/.ssh/config)"}:#Host*}#Host }:#*\**} )'
# >>2
# Set the desired setup options man zshoptions <<2
#-------------------------------------------------------------------------------
# If command can't be executed, and command is name of a directory, cd to directory
setopt  auto_cd
# Make cd push the old directory onto the directory stack.
setopt  auto_pushd
# Safety for overwriting files use >| instead of > to over write files
setopt  noclobber
# Prevents aliases on the command line from being internally substituted before
# completion is attempted. The effect is to make the alias a distinct command
# for completion purposes.
setopt  complete_aliases
# Treat the #, ~ and ^ characters as part of patterns for filename
# generation, etc.  (An initial unquoted `~' always produces named directory
# expansion.)
setopt  extended_glob
# If a new command line being added to the history list duplicates an older one,
# the older command is removed from the list (even if it is not the previous event).
setopt  hist_ignore_all_dups
#  Remove command lines from the history list when the first character on the line
#  is a space, or when one of the expanded aliases contains a leading space.
setopt  hist_ignore_space
# This  option  both  imports new commands from the history file, and also
# causes your typed commands to be appended to the history file
setopt  share_history
setopt  noflowcontrol
# When listing files that are possible completions, show the type of each file
# with a trailing identifying mark.
setopt  list_types
# Append a trailing / to all directory names resulting from filename
# generation (globbing).
setopt  mark_dirs
# Perform a path search even on command names with slashes in them.
# Thus if /usr/local/bin is in the user's path, and he or she types
# X11/xinit, the  command /usr/local/bin/X11/xinit will be executed
# (assuming it exists).
setopt  path_dirs
# If set, `%' is treated specially in prompt expansion.
setopt  prompt_percent
# If set, parameter expansion, command substitution and arithmetic
# expansion are performed in prompts.
# Substitutions within prompts do not affect the command status.
setopt  prompt_subst
# >>2
# History settings <<2
#-------------------------------------------------------------------------------
HISTFILE=$HOME/.zsh_history
HISTFILESIZE=65536  # search this with `grep | sort -u`
HISTSIZE=4096
SAVEHIST=4096
REPORTTIME=60       # Report time statistics for progs that take more than a minute to run
# >>2
# utf-8 in the terminal, will break stuff if your term isn't utf aware <<2
#-------------------------------------------------------------------------------
export LANG=en_US.UTF-8
export LC_ALL=$LANG
export LC_COLLATE=C
# >>2
# Use the correct ctags <<2
#-------------------------------------------------------------------------------
# >>2
# Editor and display configurations <<2
#-------------------------------------------------------------------------------
export EDITOR='nvim'
export VISUAL='nvim'
export GIT_EDITOR=$EDITOR
export LESS='-imJMWR'
export PAGER="less $LESS"
export MANPAGER=$PAGER
export GIT_PAGER=$PAGER
export BROWSER='firefox'
# >>2
# Eliminate lag between transition from normal/insert mode <<2
#-------------------------------------------------------------------------------
# If this causes issue with other shell commands it can be raised default is 4
export KEYTIMEOUT=1
# >>2
# >>1

# Source antigen <<1
#-------------------------------------------------------------------------------
if [[ ! -f ~/.antigen.zsh ]]; then
    curl -L git.io/antigen > ~/.antigen.zsh
fi
source ~/.antigen.zsh
# >>1

# Set antigen bundles <<1
#-------------------------------------------------------------------------------
antigen use oh-my-zsh
antigen bundle zsh-users/zsh-syntax-highlighting
antigen bundle git
if [ -z "$SSH_CLIENT" ]; then
    antigen bundle ssh-agent
fi
# >>1
#
#antigen theme powerlevel10k
antigen theme romkatv/powerlevel10k
antigen apply


# Key Bindings <<1
#-------------------------------------------------------------------------------
# Set vi-mode and create a few additional Vim-like mappings
#-------------------------------------------------------------------------------
bindkey -v
bindkey '^R' history-incremental-search-backward
bindkey '^R' history-incremental-pattern-search-backward
bindkey '^?' backward-delete-char
bindkey '^H' backward-delete-char
# >>1

# Aliases <<1
#-------------------------------------------------------------------------------
if [ "$(uname)" = "Darwin" ]; then
    alias ls='ls -FHG'
else
    alias ls='ls -F --color'
fi
alias ll='ls -lh'
alias la='ls -la'
alias lls='ll -Sr'
alias less='less -imJMW'
alias tmux="TERM=screen-256color-bce tmux"  # Fix tmux making vim colors funky
alias gs='git status'
alias gd='git diff'
alias gc='git commit'
alias push='git push origin master'
alias pull='git pull --rebase'
alias ts='tig status'
alias tigr='git reflog --pretty=raw | tig --pretty=raw'
alias tmuxh='tmux attach -t host-session || tmux new-session -s host-session'
alias vim='nvim'
# >>1

# Agnoster theme tricks
DEFAULT_USER=do3cc

PATH="/home/do3cc/.local/bin:/usr/local/bin:$PATH"
export PATH="$PATH:$HOME/.rvm/bin" # Add RVM to PATH for scripting

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

export PATH="$HOME/.yarn/bin:$HOME/.config/yarn/global/node_modules/.bin:$PATH"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion

eval "$(direnv hook zsh)"
