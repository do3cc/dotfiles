# Path to your oh-my-zsh configuration.
ZSH=$HOME/.oh-my-zsh

# Set name of the theme to load.
# Look in ~/.oh-my-zsh/themes/
# Optionally, if you set this to "random", it'll load a random theme each
# time that oh-my-zsh is loaded.
#ZSH_THEME="mortalscumbag"
#ZSH_THEME="dogenpunk"
ZSH_THEME="smt"
#ZSH_THEME='wedisagree'

# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"

# Set to this to use case-sensitive completion
# CASE_SENSITIVE="true"

# Comment this out to disable bi-weekly auto-update checks
# DISABLE_AUTO_UPDATE="true"

# Uncomment to change how many often would you like to wait before auto-updates occur? (in days)
# export UPDATE_ZSH_DAYS=13

# Uncomment following line if you want to disable colors in ls
# DISABLE_LS_COLORS="true"

# Uncomment following line if you want to disable autosetting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment following line if you want red dots to be displayed while waiting for completion
# COMPLETION_WAITING_DOTS="true"

# Which plugins would you like to load? (plugins can be found in ~/.oh-my-zsh/plugins/*)
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)

plugins=(git knife pip python sublime supervisor vagrant fabric rvm tmuxinator)
source $ZSH/oh-my-zsh.sh

alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal ||     echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*       alert$//'\'')"'

# Sort properly for plone
alias sort="LC_ALL=C sort"

# configure todo
alias t="todo.sh -d /home/do3cc/ownCloud/todo/todo.cfg"

#(which keychain > /dev/null && eval `keychain /home/do3cc/Private/ssh/id_rsa /home/do3cc/Private/ssh/id_rsa_old /home/do3cc/Private/ssh/blog.pem`)
(which keychain > /dev/null && eval `keychain A9516641`)

PATH=$PATH:$HOME/.rvm/bin # Add RVM to PATH for scripting

export DEBFULLNAME="Patrick Gerken"
export DEBEMAIL="gerken@patrick-gerken.de"

export EDITOR=vim

# Set up virtualenvwrappre, depends on where it exists
export WORKON_HOME=~/.dev
export PROJECT_HOME=~/dev
[ -f /usr/local/bin/virtualenvwrapper.sh ]  && source /usr/local/bin/virtualenvwrapper.sh
[ -f /usr/share/virtualenvwrapper/virtualenvwrapper.sh ] && source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
