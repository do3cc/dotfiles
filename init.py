import argparse
from datetime import datetime
import os
from os.path import abspath, exists, expanduser
import socket
import subprocess
import sys
import time
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
        """Install NVM and Pyenv with proper error handling"""
        # Install NVM
        nvm_path = expand("~/.local/share/nvm")
        if not exists(nvm_path):
            try:
                print("Installing NVM...")
                nvm_script = expand("./install_scripts/install_nvm.sh")
                if not exists(nvm_script):
                    print("❌ ERROR: NVM installation script not found")
                    print(f"💡 Expected: {nvm_script}")
                    raise FileNotFoundError(f"NVM script not found: {nvm_script}")

                result = subprocess.run(
                    ["/usr/bin/bash", nvm_script],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )
                print("✅ NVM installed successfully")
            except subprocess.TimeoutExpired:
                print("❌ ERROR: NVM installation timed out (network issues?)")
                print("💡 Try: Check internet connection and run again")
                raise
            except subprocess.CalledProcessError as e:
                print(
                    f"❌ ERROR: NVM installation failed with exit code {e.returncode}"
                )
                if e.stderr:
                    print(f"💡 Error output: {e.stderr}")
                print("💡 Try: Check network connection and script permissions")
                raise
            except FileNotFoundError as e:
                if "/usr/bin/bash" in str(e):
                    print("❌ ERROR: Bash not found at /usr/bin/bash")
                    print("💡 Try: Install bash or update the script")
                else:
                    print(f"❌ ERROR: {e}")
                raise
        else:
            print("✅ NVM already installed")

        # Install Pyenv
        pyenv_path = expand("~/.config/pyenv")
        if not exists(pyenv_path):
            try:
                print("Installing Pyenv...")
                pyenv_script = expand("./install_scripts/install_pyenv.sh")
                if not exists(pyenv_script):
                    print("❌ ERROR: Pyenv installation script not found")
                    print(f"💡 Expected: {pyenv_script}")
                    raise FileNotFoundError(f"Pyenv script not found: {pyenv_script}")

                subprocess.run(
                    ["/usr/bin/bash", pyenv_script],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                print("✅ Pyenv installed successfully")
            except subprocess.TimeoutExpired:
                print("❌ ERROR: Pyenv installation timed out")
                print("💡 Try: Check internet connection and run again")
                raise
            except subprocess.CalledProcessError as e:
                print(
                    f"❌ ERROR: Pyenv installation failed with exit code {e.returncode}"
                )
                if e.stderr:
                    print(f"💡 Error output: {e.stderr}")
                raise
            except FileNotFoundError as e:
                print(f"❌ ERROR: {e}")
                raise
        else:
            print("✅ Pyenv already installed")

    def link_configs(self):
        """Create symlinks with comprehensive error handling"""
        # Ensure ~/.config exists
        config_base_dir = expand("~/.config")
        try:
            ensure_path(config_base_dir)
        except OSError as e:
            print(f"❌ ERROR: Cannot create ~/.config directory: {e}")
            print("💡 Try: Check home directory permissions")
            raise

        for config_dir_src, config_dir_target in (
            self.config_dirs
            + self.environment_specific["config_dirs"].get(self.environment, [])
        ):
            target_path = expand(f"~/.config/{config_dir_target}")
            source_path = expand(f"./{config_dir_src}")

            try:
                # Verify source exists
                if not exists(source_path):
                    print(f"❌ ERROR: Source directory {source_path} does not exist")
                    print(f"💡 Expected config directory: {config_dir_src}")
                    continue

                if not exists(target_path):
                    try:
                        os.symlink(source_path, target_path)
                        print(f"✅ Linked {config_dir_target}")
                    except OSError as e:
                        if e.errno == 13:  # Permission denied
                            print(
                                f"❌ ERROR: Permission denied creating symlink for {config_dir_target}"
                            )
                            print(
                                "💡 Try: Check ~/.config directory ownership and permissions"
                            )
                        elif e.errno == 17:  # File exists (race condition)
                            print(
                                f"⚠️  WARNING: {config_dir_target} was created by another process"
                            )
                        elif e.errno == 30:  # Read-only file system
                            print(
                                f"❌ ERROR: Cannot create symlink on read-only filesystem for {config_dir_target}"
                            )
                        else:
                            print(
                                f"❌ ERROR: Failed to create symlink for {config_dir_target}: {e}"
                            )
                        continue
                else:
                    # Check if it's a directory or symlink to another location
                    if os.path.isdir(target_path):
                        if os.path.islink(target_path):
                            # It's a symlink to a directory
                            try:
                                current_target = os.readlink(target_path)
                                expected_target = source_path
                                if current_target != expected_target:
                                    print(
                                        f"⚠️  WARNING: {config_dir_target} is linked to {current_target}, "
                                        f"but should be linked to {expected_target}"
                                    )
                                else:
                                    print(
                                        f"✅ {config_dir_target} is already correctly linked"
                                    )
                            except OSError as e:
                                print(
                                    f"⚠️  WARNING: Could not read symlink for {config_dir_target}: {e}"
                                )
                        else:
                            # It's a regular directory
                            print(
                                f"⚠️  WARNING: {config_dir_target} exists as a directory, "
                                f"but should be a symlink to {source_path}"
                            )
                    else:
                        # It's a file (not a directory)
                        print(
                            f"⚠️  WARNING: {config_dir_target} exists as a file, "
                            f"but should be a symlink to {source_path}"
                        )
            except Exception as e:
                print(f"❌ ERROR: Unexpected error processing {config_dir_target}: {e}")
                continue

    def setup_shell(self):
        # Check current user's default shell
        try:
            current_shell = os.environ.get("SHELL", "")
            if not current_shell.endswith("/fish"):
                # Double-check by reading from /etc/passwd
                import pwd

                user_entry = pwd.getpwuid(os.getuid())
                if not user_entry.pw_shell.endswith("/fish"):
                    print(f"Changing shell from {user_entry.pw_shell} to fish")
                    subprocess.run(["chsh", "-s", "/usr/bin/fish"], check=True)
                else:
                    print("Shell is already set to fish")
            else:
                print("Shell is already set to fish")
        except Exception as e:
            print(f"Warning: Could not check/change shell: {e}")

    def link_accounts(self):
        if self.test_mode:
            print("Test mode: Skipping GitHub and SSH key setup")
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
    aur_packages = [
        "google-java-format",  # Java formatting tool
        "nodejs-markdown-toc",  # TOC Generator in javascript
    ]
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
        "config_dirs": Linux.environment_specific["config_dirs"],
        "ssh_key_email": Linux.environment_specific["ssh_key_email"],
    }
    systemd_services_to_enable = []

    def install_dependencies(self):
        """Install packages with retry logic and comprehensive error handling"""

        def pacman(*args, **kwargs):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = subprocess.run(
                        ["sudo", "pacman"] + list(args),
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=1800,  # 30 minute timeout
                        **kwargs,
                    )
                    return result
                except subprocess.TimeoutExpired:
                    print(
                        f"❌ Package installation timed out (attempt {attempt + 1}/{max_retries})"
                    )
                    if attempt == max_retries - 1:
                        print(
                            "💡 Try: Check internet connection or use different mirror"
                        )
                        raise
                    print("🔄 Retrying in 10 seconds...")
                    time.sleep(10)
                except subprocess.CalledProcessError as e:
                    if "conflict" in e.stderr.lower():
                        print("❌ ERROR: Package conflicts detected")
                        print(
                            "💡 Try: Resolve conflicts manually or update system first"
                        )
                    elif "not found" in e.stderr.lower():
                        print("❌ ERROR: Package not found in repositories")
                        print("💡 Try: Update package databases with 'pacman -Sy'")
                    elif "permission denied" in e.stderr.lower():
                        print(
                            "❌ ERROR: Permission denied - sudo may not be configured"
                        )
                        print("💡 Try: Configure sudo or run as appropriate user")
                    else:
                        print(f"❌ ERROR: Package installation failed: {e.stderr}")
                    raise

        try:
            # Install base packages
            print("Installing base development tools...")
            pacman("-S", "--needed", "git", "base-devel")
            print("✅ Base development tools installed")

            # Create projects directory safely
            projects_dir = expand("~/projects")
            try:
                ensure_path(projects_dir)
            except OSError as e:
                print(f"❌ ERROR: Cannot create projects directory: {e}")
                print("💡 Try: Check home directory permissions")
                raise

            # Install yay with error handling
            yay_dir = expand("~/projects/yay-bin")
            if not exists(yay_dir):
                try:
                    print("Cloning yay AUR helper...")
                    subprocess.run(
                        [
                            "git",
                            "clone",
                            "https://aur.archlinux.org/yay-bin.git",
                            yay_dir,
                        ],
                        check=True,
                        timeout=120,
                        capture_output=True,
                        text=True,
                    )

                    print("Building yay...")
                    subprocess.run(
                        ["makepkg", "-si", "--needed", "--noconfirm"],
                        check=True,
                        cwd=yay_dir,
                        timeout=600,
                        capture_output=True,
                        text=True,
                    )
                    print("✅ Yay AUR helper installed")

                except subprocess.TimeoutExpired:
                    print("❌ ERROR: Git clone or yay build timed out")
                    print("💡 Try: Check internet connection")
                    raise
                except subprocess.CalledProcessError as e:
                    print(f"❌ ERROR: Failed to install yay: {e}")
                    if e.stderr:
                        print(f"💡 Error details: {e.stderr}")
                    raise
            else:
                print("✅ Yay already installed")

            # Install main packages with detailed progress
            all_packages = self.pacman_packages + self.environment_specific[
                "pacman_packages"
            ].get(self.environment, [])
            print(f"Installing {len(all_packages)} pacman packages...")

            try:
                pacman("-S", "--needed", "--noconfirm", *all_packages)
                print("✅ All pacman packages installed successfully")
            except subprocess.CalledProcessError as e:
                print("❌ ERROR: Some pacman packages failed to install")
                print("💡 Try: Check package names and update system")
                raise e

            # Install AUR packages
            aur_packages = self.aur_packages + self.environment_specific[
                "aur_packages"
            ].get(self.environment, [])
            if aur_packages:
                print(f"Installing {len(aur_packages)} AUR packages...")
                try:
                    subprocess.run(
                        ["yay", "-S", "--needed", "--noconfirm"] + aur_packages,
                        check=True,
                        timeout=1800,
                        capture_output=True,
                        text=True,
                    )
                    print("✅ All AUR packages installed successfully")
                except subprocess.TimeoutExpired:
                    print("❌ ERROR: AUR package installation timed out")
                    raise
                except subprocess.CalledProcessError as e:
                    print("❌ ERROR: Some AUR packages failed to install")
                    if e.stderr:
                        print(f"💡 Error details: {e.stderr}")
                    raise

            # Enable systemd services
            services_to_enable = (
                self.systemd_services_to_enable
                + self.environment_specific["systemd_services_to_enable"].get(
                    self.environment, []
                )
            )
            for service in services_to_enable:
                try:
                    subprocess.run(
                        ["systemctl", "enable", "--now", service],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    print(f"✅ Enabled service: {service}")
                except subprocess.CalledProcessError as e:
                    # In containers, systemd services often fail - this is expected
                    if (
                        "chroot" in e.stderr.lower()
                        or "failed to connect to bus" in e.stderr.lower()
                    ):
                        print(
                            f"⚠️  WARNING: Cannot enable {service} in container environment"
                        )
                    else:
                        print(
                            f"❌ ERROR: Failed to enable service {service}: {e.stderr}"
                        )
                        # Don't raise here - continue with other services

        except KeyboardInterrupt:
            print("\n❌ Installation interrupted by user")
            raise
        except Exception as e:
            print(f"❌ FATAL ERROR during package installation: {e}")
            print("💡 Try: Check logs above for specific error details")
            raise

        # Call parent class
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
        """Install packages with retry logic and comprehensive error handling"""
        
        def apt_get(*args, **kwargs):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = subprocess.run(
                        ["sudo", "apt-get"] + list(args),
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=1800,  # 30 minute timeout
                        **kwargs
                    )
                    return result
                except subprocess.TimeoutExpired:
                    print(f"❌ APT operation timed out (attempt {attempt + 1}/{max_retries})")
                    if attempt == max_retries - 1:
                        print("💡 Try: Check internet connection or use different mirror")
                        raise
                    print("🔄 Retrying in 10 seconds...")
                    time.sleep(10)
                except subprocess.CalledProcessError as e:
                    if "unable to lock" in e.stderr.lower():
                        print("❌ ERROR: APT database is locked")
                        print("💡 Try: Wait for other package operations to complete")
                    elif "no space left" in e.stderr.lower():
                        print("❌ ERROR: No space left on device")
                        print("💡 Try: Free up disk space and try again")
                    elif "permission denied" in e.stderr.lower():
                        print("❌ ERROR: Permission denied - sudo may not be configured")
                        print("💡 Try: Configure sudo or run as appropriate user")
                    elif "failed to fetch" in e.stderr.lower():
                        print("❌ ERROR: Failed to fetch packages")
                        print("💡 Try: Check internet connection and repository availability")
                    else:
                        print(f"❌ ERROR: APT operation failed: {e.stderr}")
                    raise

        try:
            # Update package databases
            print("Updating package databases...")
            apt_get("update")
            print("✅ Package databases updated")

            # Upgrade existing packages
            print("Upgrading existing packages...")
            try:
                apt_get("upgrade", "--assume-yes")
                print("✅ System packages upgraded")
            except subprocess.CalledProcessError as e:
                print("⚠️  WARNING: Some packages failed to upgrade")
                print("💡 This is often non-critical, continuing with installation...")

            # Install main packages
            print(f"Installing {len(self.apt_packages)} APT packages...")
            try:
                apt_get("install", "--assume-yes", *self.apt_packages)
                print("✅ All APT packages installed successfully")
            except subprocess.CalledProcessError as e:
                print("❌ ERROR: Some APT packages failed to install")
                print("💡 Try: Check package names and fix any dependency conflicts")
                raise

            # Update apt-file database
            print("Updating apt-file database...")
            try:
                subprocess.run(
                    ["sudo", "apt-file", "update"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                print("✅ Apt-file database updated")
            except subprocess.CalledProcessError as e:
                print("⚠️  WARNING: apt-file update failed")
                print("💡 This is non-critical, continuing...")
            except subprocess.TimeoutExpired:
                print("⚠️  WARNING: apt-file update timed out")
                print("💡 This is non-critical, continuing...")

            # Download and install latest Neovim AppImage
            nvim_appimage = expand("./nvim.appimage")
            if not exists(nvim_appimage):
                print("Downloading latest Neovim AppImage...")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        import urllib.request
                        import urllib.error
                        
                        # Download with timeout
                        request = urllib.request.Request(
                            "https://github.com/neovim/neovim/releases/latest/download/nvim.appimage",
                            headers={'User-Agent': 'dotfiles-installer/1.0'}
                        )
                        
                        with urllib.request.urlopen(request, timeout=300) as response:
                            with open(nvim_appimage, 'wb') as f:
                                # Download in chunks to handle large files
                                while True:
                                    chunk = response.read(8192)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                        
                        print("✅ Neovim AppImage downloaded successfully")
                        break
                        
                    except urllib.error.URLError as e:
                        print(f"❌ ERROR: Failed to download Neovim (attempt {attempt + 1}/{max_retries}): {e}")
                        if attempt == max_retries - 1:
                            print("💡 Try: Check internet connection or download manually")
                            raise
                        print("🔄 Retrying in 5 seconds...")
                        time.sleep(5)
                    except Exception as e:
                        print(f"❌ ERROR: Unexpected error downloading Neovim: {e}")
                        raise

                # Make AppImage executable
                try:
                    os.chmod(nvim_appimage, 0o755)
                    print("✅ Neovim AppImage made executable")
                except OSError as e:
                    print(f"❌ ERROR: Failed to make Neovim executable: {e}")
                    raise

                # Create ~/bin directory
                bin_dir = expand("~/bin")
                try:
                    ensure_path(bin_dir)
                    print("✅ ~/bin directory created")
                except OSError as e:
                    print(f"❌ ERROR: Cannot create ~/bin directory: {e}")
                    print("💡 Try: Check home directory permissions")
                    raise

                # Create symlink to nvim
                nvim_symlink = expand("~/bin/nvim")
                if not exists(nvim_symlink):
                    try:
                        os.symlink(nvim_appimage, nvim_symlink)
                        print("✅ Neovim symlink created in ~/bin/nvim")
                    except OSError as e:
                        print(f"❌ ERROR: Failed to create Neovim symlink: {e}")
                        print("💡 Try: Check ~/bin directory permissions")
                        raise
                else:
                    print("✅ Neovim symlink already exists")
            else:
                print("✅ Neovim AppImage already exists")

        except KeyboardInterrupt:
            print("\n❌ Installation interrupted by user")
            raise
        except Exception as e:
            print(f"❌ FATAL ERROR during package installation: {e}")
            print("💡 Try: Check logs above for specific error details")
            raise

        # Call parent class
        super().install_dependencies()


def detect_operating_system(environment="minimal", test_mode=False):
    """Detect and return the appropriate operating system class"""
    with open("/etc/os-release") as release_file:
        content = release_file.read()
        if 'NAME="Arch Linux"' in content:
            return Arch(environment=environment, test_mode=test_mode)
        elif 'NAME="Garuda Linux"' in content:
            return Arch(environment=environment, test_mode=test_mode)
        elif 'ID=debian' in content or 'ID_LIKE=debian' in content:
            return Debian(environment=environment, test_mode=test_mode)
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
    """Main entry point with comprehensive error handling"""
    try:
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
            return 0

        print(
            f"🚀 Installing dotfiles for {args.environment} environment{' (test mode)' if args.test else ''}"
        )

        try:
            operating_system = detect_operating_system(
                environment=args.environment, test_mode=args.test
            )
        except FileNotFoundError:
            print(
                "❌ ERROR: Cannot detect operating system (/etc/os-release not found)"
            )
            print("💡 This script only supports Linux distributions")
            return 1
        except NotImplementedError as e:
            print(f"❌ ERROR: {e}")
            print(
                "💡 This script currently supports Arch Linux, Garuda Linux, and Debian-based systems"
            )
            return 1

        # Execute installation steps with individual error handling
        steps = [
            ("Installing dependencies", operating_system.install_dependencies),
            ("Linking configurations", operating_system.link_configs),
            ("Setting up shell", operating_system.setup_shell),
            ("Setting up accounts", operating_system.link_accounts),
        ]

        for step_name, step_func in steps:
            try:
                print(f"\n🔄 {step_name}...")
                step_func()
                print(f"✅ {step_name} completed successfully")
            except KeyboardInterrupt:
                print(f"\n❌ {step_name} interrupted by user")
                return 130  # Standard exit code for SIGINT
            except Exception as e:
                print(f"❌ ERROR in {step_name}: {e}")
                print("💡 Check the error details above and retry")
                return 1

        print("\n🎉 Dotfiles installation completed successfully!")
        print(
            "💡 You may need to restart your terminal or run 'source ~/.config/fish/config.fish' for changes to take effect"
        )
        return 0

    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("💡 Please report this issue with the full error message")
        return 1


if __name__ == "__main__":
    sys.exit(main())
