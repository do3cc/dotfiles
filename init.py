import argparse
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
        ("lazy_nvim", "nvim"),
        ("tmux", "tmux"),
        ("byobu", "byobu"),
        ("git", "git"),
    ]

    ssh_key_email = "sshkeys@patrick-gerken.de"

    environment_specific = {
        "config_dirs": {
            "private": [
                ("irssi", "irssi"),
            ]
        },
        "ssh_key_email": {"work": "patrick.gerken@zumtobelgroup.com"},
    }

    def __init__(self, environment="minimal", test_mode=False):
        self.environment = environment
        self.test_mode = test_mode

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
        for config_dir_src, config_dir_target in (
            self.config_dirs
            + self.environment_specific["config_dirs"].get(self.environment, [])
        ):
            if not exists(expand(f"~/.config/{config_dir_target}")):
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
        if self.test_mode:
            print("Test mode: Skipping GitHub and SSH key setup")
            if self.environment in ["private"]:
                print("Test mode: Skipping Tailscale setup")
            return

        if "Logged in" not in subprocess.run(
            ["/usr/bin/gh", "auth", "status"], capture_output=True
        ).stdout.decode("utf-8"):
            subprocess.run(["/usr/bin/gh", "auth", "login"])
            subprocess.run(
                ["gh", "auth", "refresh", "-h", "github.com", "-s", "admin:public_key"]
            )

        current_key = expand("~/.ssh/id_ed_" + datetime.now().strftime("%Y%m"))
        if not exists(current_key):
            ssh_key_email = self.environment_specific["ssh_key_email"].get(
                self.environment, self.ssh_key_email
            )
            subprocess.run(
                [
                    "ssh-keygen",
                    "-t",
                    "ed25519",
                    "-C",
                    f"'Patrick Gerken {socket.gethostname()} {ssh_key_email} {datetime.now().strftime('%Y%m')}'",
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

        if self.environment in ["private"]:
            if "Logged in" not in subprocess.run(
                ["tailscale", "status"], check=True, capture_output=True
            ).stdout.decode("utf-8"):
                subprocess.run(
                    ["sudo", "tailscale", "login", "--operator=do3cc", "--qr"],
                    check=True,
                )


class Arch(Linux):
    aur_packages = []
    pacman_packages = [
        "ast-grep",  # structural code search tool
        "bat",  # syntax highlighted cat alternative
        "byobu",  # terminal multiplexer frontend
        "direnv",  # environment variable manager
        "eza",  # modern ls replacement
        "fd",  # fast find replacement
        "fish",  # friendly interactive shell
        "git",  # version control system
        "github-cli",  # GitHub command line interface
        "htop",  # interactive process viewer
        "jdk-openjdk",  # Java development kit
        "jq",  # JSON command line processor
        "less",  # terminal pager
        "lua51",  # Lua scripting language
        "luarocks",  # Lua package manager
        "man-db",  # manual page database
        "mermaid-cli",  # diagram generation tool
        "neovim",  # modern Vim text editor
        "nmap",  # network discovery and scanning
        "npm",  # Node.js package manager
        "rsync",  # file synchronization tool
        "starship",  # cross-shell prompt
        "tectonic",  # LaTeX engine
        "the_silver_searcher",  # fast text search tool
        "tig",  # text-mode Git interface
        "tealdeer",  # fast tldr client
        "tree-sitter-cli",  # parser generator tool
        "uv",  # fast Python package manager
        "wget",  # web file downloader
        "yarn",  # Node.js package manager
    ]

    environment_specific = {
        "aur_packages": {
            "private": [
                "hyprshot",  # Hyprland screenshot tool
            ]
        },
        "pacman_packages": {
            "private": [
                "bitwarden",  # password manager
                "brightnessctl",  # screen brightness control
                "dolphin",  # KDE file manager
                "firefox",  # web browser
                "ghostscript",  # PostScript and PDF interpreter
                "hyprland",  # Wayland compositor
                "hyprpaper",  # wallpaper utility for Hyprland
                "imagemagick",  # image manipulation toolkit
                "libnotify",  # desktop notification library
                "mako",  # lightweight notification daemon
                "mpd",  # music player daemon
                "noto-fonts-emoji",  # emoji font collection
                "otf-font-awesome",  # icon font
                "pavucontrol",  # PulseAudio volume control
                "pipewire",  # multimedia framework
                "pipewire-alsa",  # ALSA compatibility for PipeWire
                "pipewire-jack",  # JACK compatibility for PipeWire
                "pipewire-pulse",  # PulseAudio compatibility for PipeWire
                "polkit-kde-agent",  # authentication agent for KDE
                "powerline-fonts",  # fonts for powerline
                "power-profiles-daemon",  # power management service
                "python-gobject",  # Python GObject bindings
                "qt5-wayland",  # Qt5 Wayland support
                "qt6-wayland",  # Qt6 Wayland support
                "rofi-wayland",  # application launcher for Wayland
                "slurp",  # Wayland screen region selector
                "tailscale",  # mesh VPN service
                "waybar",  # Wayland status bar
                "wireplumber",  # PipeWire session manager
                "wl-clipboard",  # Wayland clipboard utilities
                "xdg-desktop-portal-gtk",  # GTK desktop portal
                "xdg-desktop-portal-hyprland",  # Hyprland desktop portal
            ]
        },
        "systemd_services_to_enable": {
            "private": [
                "tailscaled",
            ]
        },
    }
    systemd_services_to_enable = []

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
            *self.pacman_packages
            + self.environment_specific["pacman_packages"].get(self.environment, []),
            check=True,
        )
        subprocess.run(
            ["yay", "-S", "--needed", "--noconfirm"]
            + self.aur_packages
            + self.environment_specific["aur_packages"].get(self.environment, []),
            check=True,
        )

        for service in self.systemd_services_to_enable + self.environment_specific[
            "systemd_services_to_enable"
        ].get(self.environment, []):
            subprocess.run(["systemctl", "enable", "--now", service], check=True)
        super().install_dependencies()


class Debian(Linux):
    apt_packages = [
        "ack",  # text search tool
        "apt-file",  # search files in packages
        "build-essential",  # compilation tools and libraries
        "byobu",  # terminal multiplexer frontend
        "curl",  # command line URL tool
        "direnv",  # environment variable manager
        "fish",  # friendly interactive shell
        "github-cli",  # GitHub command line interface
        "jq",  # JSON command line processor
        "libbz2-dev",  # bzip2 development library
        "libffi-dev",  # foreign function interface library
        "libfuse2",  # filesystem in userspace library
        "liblzma-dev",  # XZ compression library
        "libncursesw5-dev",  # terminal control library
        "libreadline-dev",  # GNU readline library
        "libsqlite3-dev",  # SQLite development library
        "libssl-dev",  # SSL development library
        "libxml2-dev",  # XML development library
        "libxmlsec1-dev",  # XML security library
        "neovim",  # modern Vim text editor
        "nmap",  # network discovery and scanning
        "npm",  # Node.js package manager
        "silversearcher-ag",  # fast text search tool
        "tig",  # text-mode Git interface
        "tk-dev",  # Tk GUI toolkit
        "xz-utils",  # XZ compression utilities
        "zlib1g-dev",  # compression library
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


def detect_operating_system(environment="minimal", test_mode=False):
    """Detect and return the appropriate operating system class"""
    with open("/etc/os-release") as release_file:
        content = release_file.read()
        if 'NAME="Arch Linux"' in content:
            return Arch(environment=environment, test_mode=test_mode)
        if 'NAME="Garuda Linux"' in content:
            return Arch(environment=environment, test_mode=test_mode)
        else:
            raise NotImplementedError(f"Unknown operating system, found {content}")


def show_help():
    """Display detailed help information"""
    help_text = """
Dotfiles Installation Script

USAGE:
    uv run init.py [OPTIONS]

OPTIONS:
    --environment {minimal,work,private}
                        Environment configuration to install (default: minimal)
    --test             Skip remote activities (GitHub, SSH keys, Tailscale) for testing
    --help             Show this help message and exit

ENVIRONMENTS:
    minimal            Basic development tools and CLI utilities
    work               Minimal environment + work-specific configurations
    private            Full desktop environment with window manager and GUI apps

WHAT THIS SCRIPT DOES:
    1. Detects your operating system (Arch/Garuda or Debian-based)
    2. Installs required packages via package managers
    3. Creates symlinks for configuration directories to ~/.config/
    4. Sets up development tools (NVM, Pyenv)
    5. Configures shell (fish) and prompt (starship)
    6. Sets up GitHub authentication and SSH keys
    7. Configures Tailscale (private environment only)

EXAMPLES:
    uv run init.py                    # Install minimal environment
    uv run init.py --environment work # Install work environment
    uv run init.py --environment private # Install full desktop environment
    uv run init.py --test             # Test installation without remote activities

For more information, see the README or CLAUDE.md files.
"""
    print(help_text)


def main():
    """Main entry point for the dotfiles installation script"""
    parser = argparse.ArgumentParser(
        description="Install and configure dotfiles for Linux systems",
        add_help=False,  # Disable default help to use custom help
    )
    parser.add_argument(
        "--environment",
        choices=["minimal", "work", "private"],
        default="minimal",
        help="Environment configuration to install (default: minimal)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Skip remote activities (GitHub, SSH keys, Tailscale) for testing",
    )
    parser.add_argument(
        "--help", action="store_true", help="Show detailed help information"
    )

    args = parser.parse_args()

    if args.help:
        show_help()
        return

    operating_system = detect_operating_system(
        environment=args.environment, test_mode=args.test
    )

    print(
        f"Installing dotfiles for {args.environment} environment{' (test mode)' if args.test else ''}"
    )

    print("Installing dependencies")
    operating_system.install_dependencies()
    print("Linking configurations")
    operating_system.link_configs()
    print("Setting up shell")
    operating_system.setup_shell()
    print("Link online accounts")
    operating_system.link_accounts()


if __name__ == "__main__":
    main()
