#!/bin/zsh
# vim: set foldmarker=<<,>> foldlevel=0 foldmethod=marker:
#===================================================================================
#  DESCRIPTION:  You realize, Dr. Angelo, that my intelligence has surpassed yours.
#       AUTHOR:  Jarrod Taylor
#                 .__
#  ________  _____|  |_________   ____
#  \___   / /  ___/  |  \_  __ \_/ ___\
#   /    /  \___ \|   Y  \  | \/\  \___
#  /_____ \/____  >___|  /__|    \___  >
#        \/     \/     \/            \/
#
#===================================================================================
#

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
# Set grepoptions <<2
#-------------------------------------------------------------------------------
export GREP_OPTIONS='--color=auto'
# >>2
# Use the correct ctags <<2
#-------------------------------------------------------------------------------
PATH="/home/do3cc/.local/bin:/usr/local/bin:$PATH"
# >>2
# Editor and display configurations <<2
#-------------------------------------------------------------------------------
export EDITOR='vim'
export VISUAL='vim'
export GIT_EDITOR=$EDITOR
export LESS='-imJMWR'
export PAGER="less $LESS"
export MANPAGER=$PAGER
export GIT_PAGER=$PAGER
export BROWSER='firefox'
# >>2
# Specify virtualenv directories <<2
#-------------------------------------------------------------------------------
export WORKON_HOME=$HOME/.dev
export PROJECT_HOME=$HOME/dev
# >>2
# Add postgress to the path on osx <<2
#-------------------------------------------------------------------------------
if [ "$(uname)" = "Darwin" ]; then
    PATH="/Applications/Postgres.app/Contents/Versions/9.4/bin:$PATH"
fi
# >>2
# Add Heroku Toolbelt to the path on osx <<2
#-------------------------------------------------------------------------------
if [ "$(uname)" = "Darwin" ]; then
    PATH="/usr/local/heroku/bin:$PATH"
fi
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
    curl https://raw.githubusercontent.com/zsh-users/antigen/master/antigen.zsh > ~/.antigen.zsh
fi
source ~/.antigen.zsh
# >>1

# Set antigen bundles <<1
#-------------------------------------------------------------------------------
antigen use oh-my-zsh
antigen bundle zsh-users/zsh-syntax-highlighting
antigen bundle robbyrussell/oh-my-zsh plugins/django
antigen bundle git
antigen bundle hchbaw/opp.zsh opp.plugin.zsh
# >>1
#
antigen theme agnoster

# Source antigen bundles <<1
#-------------------------------------------------------------------------------
# Antigen should handle this but doesn't seem to
source ~/.antigen/repos/https-COLON--SLASH--SLASH-github.com-SLASH-hchbaw-SLASH-opp.zsh.git/opp.zsh
source ~/.antigen/repos/https-COLON--SLASH--SLASH-github.com-SLASH-robbyrussell-SLASH-oh-my-zsh.git/plugins/django/django.plugin.zsh
# >>1

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
    alias update='brew update && brew upgrade'
    alias upgrade='brew upgrade'
    alias clean='brew doctor'
else
    alias ls='ls -F --color'
    alias update='sudo apt-get update && sudo apt-get upgrade'
    alias upgrade='sudo apt-get upgrade'
    alias clean='sudo apt-get autoclean && sudo apt-get autoremove'
    alias root_trash='sudo bash -c "exec rm -r /root/.local/share/Trash/{files,info}/*"'
fi
alias ll='ls -lh'
alias la='ls -la'
alias lls='ll -Sr'
alias less='less -imJMW'
alias tmux="TERM=screen-256color-bce tmux"  # Fix tmux making vim colors funky
alias ping='ping -c 5'      # Pings with 5 packets, not unlimited
alias gs='git status'
alias gd='git diff'
alias gc='git commit'
alias push='git push origin master'
alias pull='git pull --rebase'
alias ts='tig status'
alias tigr='git reflog --pretty=raw | tig --pretty=raw'
alias tmuxh='tmux attach -t host-session || tmux new-session -s host-session'
alias tmuxp='tmux attach -t pair-session || tmux new-session -t host-session -s pair-session'
alias delete_pyc='find . -name \*.pyc -exec rm \{\} \+'
alias c='clear'
alias vom='vim'
# >>1

# Todo <<1
# ==============================================================================
alias t="todo.sh -d /home/do3cc/ownCloud/todo/todo.cfg"

# Functions <<1
#===============================================================================

# Python webserver <<2
#-------------------------------------------------------------------------------
#  cd into a directory you want to share and then
#  type webshare. You will be able to connect to that directory
#  with other machines on the local net work with IP:8000
#  the function will display the current machines ip address
#-------------------------------------------------------------------------------
function pyserve() {
    if [ "$(uname)" = "Darwin" ]; then
        local_ip=`ifconfig | grep 192 | cut -d ' ' -f 2`
    else
        local_ip=`hostname -I | cut -d " " -f 1`
    fi
    echo "connect to http://$local_ip:8000"
        python -m SimpleHTTPServer > /dev/null 2>&1
    }
# >>2
# Work Timer <<2
#-------------------------------------------------------------------------------
# A timer function that will say the message after the specified amount of time.
#-------------------------------------------------------------------------------
function workTimer() {
    echo -n "How long to set timer for? (ex. 1h, 10m, 20s, etc) => "; read duration
    echo -n "What to say when time finishes => "; read finishMessage
    if [ "$(uname)" = "Darwin" ]; then
      if [ $duration[-1] = "h" ]; then
          (( durationInHours = $duration[1,-2] * 60 * 60))
          sleep $durationInHours && say "$finishMessage"
      elif [ $duration[-1] = "m" ]; then
          (( durationInMinutes = $duration[1,-2] * 60))
          sleep $durationInMinutes && say "$finishMessage"
      elif [ $duration[-1] = "s" ]; then
          sleep $duration && say "$finishMessage"
      else
        echo "You must specify; Hours, Min or Seconds.."
      fi
    else
      sleep $duration && espeak "$finishMessage" && zenity --info --title="$name" --text="$finishMessage"
    fi
}
# >>2
# Memory Usage <<2
#-------------------------------------------------------------------------------
# Shows the specified number of the top memory consuming processes and their PID
#-------------------------------------------------------------------------------
function mem_usage() {
    echo -n "How many you what to see? "; read number
    echo ""
    echo "Mem Size       PID     Process"
    echo "============================================================================="
    if [ "$(uname)" = "Darwin" ]; then
      ps aux | awk '{ output = sprintf("%5d Mb --> %5s --> %s%s%s%s", $6/1024, $2, $11, $12, $13, $14); print output }' | sort -gr | head -n $number
    else
      ps aux | awk '{ output = sprintf("%5d Mb --> %5s --> %s%s%s%s", $6/1024, $2, $11, $12, $13, $14); print output }' | sort -gr | head --line $number
    fi
    }
# >>2
# Spell Check <<2
#------------------------------------------------------------------------------
# Because, well I need to spell check a lot :\
#------------------------------------------------------------------------------
spell (){
    echo $1 | aspell -a
}
# >>2
# Workon virtualenv <<2
#--------------------------------------------------------------------
# If we cd into a directory that is named the same as a virtualenv
# auto activate that virtualenv
# -------------------------------------------------------------------
[[ -a /usr/local/share/python/virtualenvwrapper.sh ]] && source /usr/local/share/python/virtualenvwrapper.sh
[[ -a /usr/local/bin/virtualenvwrapper.sh ]] && source /usr/local/bin/virtualenvwrapper.sh

workon_virtualenv() {
  if [[ -d .git ]]; then
     VENV_CUR_DIR="${PWD##*/}"
     if [[ -a ~/.dev/$VENV_CUR_DIR ]]; then
       deactivate > /dev/null 2>&1
       source ~/.dev/$VENV_CUR_DIR/bin/activate
     fi
  fi
}
# >>2
# Workon node env <<2
#--------------------------------------------------------------------
# If we cd into a directory that contains a directory named node_modules
# we automatically add it to the $PATH
# -------------------------------------------------------------------
workon_node_env() {
  if [[ -d "node_modules" ]]; then

    export NPM_ORIGINAL_PATH=$PATH
    eval NODE_NAME=$(basename $(pwd))
    export PATH="${PATH}:$(pwd)/node_modules/.bin"

    deactivatenode(){
      export PATH=$NPM_ORIGINAL_PATH
      unset -f deactivatenode
      unset NODE_NAME
    }
  fi
}
# >>2
# Run the virtual environments functions for the prompt on each cd <<2
# -------------------------------------------------------------------
cd() {
  builtin cd "$@"
  unset NODE_NAME
  workon_virtualenv
  workon_node_env
}
# >>2
# Search for running processes <<2
# -------------------------------------------------------------------
any() {
    emulate -L zsh
    unsetopt KSH_ARRAYS
    if [[ -z "$1" ]] ; then
        echo "any - grep for process(es) by keyword" >&2
        echo "Usage: any " >&2 ; return 1
    else
        if [ "$(uname)" = "Darwin" ]; then
            echo "USER            PID     %CPU %MEM VSZ       RSS  TTY   STAT START     TIME    COMMAND"
        else
            echo "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND"
        fi
        ps xauwww | grep -i --color=auto "[${1[1]}]${1[2,-1]}"
    fi
}
# >>2
# Display a neatly formatted path <<2
# -------------------------------------------------------------------
path() {
echo $PATH | tr ":" "\n" | \
    awk "{ sub(\"/usr\",   \"$fg_no_bold[green]/usr$reset_color\"); \
           sub(\"/bin\",   \"$fg_no_bold[blue]/bin$reset_color\"); \
           sub(\"/opt\",   \"$fg_no_bold[cyan]/opt$reset_color\"); \
           sub(\"/sbin\",  \"$fg_no_bold[magenta]/sbin$reset_color\"); \
           sub(\"/local\", \"$fg_no_bold[yellow]/local$reset_color\"); \
           print }"
  }
# >>2
# Displays mounted drive information in a nicely formatted manner <<2
# -------------------------------------------------------------------
function nicemount() {
    (echo "DEVICE PATH TYPE FLAGS" && mount | awk '$2="";1') | column -t ;
}
# >>2
# Source file if it exists <<2
#--------------------------------------------------------------------
include() {
    [[ -s "$1" ]] && source "$1"
}
# >>2
# agvim open ag results in vim <<2
#--------------------------------------------------------------------
agv() {
   vim +"Search"
}
# >>2
# Extract the most common compression types <<2
#--------------------------------------------------------------------
function extract()
{
    if [ -f $1 ] ; then
        case $1 in
            *.tar.bz2)   tar xvjf $1     ;;
            *.tar.gz)    tar xvzf $1     ;;
            *.bz2)       bunzip2 $1      ;;
            *.rar)       unrar x $1      ;;
            *.gz)        gunzip $1       ;;
            *.tar)       tar xvf $1      ;;
            *.tbz2)      tar xvjf $1     ;;
            *.tgz)       tar xvzf $1     ;;
            *.zip)       unzip $1        ;;
            *.Z)         uncompress $1   ;;
            *.7z)        7z x $1         ;;
            *)           echo "'$1' cannot be extracted via >extract<" ;;
        esac
    else
        echo "'$1' is not a valid file!"
    fi
}
# >>2
# Find a file with a pattern in name: <<2
#--------------------------------------------------------------------
function ff() { find . -type f -iname '*'"$*"'*' -ls ; }
# >>2
# Create an archive (*.tar.gz) from given directory <<2
#--------------------------------------------------------------------
function maketar() { tar cvzf "${1%%/}.tar.gz"  "${1%%/}/"; }
# >>2
# Create a ZIP archive of a file or folder <<2
#--------------------------------------------------------------------
function makezip() { zip -r "${1%%/}.zip" "$1" ; }
# >>2
# Get info about an ip or url <<2
#--------------------------------------------------------------------
# Usage:
# ipinfo -i 199.59.150.7
# ipinfo -u github.com
#--------------------------------------------------------------------
ipinfo() {
    if [ $# -lt 2 ]; then
      echo "Usage: `basename $0` -i ipaddress" 1>&2
      echo "Usage: `basename $0` -u url" 1>&2
      return
    fi
    if [ "$1" = "-i" ]; then
        desiredIP=$2
    fi
    if [ "$1" = "-u" ]; then
        # Aleternate ways to get desired IP
        # desitedIP=$(host unix.stackexchange.com | awk '/has address/ { print $4 ; exit }')
        # desiredIP=$(nslookup google.com | awk '/^Address: / { print $2 ; exit }')
        desiredIP=$(dig +short $2)
    fi
    curl freegeoip.net/json/$desiredIP | python -mjson.tool
}
# >>2
# Export java cmd if jdk is installed <<2
#--------------------------------------------------------------------
# This seems like it is going to be a PITA with versions, but it works ATM.
if [[ -s "/Library/Java/JavaVirtualMachines/jdk1.8.0_20.jdk/Contents/Home/bin/java" ]]; then
    export JAVA_CMD="/Library/Java/JavaVirtualMachines/jdk1.8.0_20.jdk/Contents/Home/bin/java"
fi
# >>2
# Upwards directory traversal shortcut <<2
#--------------------------------------------------------------------
# Hitting `...` will produce `../..` an additional `/..` will be added
# for every `.` after that
# -------------------------------------------------------------------
traverse_up() {
    if [[ $LBUFFER = *.. ]]; then
        LBUFFER+=/..
    else
        LBUFFER+=.
    fi
}
zle -N traverse_up
bindkey . traverse_up
# >>2
# >>1

# Source Custom Configurations <<1
for fname in $(find ~/dotfiles/custom-configs -name "*.sh*"); do
    source $fname
done
# >>1

# EOF

# Agnoster theme tricks
DEFAULT_USER=do3cc
eval `dircolors ~/.dircolors`

export PATH="$PATH:$HOME/.rvm/bin" # Add RVM to PATH for scripting
