from datetime import datetime
import os
from os.path import abspath, exists, expanduser
import socket
import subprocess
import urllib.request


def expand(path):
    return abspath(expanduser(path))


def ensure_path(path):
    if not exists(expand(path)):
        os.makedirs(expand(path))


class Linux:
    config_dirs = [
        ("alacritty", "alacritty"),
        ("direnv", "direnv"),
        ("fish", "fish"),
        ("irssi", "irssi"),
        ("lazy_nvim", "nvim"),
        ("tmux", "tmux"),
        ("byobu", "byobu"),
        ("git", "git"),
    ]

    def install_dependencies(self):
        if not exists(expand("~/.local/share/nvm")):
            subprocess.run(
                ["/usr/bin/bash", expand("./install_scripts/install_nvm.sh")],
                check=True,
            )
        if not exists(expand("~/.config/pyenv")):
            subprocess.run(
                ["/usr/bin/bash", expand("./install_scripts/install_pyenv.sh")],
                check=True,
            )

    def link_configs(self):
        for config_dir_src, config_dir_target in self.config_dirs:
            if not exists(expand(f"~/.config/{config_dir_target}")):
                import pdb;pdb.set_trace()
                os.symlink(
                    expand(f"./{config_dir_src}"),
                    expand(f"~/.config/{config_dir_target}"),
                )
            else:
                print(
                    f"Skipping configuration directory {config_dir_target}, it already exists"
                )

    def setup_shell(self):
        if "fish" not in str(
            subprocess.run(["ps"], check=True, capture_output=True).stdout
        ):
            subprocess.run(["chsh", "-s", "/usr/bin/fish"])

    def link_accounts(self):
        if "Logged in" not in subprocess.run(
            ["/usr/bin/gh", "auth", "status"], capture_output=True
        ).stdout.decode("utf-8"):
            subprocess.run(["/usr/bin/gh", "auth", "login"])
            subprocess.run(
                ["gh", "auth", "refresh", "-h", "github.com", "-s", "admin:public_key"]
            )

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
            subprocess.run(["ssh-add", current_key])
            key_name = f'"{socket.gethostname()} {datetime.now().strftime("%Y%m")}"'
            subprocess.run(
                ["/usr/bin/gh", "ssh-key", "add", f"{current_key}.pub", "-t", key_name],
                check=True,
            )


class Arch(Linux):
    aur_packages = [
        "hyprshot",
    ]
    pacman_packages = [
        "ast-grep",
        "bat",
        "bitwarden",
        "brightnessctl",
        "byobu",
        "direnv",
        "dolphin",
        "eza",
        "fd",
        "firefox",
        "fish",
        "ghostscript",
        "git",
        "github-cli",
        "htop",
        "hyprland",
        "hyprpaper",
        "imagemagick",
        "jdk-openjdk",
        "jq",
        "less",
        "libnotify",
        "lua51",
        "luarocks",
        "mako",
        "man-db",
        "mermaid-cli",
        "mpd",
        "neovim",
        "nmap",
        "noto-fonts-emoji",
        "npm",
        "otf-font-awesome",
        "pavucontrol",
        "pipewire",
        "pipewire-alsa",
        "pipewire-jack",
        "pipewire-pulse",
        "polkit-kde-agent",
        "powerline-fonts",
        "power-profiles-daemon",
        "python-gobject",
        "qt5-wayland",
        "qt6-wayland",
        "rofi-wayland",
        "rsync",
        "slurp",
        "starship",
        "tectonic",
        "the_silver_searcher",
        "tig",
        "tldr",
        "tree-sitter-cli",
        "uv",
        "waybar",
        "wget",
        "wireplumber",
        "wl-clipboard",
        "xdg-desktop-portal-gtk",
        "xdg-desktop-portal-hyprland",
        "yarn",
    ]

    def install_dependencies(self):
        def pacman(*args, **kwargs):
            subprocess.run(["sudo", "pacman"] + list(args), **kwargs)

        pacman("-S", "--needed", "git", "base-devel", check=True)
        ensure_path(expand("~/projects"))
        if not exists(expand("~/projects/yay-bin")):
            subprocess.run(
                [
                    "git",
                    "clone",
                    "https://aur.archlinux.org/yay-bin.git",
                    expand("~/projects/yay-bin"),
                ],
                check=True,
            )
            subprocess.run(
                ["makepkg", "-si", "--needed", "--noconfirm"],
                check=True,
                cwd=expand("~/projects/yay-bin"),
            )

        pacman(
            "-S",
            "--needed",
            "--noconfirm",
            *self.pacman_packages,
            check=True,
        )
        subprocess.run(
            ["yay", "-S", "--needed", "--noconfirm"] + self.aur_packages,
            check=True,
        )
        super().install_dependencies()


class Debian(Linux):
    apt_packages = [
        "ack",
        "apt-file",
        "build-essential",
        "byobu",
        "curl",
        "direnv",
        "fish",
        "github-cli",
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

    def install_dependencies(self):
        subprocess.run(["sudo", "apt-get", "update"])
        subprocess.run(["sudo", "apt-get", "upgrade", "--assume-yes"])
        subprocess.run(
            ["sudo", "apt-get", "install", "--assume-yes"] + self.apt_packages,
            check=True,
        )
        subprocess.run(["sudo", "apt-file", "update"])
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

        super().install_dependencies()


operating_system = None

with open("/etc/os-release") as release_file:
    content = release_file.read()
    if 'NAME="Arch Linux"' in content:
        operating_system = Arch()
    else:
        raise NotImplementedError


print("Installing dependencies")
operating_system.install_dependencies()
print("Linking configurations")
operating_system.link_configs()
print("Setting up shell")
operating_system.setup_shell()
print("Link online accounts")
operating_system.link_accounts()
