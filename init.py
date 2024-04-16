from datetime import datetime
import os
import os.path
from os.path import abspath, exists, expanduser
import socket
import subprocess
import urllib.request

apt_packages = [
    "ack",
    "apt-file",
    "build-essential",
    "byobu",
    "curl",
    "direnv",
    "fish",
    "jq",
    "libbz2-dev",
    "libffi-dev",
    "libfuse2",
    "liblzma-dev",
    "libncursesw5-dev",
    "libreadline-dev",
    "libsqlite3-dev",
    "libssl-dev",
    "libxml2-dev",
    "libxmlsec1-dev",
    "neovim",
    "nmap",
    "npm",
    "silversearcher-ag",
    "tig",
    "tk-dev",
    "xz-utils",
    "zlib1g-dev",
]


dotfiles_home = [
    ".byobu",
    ".gitconfig",
    ".gitmessage.txt",
    ".gitignore",
    ".inputrc",
    ".irssi",
    ".p10k.zsh",
    ".tmux.conf",
    ".vimrc",
]

other_dotfiles = [
    ("config_direnv_direnvrc", ".config", "direnv", "direnvrc"),
    ("config_nvim_coc-settings.json", ".config", "nvim", "coc-settings.json"),
    ("config_fish_config.fish", ".config", "fish", "config.fish"),
]


def expand(path):
    return abspath(expanduser(path))


def ensure_path(path):
    if not exists(expand(path)):
        os.makedirs(expand(path))


subprocess.run(["sudo", "apt-get", "update"])
subprocess.run(["sudo", "apt-get", "upgrade", "--assume-yes"])
subprocess.run(
    ["sudo", "apt-get", "install", "--assume-yes"] + apt_packages, check=True
)
subprocess.run(["sudo", "apt-file", "update"])

for dotfile in dotfiles_home:
    if not exists(expand(f"~/{dotfile}")):
        os.symlink(expand(f"./{dotfile}"), expand(f"~/{dotfile}"))

for source, *target in other_dotfiles:
    ensure_path(f"~/{os.path.join(*target[:-1])}")
    if not exists(expand(f"~/{os.path.join(*target)}")):
        os.symlink(expand(f"./{source}"), expand(f"~/{os.path.join(*target)}"))

if "fish" not in str(subprocess.run(["ps"], check=True, capture_output=True).stdout):
    subprocess.run(["chsh", "-s", "/usr/bin/fish"])

if not exists(expand("~/.nvm")):
    subprocess.run(
        ["/usr/bin/bash", expand("./install_scripts/install_nvm.sh")], check=True
    )

if not exists(expand("~/.pyenv")):
    subprocess.run(
        ["/usr/bin/bash", expand("./install_scripts/install_pyenv.sh")], check=True
    )
ensure_path("~/.config/nvim")
if not exists(expand("~/.config/nvim/init.vim")):
    os.symlink(expand("./.vimrc"), expand("~/.config/nvim/init.vim"))

if not exists(expand("./nvim.appimage")):
    urllib.request.urlretrieve(
        "https://github.com/neovim/neovim/releases/latest/download/nvim.appimage",
        "nvim.appimage",
    )
    os.chmod(expand("./nvim.appimage"), 0o744)
    ensure_path(expand("~/bin"))
    if not exists(expand("~/bin/nvim")):
        os.symlink(expand("./nvim.appimage"), expand("~/bin/nvim"))
        os.chmod("~/bin/nvim", 0o744)

for addon in ["fish-ssh-agent-master", "nvm.fish-main", "plugin-pyenv-master"]:
    for dir in ("completions", "conf.d", "functions"):
        if exists(expand(f"./fish_addons/{addon}/{dir}")):
            for filename in os.listdir(expand(f"./fish_addons/{addon}/{dir}")):
                if not exists(expand(f"~/.config/fish/{dir}/{filename}")):
                    os.symlink(
                        expand(f"./fish_addons/{addon}/{dir}/{filename}"),
                        expand(f"~/.config/fish/{dir}/{filename}"),
                    )

if "Logged in" not in subprocess.run(
    ["/usr/bin/gh", "auth", "status"], check=True, capture_output=True
).stderr.decode("utf-8"):
    subprocess.run(["/usr/bin/gh", "auth", "login"])

current_key = expand("~/.ssh/id_ed_" + datetime.now().strftime("%Y%m"))
if not exists(current_key):
    subprocess.run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-C",
            f"'Patrick Gerken {socket.gethostname()} sshkeys@patrick-gerken.de {datetime.now().strftime('%Y%m')}'",
            "-f",
            current_key,
        ]
    )
    key_name = f"\"{socket.gethostname()} {datetime.now().strftime('%Y%m')}\""
    subprocess.run(
        ["/usr/bin/gh", "ssh-key", "add", f"{current_key}.pub", "-t", key_name],
        check=True,
    )
