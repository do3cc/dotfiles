import argparse
from dataclasses import dataclass, field
from datetime import datetime
import os
from os.path import abspath, exists, expanduser
import socket
import subprocess
from typing import Dict, List, Tuple
import urllib.request


# Configuration Constants - Modify these to customize your dotfiles setup

# Personal Information - Change these to your details
DEFAULT_SSH_KEY_EMAIL = "sshkeys@patrick-gerken.de"  # Default SSH key email
DEFAULT_AUTHOR_NAME = "Patrick Gerken"  # Your name for SSH key comments

# Environment-specific personal data
ENVIRONMENT_PERSONAL_DATA = {
    "work": {
        "ssh_key_email": "patrick.gerken@zumtobelgroup.com",
    }
}

# Base configuration directories that get symlinked to ~/.config/
BASE_CONFIG_DIRS = [
    ("alacritty", "alacritty"),
    ("direnv", "direnv"),
    ("fish", "fish"),
    ("lazy_nvim", "nvim"),
    ("tmux", "tmux"),
    ("byobu", "byobu"),
    ("git", "git"),
]

# Environment-specific additional config directories
ENVIRONMENT_CONFIG_DIRS = {
    "private": [
        ("irssi", "irssi"),
    ]
}

# Arch Linux base packages
ARCH_PACMAN_PACKAGES = [
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
    "texlive-latex",  # for markdown rendering
    "lazygit",  # git cli used by lazy vim
    "less",  # terminal pager
    "lua51",  # Lua scripting language
    "luarocks",  # Lua package manager
    "man-db",  # manual page database
    "markdownlint-cli2",  # linter for markdown
    "mermaid-cli",  # diagram generation tool
    "neovim",  # modern Vim text editor
    "nmap",  # network discovery and scanning
    "npm",  # Node.js package manager
    "python-pip",  # Global pip
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

# Arch Linux AUR packages
ARCH_AUR_PACKAGES = [
    "google-java-format",  # Java formatting tool
    "nodejs-markdown-toc",  # TOC Generator in javascript
]

# Environment-specific Arch packages
ARCH_ENVIRONMENT_PACKAGES = {
    "pacman": {
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
    "aur": {
        "private": [
            # "hyprshot",  # Hyprland screenshot tool - REMOVED per issue requirements
        ]
    }
}

# Debian/Ubuntu packages
DEBIAN_APT_PACKAGES = [
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

# SystemD services to enable by environment
SYSTEMD_SERVICES = {
    "private": [
        "tailscaled",
    ]
}


@dataclass
class EnvironmentConfig:
    """
    Configuration dataclass for environment-specific settings.

    This replaces the cumbersome dictionary-based approach with a more
    structured and type-safe configuration system.
    """

    environment: str
    config_dirs: List[Tuple[str, str]] = field(default_factory=list)
    ssh_key_email: str = DEFAULT_SSH_KEY_EMAIL
    pacman_packages: List[str] = field(default_factory=list)
    aur_packages: List[str] = field(default_factory=list)
    apt_packages: List[str] = field(default_factory=list)
    systemd_services: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize environment-specific configuration after dataclass creation."""
        # Start with base configuration
        self.config_dirs = BASE_CONFIG_DIRS.copy()

        # Add environment-specific config directories
        if self.environment in ENVIRONMENT_CONFIG_DIRS:
            self.config_dirs.extend(ENVIRONMENT_CONFIG_DIRS[self.environment])

        # Set environment-specific personal data
        if self.environment in ENVIRONMENT_PERSONAL_DATA:
            env_data = ENVIRONMENT_PERSONAL_DATA[self.environment]
            if "ssh_key_email" in env_data:
                self.ssh_key_email = env_data["ssh_key_email"]

        # Set systemd services
        if self.environment in SYSTEMD_SERVICES:
            self.systemd_services = SYSTEMD_SERVICES[self.environment]


@dataclass
class OSConfig:
    """
    Base configuration for operating system specific settings.
    """

    def get_environment_config(self, environment: str) -> EnvironmentConfig:
        """Get environment configuration for this OS."""
        return EnvironmentConfig(environment=environment)


@dataclass
class ArchConfig(OSConfig):
    """
    Arch Linux specific configuration.
    """

    def get_environment_config(self, environment: str) -> EnvironmentConfig:
        """Get environment configuration for Arch Linux."""
        config = super().get_environment_config(environment)

        # Set base packages
        config.pacman_packages = ARCH_PACMAN_PACKAGES.copy()
        config.aur_packages = ARCH_AUR_PACKAGES.copy()

        # Add environment-specific packages
        if environment in ARCH_ENVIRONMENT_PACKAGES["pacman"]:
            config.pacman_packages.extend(ARCH_ENVIRONMENT_PACKAGES["pacman"][environment])

        if environment in ARCH_ENVIRONMENT_PACKAGES["aur"]:
            config.aur_packages.extend(ARCH_ENVIRONMENT_PACKAGES["aur"][environment])

        return config


@dataclass
class DebianConfig(OSConfig):
    """
    Debian/Ubuntu specific configuration.
    """

    def get_environment_config(self, environment: str) -> EnvironmentConfig:
        """Get environment configuration for Debian/Ubuntu."""
        config = super().get_environment_config(environment)
        config.apt_packages = DEBIAN_APT_PACKAGES.copy()
        return config


# Simple console output class since we don't have Rich available in this branch
class ConsoleOutput:
    """
    Simple console output class to replace print statements.
    """

    def __init__(self, quiet: bool = False):
        self.quiet = quiet

    def status(self, message: str) -> None:
        """Display a status message."""
        if not self.quiet:
            print(f"🔍 {message}")

    def success(self, message: str) -> None:
        """Display a success message."""
        if not self.quiet:
            print(f"✅ {message}")

    def error(self, message: str) -> None:
        """Display an error message."""
        if not self.quiet:
            print(f"❌ {message}")

    def warning(self, message: str) -> None:
        """Display a warning message."""
        if not self.quiet:
            print(f"⚠️  {message}")

    def info(self, message: str) -> None:
        """Display an info message."""
        if not self.quiet:
            print(f"💡 {message}")


def expand(path):
    return abspath(expanduser(path))


def ensure_path(path):
    if not exists(expand(path)):
        os.makedirs(expand(path))


class Linux:
    """
    Base Linux system configuration and installation logic.
    """

    def __init__(self, environment="minimal", test_mode=False):
        self.environment = environment
        self.test_mode = test_mode
        self.console = ConsoleOutput()
        self.config = self.get_os_config().get_environment_config(environment)

    def get_os_config(self) -> OSConfig:
        """Override in subclasses to return OS-specific configuration."""
        return OSConfig()

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
        """Create symlinks for configuration directories."""
        for config_dir_src, config_dir_target in self.config.config_dirs:
            target_path = expand(f"~/.config/{config_dir_target}")
            if not exists(target_path):
                os.symlink(
                    expand(f"./{config_dir_src}"),
                    target_path,
                )
                self.console.success(f"Linked {config_dir_target} configuration")
            else:
                # Check if it's a directory or symlink to another location
                if os.path.isdir(target_path):
                    if os.path.islink(target_path):
                        # It's a symlink to a directory
                        current_target = os.readlink(target_path)
                        expected_target = expand(f"./{config_dir_src}")
                        if current_target != expected_target:
                            self.console.warning(
                                f"{config_dir_target} is linked to {current_target}, "
                                f"but should be linked to {expected_target}"
                            )
                        else:
                            self.console.success(f"{config_dir_target} is already correctly linked")
                    else:
                        # It's a regular directory
                        self.console.warning(
                            f"{config_dir_target} exists as a directory, "
                            f"but should be a symlink to {expand(f'./{config_dir_src}')}"
                        )
                else:
                    # It's a file (not a directory)
                    self.console.warning(
                        f"{config_dir_target} exists as a file, "
                        f"but should be a symlink to {expand(f'./{config_dir_src}')}"
                    )

    def setup_shell(self):
        if "fish" not in str(
            subprocess.run(["ps"], check=True, capture_output=True).stdout
        ):
            subprocess.run(["chsh", "-s", "/usr/bin/fish"])

    def link_accounts(self):
        """Set up GitHub authentication, SSH keys, and other online accounts."""
        if self.test_mode:
            self.console.info("Test mode: Skipping GitHub and SSH key setup")
            if self.environment in ["private"]:
                self.console.info("Test mode: Skipping Tailscale setup")
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
            ssh_key_email = self.config.ssh_key_email
            self.console.status(f"Generating SSH key for {ssh_key_email}")
            subprocess.run(
                [
                    "ssh-keygen",
                    "-t",
                    "ed25519",
                    "-C",
                    f"'{DEFAULT_AUTHOR_NAME} {socket.gethostname()} {ssh_key_email} {datetime.now().strftime('%Y%m')}'",
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
            self.console.success(f"SSH key generated and added to GitHub")

        if self.environment in ["private"]:
            if "Logged in" not in subprocess.run(
                ["tailscale", "status"], check=True, capture_output=True
            ).stdout.decode("utf-8"):
                self.console.status("Setting up Tailscale connection")
                subprocess.run(
                    ["sudo", "tailscale", "login", "--operator=do3cc", "--qr"],
                    check=True,
                )
                self.console.success("Tailscale setup completed")


class Arch(Linux):
    """
    Arch Linux specific implementation with package management.
    """

    def get_os_config(self) -> OSConfig:
        """Return Arch-specific configuration."""
        return ArchConfig()

    def install_dependencies(self):
        """Install Arch Linux packages using pacman and yay."""
        def pacman(*args, **kwargs):
            subprocess.run(["sudo", "pacman"] + list(args), **kwargs)

        self.console.status("Installing base development tools")
        pacman("-S", "--needed", "git", "base-devel", check=True)

        ensure_path(expand("~/projects"))
        if not exists(expand("~/projects/yay-bin")):
            self.console.status("Installing yay AUR helper")
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
            self.console.success("Yay AUR helper installed")

        self.console.status(f"Installing {len(self.config.pacman_packages)} pacman packages")
        pacman(
            "-S",
            "--needed",
            "--noconfirm",
            *self.config.pacman_packages,
            check=True,
        )
        self.console.success("Pacman packages installed")

        if self.config.aur_packages:
            self.console.status(f"Installing {len(self.config.aur_packages)} AUR packages")
            subprocess.run(
                ["yay", "-S", "--needed", "--noconfirm"]
                + self.config.aur_packages,
                check=True,
            )
            self.console.success("AUR packages installed")

        if self.config.systemd_services:
            self.console.status(f"Enabling {len(self.config.systemd_services)} systemd services")
            for service in self.config.systemd_services:
                subprocess.run(["systemctl", "enable", "--now", service], check=True)
            self.console.success("Systemd services enabled")

        super().install_dependencies()


class Debian(Linux):
    """
    Debian/Ubuntu specific implementation with apt package management.
    """

    def get_os_config(self) -> OSConfig:
        """Return Debian-specific configuration."""
        return DebianConfig()

    def install_dependencies(self):
        """Install Debian/Ubuntu packages using apt."""
        self.console.status("Updating package lists")
        subprocess.run(["sudo", "apt-get", "update"])
        subprocess.run(["sudo", "apt-get", "upgrade", "--assume-yes"])

        self.console.status(f"Installing {len(self.config.apt_packages)} apt packages")
        subprocess.run(
            ["sudo", "apt-get", "install", "--assume-yes"] + self.config.apt_packages,
            check=True,
        )
        self.console.success("Apt packages installed")

        subprocess.run(["sudo", "apt-file", "update"])

        if not exists(expand("./nvim.appimage")):
            self.console.status("Downloading Neovim AppImage")
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
            self.console.success("Neovim AppImage installed")

        super().install_dependencies()


def detect_operating_system(environment="minimal", test_mode=False):
    """Detect and return the appropriate operating system class"""
    try:
        with open("/etc/os-release") as release_file:
            content = release_file.read()
            if 'NAME="Arch Linux"' in content:
                return Arch(environment=environment, test_mode=test_mode)
            elif 'NAME="Garuda Linux"' in content:
                return Arch(environment=environment, test_mode=test_mode)
            elif 'NAME="Debian' in content or 'NAME="Ubuntu' in content:
                return Debian(environment=environment, test_mode=test_mode)
            else:
                raise NotImplementedError(f"Unknown operating system, found {content}")
    except FileNotFoundError:
        raise RuntimeError("Could not detect operating system: /etc/os-release not found")


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

    console = ConsoleOutput()

    try:
        operating_system = detect_operating_system(
            environment=args.environment, test_mode=args.test
        )

        console.status(
            f"Installing dotfiles for {args.environment} environment{' (test mode)' if args.test else ''}"
        )

        console.info("Installing dependencies")
        operating_system.install_dependencies()
        console.info("Linking configurations")
        operating_system.link_configs()
        console.info("Setting up shell")
        operating_system.setup_shell()
        console.info("Link online accounts")
        operating_system.link_accounts()

        console.success("Dotfiles installation completed successfully!")

    except Exception as e:
        console.error(f"Installation failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
