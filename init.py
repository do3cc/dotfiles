from datetime import datetime
import os
import os.path
from os.path import abspath, exists, expanduser
import pdb
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
    "gh",
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


config_dirs = [
        "alacritty",
        "direnv",
        "fish",
        "irssi",
        "nvim",
        "tmux",
        "byobu",
        "git",
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

;pdb.set_trace()
for config_dir in config_dirs:
    if not exists(expand(f"~/.config/{config_dir}")):
        os.symlink(expand(f"./{config_dir}"), expand(f"~/.config/{config_dir}"))

if "fish" not in str(subprocess.run(["ps"], check=True, capture_output=True).stdout):
    subprocess.run(["chsh", "-s", "/usr/bin/fish"])

if not exists(expand("~/.local/share/nvm")):
    subprocess.run(
        ["/usr/bin/bash", expand("./install_scripts/install_nvm.sh")], check=True
    )

if not exists(expand("~/.config/pyenv")):
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
        ensure_path(expand("~/bin"))
        os.symlink(expand("./nvim.appimage"), expand("~/bin/nvim"))
        os.chmod("~/bin/nvim", 0o744)

if "Logged in" not in subprocess.run(
    ["/usr/bin/gh", "auth", "status"], capture_output=True
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
