# Change shell to zsh
chsh -s /usr/bin/zsh

# Symlink oy-my-zsh
cd ~
[ ! -d .oh-my-zsh ] && git clone https://github.com/do3cc/oh-my-zsh.git .oh-my-zsh
