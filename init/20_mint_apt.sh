# Ubuntu-only stuff. Abort if not Ubuntu.
is_mint || return 1

# Update APT.
e_header "Updating APT"
sudo apt-get -qq update
sudo apt-get -qq dist-upgrade

# Install APT packages.
packages=(
  ansible
  build-essential
  cowsay
  git-core
  htop
  nmap
  ack-grep
  byobu
  vim
  zsh
  apt-file
  virtualenvwrapper
  python-pip
  owncloud-client
  keepass2
  xdotool
  mutt-patched
  offlineimap
  notmuch
  pycarddav
  keychain
  irssi
)

packages=($(setdiff "${packages[*]}" "$(dpkg --get-selections | grep -v deinstall | awk '{print $1}')"))
echo 123
echo $packages

if (( ${#packages[@]} > 0 )); then
  e_header "Installing APT packages: ${packages[*]}"
  for package in "${packages[@]}"; do
    sudo apt-get -qq install "$package"
  done
fi

# Install Git Extras
if [[ ! "$(type -P git-extras)" ]]; then
  e_header "Installing Git Extras"
  (
    cd $DOTFILES/vendor/git-extras &&
    sudo make install
  )
fi
