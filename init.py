import argparse
from datetime import datetime
import os
from os.path import abspath, exists, expanduser
import socket
import subprocess
import sys
import time
import traceback
import urllib.request


def expand(path):
    return abspath(expanduser(path))


def run_command_with_error_handling(
    command, description="Command", timeout=300, **kwargs
):
    """Run a subprocess command with comprehensive error handling"""
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            **kwargs,
        )
        return result
    except subprocess.TimeoutExpired as e:
        print(f"❌ ERROR: {description} timed out after {timeout} seconds")
        print(f"🔍 Command: {' '.join(command)}")
        raise
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: {description} failed: {e}")
        print(f"🔍 Command: {' '.join(command)}")
        if e.stdout:
            print(f"📄 STDOUT:\n{e.stdout}")
        if e.stderr:
            print(f"📄 STDERR:\n{e.stderr}")
        raise
    except Exception as e:
        print(f"❌ ERROR: Unexpected error running {description}: {e}")
        print(f"🔍 Command: {' '.join(command)}")
        raise


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

    def validate_git_credential_helper(self):
        """Validate that git credential helper is properly configured"""
        try:
            # Check if libsecret binary exists
            libsecret_path = "/usr/lib/git-core/git-credential-libsecret"
            if not exists(libsecret_path):
                print(
                    f"⚠️  WARNING: git-credential-libsecret not found at {libsecret_path}"
                )
                print("💡 Try: Install libsecret package")
                return False

            # Check if libsecret binary is executable
            if not os.access(libsecret_path, os.X_OK):
                print(f"⚠️  WARNING: git-credential-libsecret is not executable")
                print("💡 Try: chmod +x /usr/lib/git-core/git-credential-libsecret")
                return False

            # Test if credential helper responds
            try:
                result = subprocess.run(
                    [libsecret_path],
                    input="",
                    text=True,
                    capture_output=True,
                    timeout=5,
                )
                # libsecret helper should exit cleanly when given empty input
                print("✅ Git credential helper (libsecret) is properly configured")
                return True
            except subprocess.TimeoutExpired:
                print("⚠️  WARNING: Git credential helper test timed out")
                return False
            except Exception as e:
                print(f"⚠️  WARNING: Error testing git credential helper: {e}")
                return False

        except Exception as e:
            print(f"❌ ERROR: Failed to validate git credential helper: {e}")
            return False

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
                    run_command_with_error_handling(
                        ["chsh", "-s", "/usr/bin/fish"], "Change shell to fish"
                    )
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

        try:
            result = run_command_with_error_handling(
                ["/usr/bin/gh", "auth", "status"], "Check GitHub auth status"
            )
            if "Logged in" not in result.stdout:
                # Interactive command - don't capture output
                subprocess.run(["/usr/bin/gh", "auth", "login"])
                run_command_with_error_handling(
                    [
                        "gh",
                        "auth",
                        "refresh",
                        "-h",
                        "github.com",
                        "-s",
                        "admin:public_key",
                    ],
                    "Refresh GitHub auth",
                )
        except subprocess.CalledProcessError:
            print("GitHub CLI not authenticated, running login...")
            subprocess.run(["/usr/bin/gh", "auth", "login"])
            run_command_with_error_handling(
                ["gh", "auth", "refresh", "-h", "github.com", "-s", "admin:public_key"],
                "Refresh GitHub auth",
            )

        current_key = expand("~/.ssh/id_ed_" + datetime.now().strftime("%Y%m"))
        if not exists(current_key):
            ssh_key_email = self.environment_specific["ssh_key_email"].get(
                self.environment, self.ssh_key_email
            )
            run_command_with_error_handling(
                [
                    "ssh-keygen",
                    "-t",
                    "ed25519",
                    "-C",
                    f"'Patrick Gerken {socket.gethostname()} {ssh_key_email} {datetime.now().strftime('%Y%m')}'",
                    "-f",
                    current_key,
                    "-N",
                    "",  # No passphrase
                ],
                "Generate SSH key",
            )
            run_command_with_error_handling(
                ["ssh-add", current_key], "Add SSH key to agent"
            )
            key_name = f'"{socket.gethostname()} {datetime.now().strftime("%Y%m")}"'
            run_command_with_error_handling(
                ["/usr/bin/gh", "ssh-key", "add", f"{current_key}.pub", "-t", key_name],
                "Add SSH key to GitHub",
            )

        if self.environment in ["private"]:
            try:
                result = run_command_with_error_handling(
                    ["tailscale", "status"], "Check Tailscale status"
                )
                if "Logged in" not in result.stdout:
                    # Interactive command - don't capture output
                    subprocess.run(
                        ["sudo", "tailscale", "login", "--operator=do3cc", "--qr"]
                    )
            except subprocess.CalledProcessError:
                print("Tailscale not logged in, running login...")
                subprocess.run(
                    ["sudo", "tailscale", "login", "--operator=do3cc", "--qr"]
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
        "glab",  # GitLab command line interface
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
                "firefox",  # web browser
                "ghostscript",  # PostScript and PDF interpreter
                "imagemagick",  # image manipulation toolkit
                "noto-fonts-emoji",  # emoji font collection
                "otf-font-awesome",  # icon font
                "python-gobject",  # Python GObject bindings
                "tailscale",  # mesh VPN service
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

    def should_update_system(self):
        """Check if system update should be performed (not done in last 24 hours)"""
        update_marker = expand("~/.cache/dotfiles_last_update")

        if not exists(update_marker):
            return True

        try:
            with open(update_marker, "r") as f:
                last_update_str = f.read().strip()

            last_update = datetime.fromisoformat(last_update_str)
            time_since_update = datetime.now() - last_update

            # Update if more than 24 hours have passed
            return time_since_update.total_seconds() > 24 * 60 * 60

        except (ValueError, OSError):
            # If we can't read/parse the file, assume we should update
            return True

    def mark_system_updated(self):
        """Mark that system update was performed"""
        update_marker = expand("~/.cache/dotfiles_last_update")

        # Ensure cache directory exists
        cache_dir = os.path.dirname(update_marker)
        os.makedirs(cache_dir, exist_ok=True)

        try:
            with open(update_marker, "w") as f:
                f.write(datetime.now().isoformat())
        except OSError as e:
            print(f"⚠️  WARNING: Could not write update marker: {e}")

    def update_system(self):
        """Perform system update if needed"""
        if not self.should_update_system():
            print("✅ System updated within last 24 hours, skipping update")
            return

        print("🔄 Updating system packages...")
        try:
            run_command_with_error_handling(
                ["sudo", "pacman", "-Syu", "--noconfirm"], "System update", timeout=1800
            )
            print("✅ System update completed successfully")
            self.mark_system_updated()
        except Exception:
            print("💡 Try: Run 'sudo pacman -Syu' manually to check for issues")
            raise

    def install_dependencies(self):
        """Install packages with retry logic and comprehensive error handling"""

        # Perform system update if needed
        self.update_system()

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
                    print(f"❌ ERROR: Package installation failed: {e}")
                    print(f"🔍 Command: sudo pacman {' '.join(args)}")
                    if e.stdout:
                        print(f"📄 STDOUT:\n{e.stdout}")
                    if e.stderr:
                        print(f"📄 STDERR:\n{e.stderr}")

                    # Provide specific advice based on error
                    stderr_lower = e.stderr.lower() if e.stderr else ""
                    if "conflict" in stderr_lower:
                        print(
                            "💡 Try: Resolve conflicts manually or update system first"
                        )
                    elif "not found" in stderr_lower:
                        print("💡 Try: Update package databases with 'pacman -Sy'")
                    elif (
                        "permission denied" in stderr_lower
                        or "password" in stderr_lower
                    ):
                        print("💡 Try: Configure sudo or run in interactive terminal")
                    else:
                        print("💡 Try: Check the error details above")
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
                    run_command_with_error_handling(
                        [
                            "git",
                            "clone",
                            "https://aur.archlinux.org/yay-bin.git",
                            yay_dir,
                        ],
                        "Clone yay AUR helper",
                        timeout=120,
                    )

                    print("Building yay...")
                    run_command_with_error_handling(
                        ["makepkg", "-si", "--needed", "--noconfirm"],
                        "Build yay AUR helper",
                        timeout=600,
                        cwd=yay_dir,
                    )
                    print("✅ Yay AUR helper installed")

                except Exception:
                    print("💡 Try: Check internet connection and build dependencies")
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
                        **kwargs,
                    )
                    return result
                except subprocess.TimeoutExpired:
                    print(
                        f"❌ APT operation timed out (attempt {attempt + 1}/{max_retries})"
                    )
                    if attempt == max_retries - 1:
                        print(
                            "💡 Try: Check internet connection or use different mirror"
                        )
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
                        print(
                            "❌ ERROR: Permission denied - sudo may not be configured"
                        )
                        print("💡 Try: Configure sudo or run as appropriate user")
                    elif "failed to fetch" in e.stderr.lower():
                        print("❌ ERROR: Failed to fetch packages")
                        print(
                            "💡 Try: Check internet connection and repository availability"
                        )
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
                    timeout=600,
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
                            headers={"User-Agent": "dotfiles-installer/1.0"},
                        )

                        with urllib.request.urlopen(request, timeout=300) as response:
                            with open(nvim_appimage, "wb") as f:
                                # Download in chunks to handle large files
                                while True:
                                    chunk = response.read(8192)
                                    if not chunk:
                                        break
                                    f.write(chunk)

                        print("✅ Neovim AppImage downloaded successfully")
                        break

                    except urllib.error.URLError as e:
                        print(
                            f"❌ ERROR: Failed to download Neovim (attempt {attempt + 1}/{max_retries}): {e}"
                        )
                        if attempt == max_retries - 1:
                            print(
                                "💡 Try: Check internet connection or download manually"
                            )
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
        elif 'NAME="CachyOS Linux"' in content:
            return Arch(environment=environment, test_mode=test_mode)
        elif 'NAME="Garuda Linux"' in content:
            return Arch(environment=environment, test_mode=test_mode)
        elif "ID=debian" in content or "ID_LIKE=debian" in content:
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
    export DOTFILES_ENVIRONMENT=minimal && uv run init.py   # Install minimal environment
    export DOTFILES_ENVIRONMENT=work && uv run init.py      # Install work environment
    export DOTFILES_ENVIRONMENT=private && uv run init.py   # Install full desktop environment
    DOTFILES_ENVIRONMENT=minimal uv run init.py --test      # Test installation without remote activities

ENVIRONMENT VARIABLE:
    DOTFILES_ENVIRONMENT    Required. Must be set to: minimal, work, or private
                           This prevents accidentally running the wrong environment configuration

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
        # Environment must be set via DOTFILES_ENVIRONMENT environment variable
        # No longer accepting --environment argument to prevent accidental runs
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

        # Get environment from environment variable
        environment = os.environ.get("DOTFILES_ENVIRONMENT")
        if not environment:
            print("❌ ERROR: DOTFILES_ENVIRONMENT environment variable is not set")
            print("")
            print(
                "💡 You must set the environment variable to one of: minimal, work, private"
            )
            print("💡 Examples:")
            print("   export DOTFILES_ENVIRONMENT=minimal && uv run init.py")
            print("   export DOTFILES_ENVIRONMENT=work && uv run init.py")
            print("   export DOTFILES_ENVIRONMENT=private && uv run init.py")
            print("")
            print(
                "💡 This prevents accidentally running the wrong environment configuration"
            )
            return 1

        # Validate environment value
        valid_environments = ["minimal", "work", "private"]
        if environment not in valid_environments:
            print(f"❌ ERROR: Invalid DOTFILES_ENVIRONMENT '{environment}'")
            print(f"💡 Must be one of: {', '.join(valid_environments)}")
            return 1

        print(
            f"🚀 Installing dotfiles for {environment} environment{' (test mode)' if args.test else ''}"
        )

        try:
            operating_system = detect_operating_system(
                environment=environment, test_mode=args.test
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
            (
                "Validating git credential helper",
                operating_system.validate_git_credential_helper,
            ),
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
                print("\n🔍 DETAILED ERROR INFORMATION:")
                print("-" * 50)
                traceback.print_exc()
                print("-" * 50)
                print("💡 Check the error details above and retry")
                return 1

        print("\n🎉 Dotfiles installation completed successfully!")
        print(
            "💡 You may need to restart your terminal or run 'source ~/.config/fish/config.fish' for changes to take effect"
        )
        return 0

    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("\n🔍 DETAILED ERROR INFORMATION:")
        print("-" * 50)
        traceback.print_exc()
        print("-" * 50)
        print("💡 Please report this issue with the full error message")
        return 1


if __name__ == "__main__":
    sys.exit(main())
