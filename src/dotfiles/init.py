# pyright: strict
from subprocess import CalledProcessError, TimeoutExpired, CompletedProcess
from dataclasses import dataclass, field
from datetime import datetime
import os
from os.path import abspath, exists, expanduser
from .process_helper import run_command_with_error_handling
from pathlib import Path
import socket
import sys
import time
import traceback
import urllib.request
import urllib.error
import click
from .logging_config import (
    setup_logging,
    LoggingHelpers,
)
from .output_formatting import ConsoleOutput
from .swman import DebianSystemManager, PacmanManager

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable


def expand(path: str) -> str:
    return abspath(expanduser(path))


def ensure_path(path: str) -> None:
    if not exists(expand(path)):
        os.makedirs(expand(path))


@dataclass
class EnvironmentConfig:
    """Type-safe configuration for a specific environment."""

    # Package management
    packages: list[str] = field(default_factory=list[str])
    aur_packages: list[str] = field(default_factory=list[str])

    # Configuration directories: (source_dir, target_dir)
    config_dirs: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])

    # System services to enable
    systemd_services: list[str] = field(default_factory=list[str])

    # Environment-specific overrides
    ssh_key_email: str | None = None

    def merge_with(self, base_config: "EnvironmentConfig") -> "EnvironmentConfig":
        """Merge this config with a base, with this taking priority."""
        return EnvironmentConfig(
            packages=base_config.packages + self.packages,
            aur_packages=base_config.aur_packages + self.aur_packages,
            config_dirs=base_config.config_dirs + self.config_dirs,
            systemd_services=base_config.systemd_services + self.systemd_services,
            ssh_key_email=self.ssh_key_email or base_config.ssh_key_email,
        )


class Linux:
    def __init__(self, environment: str = "minimal", no_remote_mode: bool = False):
        self.environment = environment
        self.no_remote_mode = no_remote_mode
        # Single source of truth for this environment's configuration
        self.config = self._build_environment_config(environment)

    def _get_base_config(self) -> EnvironmentConfig:
        """Get base configuration for Linux systems."""
        return EnvironmentConfig(
            config_dirs=[
                ("alacritty", "alacritty"),
                ("direnv", "direnv"),
                ("fish", "fish"),
                ("lazy_nvim", "nvim"),
                ("tmux", "tmux"),
                ("git", "git"),
            ],
            ssh_key_email="sshkeys@patrick-gerken.de",
        )

    def _get_environment_configs(self) -> dict[str, EnvironmentConfig]:
        """Get environment-specific configurations."""
        return {
            "private": EnvironmentConfig(
                config_dirs=[("irssi", "irssi")],
            ),
            "work": EnvironmentConfig(
                ssh_key_email="patrick.gerken@zumtobelgroup.com",
            ),
        }

    def _build_environment_config(self, environment: str) -> EnvironmentConfig:
        """Build complete configuration for an environment."""
        base = self._get_base_config()
        env_configs = self._get_environment_configs()
        env_specific = env_configs.get(environment, EnvironmentConfig())
        return env_specific.merge_with(base)

    def check_systemd_service_status(
        self, service: str, logger: LoggingHelpers, output: ConsoleOutput
    ) -> tuple[bool, bool]:
        """Check if a systemd service is enabled and active"""
        try:
            # Check if service is enabled
            enabled_result = run_command_with_error_handling(
                ["systemctl", "is-enabled", service],
                logger,
                output,
                "systemctl is-enabled",
            )
            is_enabled = (
                enabled_result.returncode == 0 and "enabled" in enabled_result.stdout
            )

            # Check if service is active
            active_result = run_command_with_error_handling(
                ["systemctl", "is-active", service],
                logger,
                output,
                "systemctl is-active",
            )
            is_active = (
                active_result.returncode == 0 and "active" in active_result.stdout
            )

            return is_enabled, is_active
        except Exception as e:
            logger.log_exception(e, "systemd_service_check_failed", service=service)
            # If systemctl check fails, assume service needs setup
            return False, False

    def install_dependencies(self, logger: LoggingHelpers, output: ConsoleOutput):
        """Install NVM and Pyenv with proper error handling"""
        logger.log_progress("starting_dependency_installation")

        # Install NVM
        nvm_path = expand("~/.local/share/nvm")
        logger = logger.bind(nvm_path=nvm_path)
        logger.log_info("checking_nvm_installation")

        if not exists(nvm_path):
            nvm_script = "doesnotexist"
            try:
                output.status("Installing NVM...", logger=logger)
                nvm_script = expand("./install_scripts/install_nvm.sh")
                logger = logger.bind(nvm_script_path=nvm_script)

                if not exists(nvm_script):
                    output.error("NVM installation script not found", logger=logger)
                    output.info(f"Expected: {nvm_script}")
                    raise FileNotFoundError(f"NVM script not found: {nvm_script}")

                run_command_with_error_handling(
                    ["/usr/bin/bash", nvm_script], logger, output
                )
                logger.log_progress("nvm_installed_successfully")
                output.success("NVM installed successfully")

            except TimeoutExpired as e:
                logger.log_exception(e, "nvm_installation_timeout", timeout=300)
                output.error("NVM installation timed out (network issues?)")
                output.info("Try: Check internet connection and run again")
                raise
            except CalledProcessError as e:
                logger.log_exception(
                    e,
                    "nvm_installation_failed",
                    returncode=e.returncode,
                    stdout=e.stdout,
                    stderr=e.stderr,
                )
                output.error(f"NVM installation failed with exit code {e.returncode}")
                if e.stderr:
                    output.info(f"Error output: {e.stderr}")
                output.info("Try: Check network connection and script permissions")
                raise
            except FileNotFoundError as e:
                logger.log_exception(
                    e, "NVM installation file not found", script_path=nvm_script
                )
                if "/usr/bin/bash" in str(e):
                    output.error("Bash not found at /usr/bin/bash")
                    output.info("Try: Install bash or update the script")
                else:
                    output.error(f"{e}")
                raise
        else:
            logger.log_info("nvm_already_installed")
            output.success("NVM already installed")

        # Install Pyenv
        pyenv_path = expand("~/.config/pyenv")
        if not exists(pyenv_path):
            try:
                output.status("Installing Pyenv...")
                pyenv_script = expand("./install_scripts/install_pyenv.sh")
                logger = logger.bind(pyenv_script=pyenv_script)
                if not exists(pyenv_script):
                    output.error(
                        "ERROR: Pyenv installation script not found", logger=logger
                    )
                    output.info(f"Expected: {pyenv_script}")
                    raise FileNotFoundError(f"Pyenv script not found: {pyenv_script}")

                run_command_with_error_handling(
                    ["/usr/bin/bash", pyenv_script], logger, output
                )
                output.success("Pyenv installed successfully", logger=logger)
            except TimeoutExpired:
                output.error("ERROR: Pyenv installation timed out", logger=logger)
                output.info("Try: Check internet connection and run again")
                raise
            except CalledProcessError as e:
                output.error(
                    f"ERROR: Pyenv installation failed with exit code {e.returncode}",
                    logger=logger,
                )
                if e.stderr:
                    output.info(f"Error output: {e.stderr}")
                raise
            except FileNotFoundError as e:
                output.error(f"ERROR: {e}", logger=logger)
                raise
        else:
            output.success("Pyenv already installed", logger=logger)

        # Install dotfiles package globally via uv tool
        logger.log_progress("installing_dotfiles_package_globally")
        try:
            output.status(
                "Installing dotfiles package to ~/.local/bin...", logger=logger
            )
            run_command_with_error_handling(
                ["uv", "tool", "install", "--editable", "."], logger, output
            )
            output.success(
                "Dotfiles package installed globally to ~/.local/bin", logger=logger
            )
        except CalledProcessError as e:
            logger.log_exception(
                e,
                "dotfiles_package_installation_failed",
                returncode=e.returncode,
                stdout=e.stdout,
                stderr=e.stderr,
            )
            output.error(f"Failed to install dotfiles package: {e}")
            if e.stderr:
                output.info(f"Error output: {e.stderr}", emoji="💡")
            output.info(
                "Try: Ensure uv is properly installed and configured", emoji="💡"
            )
            raise
        except TimeoutExpired as e:
            logger.log_exception(e, "dotfiles_package_installation_timeout", timeout=60)
            output.error("Dotfiles package installation timed out")
            output.info("Try: Check internet connection and try again", emoji="💡")
            raise
        except FileNotFoundError as e:
            logger.log_exception(e, "uv_command_not_found")
            output.error("uv command not found")
            output.info("Try: Install uv first or ensure it's in PATH", emoji="💡")
            raise

    def link_configs(self, logger: LoggingHelpers, output: ConsoleOutput):
        """Create symlinks with comprehensive error handling"""
        # Ensure ~/.config exists
        config_base_dir = expand("~/.config")
        try:
            ensure_path(config_base_dir)
        except OSError as e:
            output.error(
                f"ERROR: Cannot create {config_base_dir} directory: {e}", logger=logger
            )
            output.info("Try: Check home directory permissions", emoji="💡")
            raise

        for config_dir_src, config_dir_target in self.config.config_dirs:
            target_path = expand(f"~/.config/{config_dir_target}")
            source_path = expand(f"./{config_dir_src}")
            logger = logger.bind(target_path=target_path, source_path=source_path)

            try:
                # Verify source exists
                if not exists(source_path):
                    output.error(
                        f"Source directory {source_path} does not exist", logger=logger
                    )
                    output.info(
                        f"Expected config directory: {config_dir_src}", emoji="💡"
                    )
                    continue

                if not exists(target_path):
                    try:
                        os.symlink(source_path, target_path)
                        output.success(f"Linked {config_dir_target}", logger=logger)
                        self.restart_required = True
                    except OSError as e:
                        if e.errno == 13:  # Permission denied
                            output.error(
                                f"Permission denied creating symlink for {config_dir_target}",
                                logger=logger,
                            )
                            output.info(
                                "Try: Check ~/.config directory ownership and permissions",
                                emoji="💡",
                            )
                        elif e.errno == 17:  # File exists (race condition)
                            output.warning(
                                f"{config_dir_target} was created by another process",
                                logger=logger,
                            )
                        elif e.errno == 30:  # Read-only file system
                            output.error(
                                f"Cannot create symlink on read-only filesystem for {config_dir_target}",
                                logger=logger,
                            )
                        else:
                            logger.log_exception(e, "symlink_creation_failed")
                            output.error(
                                f"Failed to create symlink for {config_dir_target}: {e}"
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
                                    output.warning(
                                        f"{config_dir_target} is linked to {current_target}, but should be linked to {expected_target}",
                                        logger=logger,
                                    )
                                else:
                                    output.success(
                                        f"{config_dir_target} is already correctly linked",
                                        logger=logger,
                                    )
                            except OSError as e:
                                logger.log_exception(e, "symlink_read_failed")
                                output.warning(
                                    f"Could not read symlink for {config_dir_target}: {e}"
                                )
                        else:
                            # It's a regular directory
                            output.warning(
                                f"{config_dir_target} exists as a directory, but should be a symlink to {source_path}",
                                logger=logger,
                            )
                    else:
                        # It's a file (not a directory)
                        output.warning(
                            f"{config_dir_target} exists as a file, but should be a symlink to {source_path}",
                            logger=logger,
                        )
            except Exception as e:
                logger.log_exception(e, "config_linking_unexpected_error")
                output.error(f"Unexpected error processing {config_dir_target}: {e}")
                continue

    def validate_git_credential_helper(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> bool:
        """Validate that git credential helper is properly configured"""
        try:
            # Check if libsecret binary exists
            libsecret_path = "/usr/lib/git-core/git-credential-libsecret"
            logger = logger.bind(libsecret_path=libsecret_path)
            if not exists(libsecret_path):
                output.warning(
                    f"WARNING: git-credential-libsecret not found at {libsecret_path}",
                    logger=logger,
                )
                output.info("Try: Install libsecret package", emoji="💡")
                return False

            # Check if libsecret binary is executable
            if not os.access(libsecret_path, os.X_OK):
                output.warning(
                    "git-credential-libsecret is not executable", logger=logger
                )
                output.info(
                    "Try: chmod +x /usr/lib/git-core/git-credential-libsecret",
                    emoji="💡",
                )
                return False

            # Test if credential helper responds
            try:
                run_command_with_error_handling(
                    [libsecret_path], logger, output, timeout=5, input=""
                )
                # libsecret helper should exit cleanly when given empty input
                output.success(
                    "Git credential helper (libsecret) is properly configured",
                    logger=logger,
                )
                return True
            except TimeoutExpired:
                output.warning("Git credential helper test timed out", logger=logger)
                return False
            except Exception as e:
                output.warning(
                    f"Error testing git credential helper: {e}", logger=logger
                )
                return False

        except Exception as e:
            logger.log_exception(e, "git_credential_helper_validation_failed")
            output.error(f"Failed to validate git credential helper: {e}")
            return False

    def setup_shell(self, logger: LoggingHelpers, output: ConsoleOutput):
        # Check current user's default shell
        try:
            current_shell = os.environ.get("SHELL", "")
            if not current_shell.endswith("/fish"):
                # Double-check by reading from /etc/passwd
                import pwd

                user_entry = pwd.getpwuid(os.getuid())
                if not user_entry.pw_shell.endswith("/fish"):
                    output.status(
                        f"Changing shell from {user_entry.pw_shell} to fish",
                        logger=logger,
                    )
                    run_command_with_error_handling(
                        ["chsh", "-s", "/usr/bin/fish"],
                        logger,
                        output,
                        "Change shell to fish",
                    )
                    self.restart_required = True
                else:
                    output.success("Shell is already set to fish", logger=logger)
            else:
                output.success("Shell is already set to fish", logger=logger)
        except Exception as e:
            logger.log_exception(e, "shell_setup_failed")
            output.warning(f"Could not check/change shell: {e}")

    def link_accounts(self, logger: LoggingHelpers, output: ConsoleOutput):
        if self.no_remote_mode:
            output.info(
                "No-remote mode: Skipping GitHub and SSH key setup", logger=logger
            )
            return

        try:
            result = run_command_with_error_handling(
                ["/usr/bin/gh", "auth", "status"],
                logger,
                output,
                "Check GitHub auth status",
            )
            if "Logged in" not in result.stdout:
                # Interactive command - don't capture output
                run_command_with_error_handling(
                    ["/usr/bin/gh", "auth", "login"], logger, output, "Log in to github"
                )
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
                    logger,
                    output,
                    "Refresh GitHub auth",
                )
        except CalledProcessError:
            output.status(
                "GitHub CLI not authenticated, running login...", logger=logger
            )
            run_command_with_error_handling(
                ["/usr/bin/gh", "auth", "login"], logger, output, "Log in to github"
            )
            run_command_with_error_handling(
                ["gh", "auth", "refresh", "-h", "github.com", "-s", "admin:public_key"],
                logger,
                output,
                "Refresh GitHub auth",
            )

        # Use permanent SSH key based on hostname and environment
        key_suffix = f"{socket.gethostname()}_{self.environment}"
        current_key = expand(f"~/.ssh/id_ed25519_{key_suffix}")

        if not exists(current_key):
            ssh_key_email = self.config.ssh_key_email
            run_command_with_error_handling(
                [
                    "ssh-keygen",
                    "-t",
                    "ed25519",
                    "-C",
                    f"'Patrick Gerken {socket.gethostname()} {ssh_key_email} {self.environment}'",
                    "-f",
                    current_key,
                    "-N",
                    "",  # No passphrase
                ],
                logger,
                output,
                "Generate SSH key",
            )
            run_command_with_error_handling(
                ["ssh-add", current_key], logger, output, "Add SSH key to agent"
            )

            # Create default SSH key symlink for automatic loading
            default_key_link = expand("~/.ssh/id_ed25519_default")
            if not exists(default_key_link):
                try:
                    os.symlink(current_key, default_key_link)
                    output.success(
                        f"Created SSH key symlink: id_ed25519_default -> {os.path.basename(current_key)}",
                        logger=logger,
                    )
                except OSError as e:
                    logger.log_exception(e, "ssh_key_symlink_creation_failed")
                    output.error(f"Could not create SSH key symlink: {e}")

            key_name = f'"{socket.gethostname()} {self.environment}"'
            run_command_with_error_handling(
                ["/usr/bin/gh", "ssh-key", "add", f"{current_key}.pub", "-t", key_name],
                logger,
                output,
                "Add SSH key to GitHub",
            )

        if self.environment in ["private"]:
            try:
                result = run_command_with_error_handling(
                    ["tailscale", "status"], logger, output, "Check Tailscale status"
                )
                logger = logger.bind(tailscale_status=result.stdout)
                # Check if we have an IP address (connected) or if we're logged out
                if "100." not in result.stdout or "Logged out" in result.stdout:
                    output.status(
                        "Tailscale not connected, running setup...", logger=logger
                    )
                    # Use 'tailscale up' for locked tailnets instead of login
                    run_command_with_error_handling(
                        ["sudo", "tailscale", "up", "--operator=do3cc"], logger, output
                    )
                else:
                    output.success("Tailscale is connected", logger=logger)
            except CalledProcessError:
                output.status(
                    "Tailscale not available, running setup...", logger=logger
                )
                run_command_with_error_handling(
                    ["sudo", "tailscale", "up", "--operator=do3cc"], logger, output
                )


class Arch(Linux):
    def _get_base_config(self) -> EnvironmentConfig:
        """Get base configuration for Arch Linux systems."""
        base = super()._get_base_config()
        arch_config = EnvironmentConfig(
            packages=[
                "ast-grep",  # structural code search tool
                "bat",  # syntax highlighted cat alternative
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
                "pacman-contrib",  # pacman utilities including checkupdates
                "prettier",  # code formatter for JS/TS/JSON/YAML/MD
                "python-pip",  # Global pip
                "rsync",  # file synchronization tool
                "shfmt",  # shell script formatter
                "starship",  # cross-shell prompt
                "stylua",  # Lua code formatter
                "tectonic",  # LaTeX engine
                "the_silver_searcher",  # fast text search tool
                "tig",  # text-mode Git interface
                "tealdeer",  # fast tldr client
                "tree-sitter-cli",  # parser generator tool
                "uv",  # fast Python package manager
                "wget",  # web file downloader
                "yarn",  # Node.js package manager
            ],
            aur_packages=[
                "google-java-format",  # Java formatting tool
                "nodejs-markdown-toc",  # TOC Generator in javascript
                "tmux-plugin-manager",  # Tmux Plugin Manager (TPM)
            ],
        )
        return arch_config.merge_with(base)

    def _get_environment_configs(self) -> dict[str, EnvironmentConfig]:
        """Get environment-specific configurations for Arch Linux."""
        base_configs = super()._get_environment_configs()

        # Add Arch-specific environment configurations
        arch_configs = {
            "private": EnvironmentConfig(
                packages=[
                    "bitwarden",  # password manager
                    "firefox",  # web browser
                    "ghostscript",  # PostScript and PDF interpreter
                    "imagemagick",  # image manipulation toolkit
                    "noto-fonts-emoji",  # emoji font collection
                    "otf-font-awesome",  # icon font
                    "python-gobject",  # Python GObject bindings
                    "tailscale",  # mesh VPN service
                ],
                systemd_services=["tailscaled"],
            ),
        }

        # Merge with base configurations
        merged_configs: dict[str, EnvironmentConfig] = {}
        for env_name in set(base_configs.keys()) | set(arch_configs.keys()):
            base_env = base_configs.get(env_name, EnvironmentConfig())
            arch_env = arch_configs.get(env_name, EnvironmentConfig())
            merged_configs[env_name] = arch_env.merge_with(base_env)

        return merged_configs

    def check_packages_installed(
        self, packages: list[str], logger: LoggingHelpers, output: ConsoleOutput
    ) -> tuple[list[str], list[str]]:
        """Check which packages are already installed via pacman"""
        logger = logger.bind(package_count=len(packages), packages=packages)
        logger.log_info("checking_pacman_packages")

        if not packages:
            logger.log_info("no_packages_to_check", logger=logger)
            return [], []

        try:
            result = run_command_with_error_handling(
                ["pacman", "-Q"] + packages, logger, output
            )

            # pacman -Q returns 0 if all packages are installed
            if result.returncode == 0:
                logger.log_info("all_packages_installed", logger=logger)
                return packages, []

            # Some packages are missing, check individually
            logger.log_info("checking_packages_individually", logger=logger)
            installed: list[str] = []
            missing: list[str] = []

            for package in packages:
                check_result = run_command_with_error_handling(
                    ["pacman", "-", package], logger, output
                )
                if check_result.returncode == 0:
                    installed.append(package)
                else:
                    missing.append(package)

            logger = logger.bind(
                installed_count=len(installed),
                missing_count=len(missing),
                installed=installed,
                missing=missing,
            )
            logger.log_info(
                "package_check_completed",
            )
            return installed, missing
        except Exception as e:
            logger.log_exception(e, "pacman_package_check_failed")
            # If pacman check fails, assume all packages need installation
            return [], packages

    def should_update_system(self) -> bool:
        """Check if system update needed (not done in last 24 hours)"""
        marker_file = Path.home() / ".cache" / "dotfiles_last_update"

        if not marker_file.exists():
            return True

        try:
            last_update = datetime.fromisoformat(marker_file.read_text().strip())
            return (datetime.now() - last_update).total_seconds() > 86400  # 24 hours
        except (ValueError, OSError):
            return True

    def mark_system_updated(self, logger: LoggingHelpers) -> None:
        """Mark system as updated with current timestamp"""
        marker_file = Path.home() / ".cache" / "dotfiles_last_update"
        marker_file.parent.mkdir(exist_ok=True)
        timestamp = datetime.now().isoformat()
        marker_file.write_text(timestamp)
        logger.log_info("Updated timestamp set", timestamp=timestamp)

    def update_system(self, logger: LoggingHelpers, output: ConsoleOutput):
        """Perform system update if needed using PacmanManager"""
        if self.no_remote_mode:
            output.info("No-remote mode: Skipping system updates", logger=logger)
            return

        if not self.should_update_system():
            output.success(
                "System updated within last 24 hours, skipping update", logger=logger
            )
            return

        try:
            manager = PacmanManager()
            if manager.is_available(logger=logger, output=output):
                # Check for updates first
                has_updates, count = manager.check_updates(logger=logger, output=output)
                logger = logger.bind(has_updates=has_updates, count=count)
                if has_updates:
                    output.status(
                        f"Found {count} system updates available",
                        emoji="🔄",
                        logger=logger,
                    )
                    # Perform the update
                    result = manager.update(logger=logger, output=output, dry_run=False)

                    if result.status.value == "success":
                        output.success("System update completed successfully")
                        logger.log_progress("system update completed successfully")
                        self.mark_system_updated(logger)
                    else:
                        logger = logger.bind(
                            result_status=result.status.value,
                            result_message=result.message,
                        )
                        output.warning(
                            f"System update completed with status: {result.status.value}",
                            logger=logger,
                        )
                        output.info(f"Message: {result.message}")
                        self.mark_system_updated(logger)
                else:
                    output.success("No system updates available", logger=logger)
                    self.mark_system_updated(logger)
            else:
                output.warning(
                    "Pacman package manager not available, skipping system updates",
                    logger=logger,
                )
        except Exception as e:
            output.error(f"ERROR during system update: {e}")
            output.info(
                "Try: Run 'sudo pacman -Syu' manually to check for issues", emoji="💡"
            )
            logger.log_exception(e, "pacman_system_update_failed")
            raise

    def install_dependencies(self, logger: LoggingHelpers, output: ConsoleOutput):
        """Install packages with retry logic and comprehensive error handling"""

        # Perform system update if needed
        self.update_system(logger, output)

        def pacman(*args: str, **kwargs: Any) -> CompletedProcess[str]:
            """
            Execute pacman commands with real-time output, error handling, and retry logic.

            Key improvements implemented here:
            1. Real-time output streaming (removed capture_output=True)
            2. Reduced timeout for faster failure detection
            3. Comprehensive error handling with retries
            4. Consistent timeout with APT operations (600s)

            Arch Linux advantages:
            - Uses --noconfirm to prevent interactive prompts (no timezone issues)
            - No environment variable complications like APT
            - Generally faster package operations than APT
            """
            max_retries = 3
            for attempt in range(max_retries):
                pacman_logger = logger.bind(attempt=attempt)
                try:
                    # Real-time output streaming configuration
                    #
                    # Previous problem: capture_output=True hid all pacman progress from users.
                    # Users only saw "Installing X packages..." with no visible progress.
                    #
                    # Solution: Remove capture_output=True to show real-time package installation.
                    # Still capture stderr for error handling while stdout flows to terminal.
                    #
                    # Timeout reduced from 1800s (30min) to 600s (10min) for consistency with APT
                    # and faster failure detection in CI environments.
                    result = run_command_with_error_handling(
                        ["sudo", "pacman"] + list(args),
                        pacman_logger,
                        output,
                        timeout=600,
                        **kwargs,
                    )
                    return result
                except TimeoutExpired:
                    output.error(
                        f"Package installation timed out (attempt {attempt + 1}/{max_retries})",
                        logger=pacman_logger,
                    )
                    if attempt == max_retries - 1:
                        output.info(
                            "Try: Check internet connection or use different mirror",
                            emoji="💡",
                            logger=pacman_logger,
                        )
                        raise
                    output.status(
                        "Retrying in 10 seconds...", emoji="🔄", logger=logger
                    )
                    time.sleep(10)
                except CalledProcessError as e:
                    output.error(f"Package installation failed: {e}", logger=logger)
                    output.info(f"Command: sudo pacman {' '.join(args)}", emoji="🔍")
                    if e.stdout:
                        output.info(f"STDOUT:\n{e.stdout}", emoji="📄")
                    if e.stderr:
                        output.info(f"STDERR:\n{e.stderr}", emoji="📄")

                    # Provide specific advice based on error
                    stderr_lower = e.stderr.lower() if e.stderr else ""
                    if "conflict" in stderr_lower:
                        output.info(
                            "Try: Resolve conflicts manually or update system first",
                            emoji="💡",
                        )
                    elif "not found" in stderr_lower:
                        output.info(
                            "Try: Update package databases with 'pacman -Sy'",
                            emoji="💡",
                        )
                    elif (
                        "permission denied" in stderr_lower
                        or "password" in stderr_lower
                    ):
                        output.info(
                            "Try: Configure sudo or run in interactive terminal",
                            emoji="💡",
                        )
                    else:
                        output.info("Try: Check the error details above", emoji="💡")
                    raise
            raise

        try:
            # Check and install base packages
            base_packages = ["git", "base-devel"]
            output.status("Checking base development tools...")
            installed, missing = self.check_packages_installed(
                base_packages, logger, output
            )

            if installed:
                output.success(f"Already installed: {', '.join(installed)}")

            if missing:
                output.status(
                    f"Installing {len(missing)} base development tools: {', '.join(missing)}"
                )
                pacman("-S", "--needed", "--noconfirm", *missing)
                output.success("Base development tools installed", logger=logger)
                self.restart_required = True
            else:
                output.success("All base development tools already installed")

            # Create projects directory safely
            projects_dir = expand("~/projects")
            logger = logger.bind(projects_dir=projects_dir)
            try:
                ensure_path(projects_dir)
            except OSError as e:
                logger.log_exception(e, "projects_directory_creation_failed")
                output.error(f"Cannot create projects directory: {e}")
                output.info("Try: Check home directory permissions", emoji="💡")
                raise

            # Check if yay is already installed system-wide
            yay_installed = False
            try:
                run_command_with_error_handling(["yay", "--version"], logger, output)
                yay_installed = True
                output.success("Yay AUR helper already installed")
            except (CalledProcessError, FileNotFoundError):
                yay_installed = False
            logger = logger.bind(yay_installed=yay_installed)

            # Install yay if not available
            if not yay_installed:
                yay_dir = expand("~/projects/yay-bin")
                logger = logger.bind(yay_dir=yay_dir)
                if not exists(yay_dir):
                    try:
                        output.status("Cloning yay AUR helper...", logger=logger)
                        # Use streaming subprocess for git clone to show progress
                        # Git clone can take time depending on network speed
                        run_command_with_error_handling(
                            [
                                "git",
                                "clone",
                                "https://aur.archlinux.org/yay-bin.git",
                                yay_dir,
                            ],
                            logger,
                            output,
                            timeout=120,
                        )

                        output.status(
                            "Building yay (this will prompt for sudo password)...",
                            logger=logger,
                        )
                        # Use streaming subprocess for makepkg to show build progress
                        # Compilation can take 5-10 minutes and users need to see progress
                        run_command_with_error_handling(
                            ["makepkg", "-si", "--needed", "--noconfirm"],
                            logger,
                            output,
                            cwd=yay_dir,
                        )
                        output.success("Yay AUR helper installed", logger=logger)

                    except Exception as e:
                        logger.log_exception(e, "pacman_package_check_failed")
                        output.info(
                            "Try: Check internet connection and build dependencies",
                            emoji="💡",
                        )
                        raise
                else:
                    output.success("Yay source already cloned")

            # Check and install main packages
            all_packages = self.config.packages
            logger = logger.bind(all_packages=all_packages)
            output.status(
                f"Checking {len(all_packages)} pacman packages...", logger=logger
            )

            installed, missing = self.check_packages_installed(
                all_packages, logger, output
            )

            if installed:
                output.success(
                    f"Already installed: {len(installed)} packages", logger=logger
                )

            if missing:
                output.status(
                    f"Installing {len(missing)} missing pacman packages...",
                    logger=logger,
                )
                try:
                    pacman("-S", "--needed", "--noconfirm", *missing, logger=logger)
                    output.success(
                        "All missing pacman packages installed successfully",
                        logger=logger,
                    )
                    self.restart_required = True
                except CalledProcessError as e:
                    logger.log_exception(e, "pacman_packages_installation_failed")
                    output.error("Some pacman packages failed to install")
                    output.info(
                        "Try: Check package names and update system", emoji="💡"
                    )
                    raise e
            else:
                output.success("All pacman packages already installed", logger=logger)

            # Check and install AUR packages
            aur_packages = self.config.aur_packages
            if aur_packages and yay_installed:
                output.status(
                    f"Checking {len(aur_packages)} AUR packages...", logger=logger
                )
                installed_aur, missing_aur = self.check_packages_installed(
                    aur_packages, logger, output
                )

                if installed_aur:
                    output.success(
                        f"Already installed: {len(installed_aur)} AUR packages",
                        logger=logger,
                    )

                if missing_aur:
                    output.status(
                        f"Installing {len(missing_aur)} missing AUR packages...",
                        logger=logger,
                    )
                    try:
                        run_command_with_error_handling(
                            ["yay", "-S", "--needed", "--noconfirm"] + missing_aur,
                            logger,
                            output,
                            timeout=1800,
                        )
                        output.success(
                            "All missing AUR packages installed successfully",
                            logger=logger,
                        )
                    except TimeoutExpired as e:
                        logger.log_exception(e, "aur_installation_timeout")
                        output.error("AUR package installation timed out")
                        raise
                    except CalledProcessError as e:
                        logger.log_exception(e, "aur_packages_installation_failed")
                        output.error("Some AUR packages failed to install")
                        if e.stderr:
                            output.info(f"Error details: {e.stderr}", emoji="💡")
                        raise
                else:
                    output.success("All AUR packages already installed", logger=logger)
            elif aur_packages and not yay_installed:
                output.warning(
                    "AUR packages requested but yay not available", logger=logger
                )

            # Check and enable systemd services
            services_to_enable = self.config.systemd_services
            logger = logger.bind(services_to_enable=services_to_enable)
            if services_to_enable:
                output.status(
                    f"Checking {len(services_to_enable)} systemd services...",
                    logger=logger,
                )

            for service in services_to_enable:
                try:
                    is_enabled, is_active = self.check_systemd_service_status(
                        service, logger, output
                    )

                    if is_enabled and is_active:
                        output.success(
                            f"Service already enabled and active: {service}",
                            logger=logger,
                        )
                        continue
                    elif is_enabled and not is_active:
                        output.status(
                            f"Starting already enabled service: {service}",
                            emoji="🔄",
                            logger=logger,
                        )
                        run_command_with_error_handling(
                            ["systemctl", "start", service], logger, output
                        )
                        output.success(f"Started service: {service}", logger=logger)
                    else:
                        output.status(
                            f"Enabling and starting service: {service}",
                            emoji="🔄",
                            logger=logger,
                        )
                        run_command_with_error_handling(
                            ["systemctl", "enable", "--now", service], logger, output
                        )
                        output.success(
                            f"Enabled and started service: {service}", logger=logger
                        )

                except CalledProcessError as e:
                    # In containers, systemd services often fail - this is expected
                    if (
                        "chroot" in e.stderr.lower()
                        or "failed to connect to bus" in e.stderr.lower()
                        or "not available" in e.stderr.lower()
                    ):
                        logger.log_exception(e, "service_enable_in_container_failed")
                        output.warning(
                            f"Cannot enable {service} in container environment"
                        )
                    else:
                        logger.log_exception(e, "service_enable_failed")
                        output.error(f"Failed to enable service {service}: {e.stderr}")
                        # Don't raise here - continue with other services

        except KeyboardInterrupt as e:
            logger.log_exception(e, "installation_interrupted_by_user")
            output.error("Installation interrupted by user")
            raise
        except Exception as e:
            logger.log_exception(e, "package_installation_fatal_error")
            output.error(f"FATAL ERROR during package installation: {e}")
            output.info("Try: Check logs above for specific error details", emoji="💡")
            raise

        # Call parent class
        super().install_dependencies(logger, output)


class Debian(Linux):
    def check_packages_installed(
        self, packages: list[str], logger: LoggingHelpers, console: ConsoleOutput
    ) -> tuple[list[str], list[str]]:
        """Check which packages are already installed via apt"""
        if not packages:
            return [], []

        try:
            installed: list[str] = []
            missing: list[str] = []
            logger = logger.bind(installed=installed, missing=missing)

            for package in packages:
                result = run_command_with_error_handling(
                    ["dpkg", "-l", package], logger, console, "dpkg command"
                )
                # dpkg -l returns 0 and shows 'ii' status for installed packages
                if result.returncode == 0 and f"ii  {package}" in result.stdout:
                    installed.append(package)
                else:
                    missing.append(package)

            return installed, missing
        except Exception as e:
            logger.log_exception(e, "dpkg_check_failed", packages=packages)
            # If dpkg check fails, assume all packages need installation
            return [], packages

    def _is_running_in_container(self, logger: LoggingHelpers):
        """
        Detect if we're running inside a container (Docker, Podman, etc.)

        This is used to determine if it's safe to modify system settings like timezone.
        Containers often need timezone pre-configuration to prevent interactive prompts
        during package installation, while real systems should preserve user settings.

        Detection methods:
        1. Container-specific files: /.dockerenv (Docker), /run/.containerenv (Podman)
        2. Process tree analysis: Check /proc/1/cgroup for container runtime signatures
        3. Virtualization indicators: /proc/vz (OpenVZ/Virtuozzo)

        Returns:
            bool: True if running in a container/virtualized environment, False otherwise

        Safety note: Defaults to False if detection fails (safer for real systems)
        """
        try:
            # Check for container-specific files/indicators
            # These files are created by container runtimes and are reliable indicators
            container_indicators = [
                "/.dockerenv",  # Docker creates this file in all containers
                "/run/.containerenv",  # Podman creates this file in all containers
            ]

            for indicator in container_indicators:
                if exists(indicator):
                    return True

            # Check /proc/1/cgroup for container runtime signatures
            # Container runtimes modify the cgroup hierarchy for process 1 (init)
            if exists("/proc/1/cgroup"):
                with open("/proc/1/cgroup", "r") as f:
                    content = f.read()
                    # Look for container runtime signatures in the cgroup path
                    if (
                        "docker" in content
                        or "containerd" in content
                        or "podman" in content
                    ):
                        return True

            # Check if running in virtualized environment that might need timezone setup
            # Some virtualization systems also benefit from timezone pre-configuration
            if exists("/proc/vz"):  # OpenVZ/Virtuozzo container system
                return True

            return False
        except Exception as e:
            logger.log_exception(e, "container_detection_failed")
            # If we can't determine container status (permissions, missing files, etc.),
            # assume we're NOT in a container. This is safer for real user systems
            # where we don't want to accidentally modify timezone settings.
            return False

    apt_packages = [
        "ack",  # text search tool
        "apt-file",  # search files in packages
        "build-essential",  # compilation tools and libraries
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

    def install_dependencies(self, logger: LoggingHelpers, output: ConsoleOutput):
        """Install packages with retry logic and comprehensive error handling"""

        if self.no_remote_mode:
            output.info(
                "No-remote mode: Skipping package installation and system updates"
            )
            return

        # Pre-configure timezone to prevent tzdata interactive prompts
        #
        # Problem: The tzdata package (timezone data) can prompt users to select their
        # geographic region and timezone during installation, even with --assume-yes.
        # This happens because tzdata uses debconf for configuration, which bypasses
        # the APT --assume-yes flag.
        #
        # Solution: Pre-configure the timezone before package installation so tzdata
        # finds the timezone already set and skips the interactive configuration.
        #
        # Why UTC: It's the safest default for containers and automated environments.
        # Real systems preserve their existing timezone settings.
        #
        # Safety: Only runs in no-remote mode (--no-remote flag) or detected containers,
        # never on real user systems where timezone might be intentionally set.
        if self.no_remote_mode or self._is_running_in_container(logger):
            try:
                output.status(
                    "Pre-configuring timezone to UTC to prevent interactive prompts...",
                    logger=logger,
                )

                # Step 1: Create symlink from /etc/localtime to UTC timezone data
                # This is the primary way Linux systems determine the current timezone
                run_command_with_error_handling(
                    ["sudo", "ln", "-fs", "/usr/share/zoneinfo/UTC", "/etc/localtime"],
                    logger,
                    output,
                    "Set timezone symlink to UTC",
                    timeout=30,
                )

                # Step 2: Set the timezone name in /etc/timezone for consistency
                # Some tools and packages read this file to determine the timezone name
                run_command_with_error_handling(
                    ["sudo", "sh", "-c", "echo 'UTC' > /etc/timezone"],
                    logger,
                    output,
                    "Set timezone name to UTC",
                    timeout=30,
                )

                output.success("Timezone pre-configured to UTC", logger=logger)
            except Exception as e:
                logger.log_exception(e, "timezone_preconfiguration_failed")
                output.warning(f"Could not pre-configure timezone: {e}")
                output.info(
                    "This may cause interactive prompts during package installation",
                    emoji="💡",
                )
        else:
            output.success(
                "Skipping timezone pre-configuration (running on real system)",
                logger=logger,
            )

        def apt_get(
            *args: str, logger: LoggingHelpers, output: ConsoleOutput, **kwargs: Any
        ):
            """
            Execute APT commands with real-time output, error handling, and retry logic.

            Key improvements implemented here:
            1. Real-time output streaming (removed capture_output=True)
            2. Non-interactive environment setup (DEBIAN_FRONTEND=noninteractive)
            3. Reduced timeout for faster failure detection
            4. Comprehensive error handling with retries

            Note: DEBIAN_FRONTEND=noninteractive may not work with sudo due to
            environment variable filtering, but we set it anyway as a fallback.
            The primary solution is timezone pre-configuration above.
            """
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger = logger.bind(retry_attempt=attempt)
                    # Set up non-interactive environment to prevent prompts
                    #
                    # Problem: sudo often drops environment variables for security.
                    # Even with env parameter, DEBIAN_FRONTEND may not reach apt-get.
                    # This is why we pre-configure timezone as the primary solution.
                    env = os.environ.copy()
                    env["DEBIAN_FRONTEND"] = "noninteractive"

                    # Real-time output streaming configuration
                    #
                    # Previous problem: capture_output=True hid all APT progress from users.
                    # Users only saw "Installing X packages..." with no visible progress.
                    #
                    # Solution: Remove capture_output=True to show real-time package installation.
                    # Still capture stderr for error handling while stdout flows to terminal.
                    #
                    # Timeout reduced from 1800s (30min) to 600s (10min) for faster failure detection
                    # while still allowing time for large package downloads.
                    result = run_command_with_error_handling(
                        ["sudo", "apt-get"] + list(args),
                        logger,
                        output,
                        env=env,
                        timeout=600,
                        **kwargs,
                    )
                    return result
                except TimeoutExpired as e:
                    logger.log_exception(e, "apt_get_timeout")
                    output.error(
                        f"APT operation timed out (attempt {attempt + 1}/{max_retries})"
                    )
                    if attempt == max_retries - 1:
                        output.info(
                            "Try: Check internet connection or use different mirror",
                            emoji="💡",
                        )
                        raise
                    output.status("Retrying in 10 seconds...", emoji="🔄")
                    time.sleep(10)
                except CalledProcessError as e:
                    logger.log_exception(e, "apt_update_failed")
                    if "unable to lock" in e.stderr.lower():
                        output.error("APT database is locked")
                        output.info(
                            "Try: Wait for other package operations to complete",
                            emoji="💡",
                        )
                    elif "no space left" in e.stderr.lower():
                        output.error("No space left on device")
                        output.info("Try: Free up disk space and try again", emoji="💡")
                    elif "permission denied" in e.stderr.lower():
                        output.error("Permission denied - sudo may not be configured")
                        output.info(
                            "Try: Configure sudo or run as appropriate user", emoji="💡"
                        )
                    elif "failed to fetch" in e.stderr.lower():
                        output.error("Failed to fetch packages")
                        output.info(
                            "Try: Check internet connection and repository availability",
                            emoji="💡",
                        )
                    else:
                        output.error(f"APT operation failed: {e.stderr}")
                    raise

        try:
            # Update package databases
            output.status("Updating package databases...", logger=logger)
            apt_get("update", output=output, logger=logger)
            output.success("Package databases updated", logger=logger)

            # Upgrade existing packages
            output.status("Upgrading existing packages...")
            try:
                apt_get("upgrade", "--assume-yes", output=output, logger=logger)
                output.success("System packages upgraded", logger=logger)
            except CalledProcessError as _:
                output.warning("Some packages failed to upgrade", logger=logger)
                output.info(
                    "This is often non-critical, continuing with installation...",
                    emoji="💡",
                )

            # Check and install main packages
            output.status(
                f"Checking {len(self.apt_packages)} APT packages...", logger=logger
            )
            (installed, missing) = self.check_packages_installed(
                self.apt_packages, logger, output
            )

            if installed:
                output.success(
                    f"Already installed: {len(installed)} packages", logger=logger
                )

            if missing:
                output.status(
                    f"Installing {len(missing)} missing APT packages...", logger=logger
                )
                try:
                    apt_get(
                        "install",
                        "--assume-yes",
                        *missing,
                        logger=logger,
                        output=output,
                    )
                    output.success(
                        "All missing APT packages installed successfully", logger=logger
                    )
                except CalledProcessError as e:
                    logger.log_exception(e, "apt_packages_installation_failed")
                    output.error("Some APT packages failed to install")
                    output.info(
                        "Try: Check package names and fix any dependency conflicts",
                        emoji="💡",
                    )
                    raise
            else:
                output.success("All APT packages already installed", logger=logger)

            # Update apt-file database
            output.status("Updating apt-file database...", logger=logger)
            try:
                run_command_with_error_handling(
                    ["sudo", "apt-file", "update"], logger, output, timeout=600
                )
                output.success("Apt-file database updated", logger=logger)
            except CalledProcessError as e:
                logger.log_exception(e, "apt_file_update_failed")
                output.warning("apt-file update failed")
                output.info("This is non-critical, continuing...", emoji="💡")
            except TimeoutExpired as e:
                logger.log_exception(e, "apt_file_timeout")
                output.warning("apt-file update timed out")
                output.info("This is non-critical, continuing...", emoji="💡")

            # Download and install latest Neovim AppImage
            nvim_appimage = expand("./nvim.appimage")
            logger = logger.bind(nvim_appimage=nvim_appimage)
            if not exists(nvim_appimage):
                output.status("Downloading latest Neovim AppImage...", logger=logger)
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        logger = logger.bind(retry_attempt=attempt)
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

                        output.success(
                            "Neovim AppImage downloaded successfully", logger=logger
                        )
                        break

                    except urllib.error.URLError as e:
                        logger.log_exception(e, "neovim_download_network_error")
                        output.error(
                            f"Failed to download Neovim (attempt {attempt + 1}/{max_retries}): {e}"
                        )
                        if attempt == max_retries - 1:
                            output.info(
                                "Try: Check internet connection or download manually",
                                emoji="💡",
                            )
                            raise
                        output.status("Retrying in 5 seconds...", emoji="🔄")
                        time.sleep(5)
                    except Exception as e:
                        logger.log_exception(e, "neovim_download_unexpected_error")
                        output.error(f"Unexpected error downloading Neovim: {e}")
                        raise

                # Make AppImage executable
                try:
                    os.chmod(nvim_appimage, 0o755)
                    output.success("Neovim AppImage made executable", logger=logger)
                except OSError as e:
                    output.error(
                        f"Failed to make Neovim executable: {e}", logger=logger
                    )
                    raise

                # Create ~/bin directory
                bin_dir = expand("~/bin")
                logger = logger.bind()
                try:
                    ensure_path(bin_dir)
                    output.success("~/bin directory created", logger=logger)
                except OSError as e:
                    logger.log_exception(e, "neovim_appimage_permissions_failed")
                    output.error(f"Cannot create ~/bin directory: {e}")
                    output.info("Try: Check home directory permissions", emoji="💡")
                    raise

                # Create symlink to nvim
                nvim_symlink = expand("~/bin/nvim")
                logger = logger.bind(nvim_symlink=nvim_symlink)
                if not exists(nvim_symlink):
                    try:
                        os.symlink(nvim_appimage, nvim_symlink)
                        output.success(
                            "Neovim symlink created in ~/bin/nvim", logger=logger
                        )
                    except OSError as e:
                        logger.log_exception(e, "neovim_appimage_permissions_failed")
                        output.error(f"Failed to create Neovim symlink: {e}")
                        output.info(
                            "Try: Check ~/bin directory permissions", emoji="💡"
                        )
                        raise
                else:
                    output.success("Neovim symlink already exists", logger=logger)
            else:
                output.success("Neovim AppImage already exists", logger=logger)

        except KeyboardInterrupt as e:
            logger.log_exception(e, "installation_interrupted_by_user")
            output.error("Installation interrupted by user")
            raise
        except Exception as e:
            logger.log_exception(e, "package_installation_fatal_error")
            output.error(f"FATAL ERROR during package installation: {e}")
            output.info("Try: Check logs above for specific error details", emoji="💡")
            raise

        # Call parent class
        super().install_dependencies(logger, output)

    def update_system(self, logger: LoggingHelpers, output: ConsoleOutput):
        """Update system packages using DebianSystemManager"""
        if self.no_remote_mode:
            output.info("No-remote mode: Skipping system updates")
            return

        try:
            manager = DebianSystemManager()
            if manager.is_available(logger=logger, output=output):
                output.status("Updating system packages...", logger=logger)
                result = manager.update(logger=logger, output=output, dry_run=False)
                logger = logger.bind(
                    result_status=result.status.value, result_message=result.message
                )

                if result.status.value == "success":
                    output.success(
                        "System packages updated successfully", logger=logger
                    )
                    logger.log_progress("system update completed successfully")
                else:
                    output.warning(
                        f"System update completed with status: {result.status.value}",
                        logger=logger,
                    )
                    output.info(f"Message: {result.message}")
            else:
                output.warning(
                    "APT package manager not available, skipping system updates",
                    logger=logger,
                )
                logger.log_warning("apt not available for system updates")
        except Exception as e:
            logger.log_exception(e, "system_update_failed")
            output.error(f"ERROR during system update: {e}")
            raise


def detect_operating_system(
    logger: LoggingHelpers, environment: str = "minimal", no_remote_mode: bool = False
):
    """Detect and return the appropriate operating system class"""
    with open("/etc/os-release") as release_file:
        content = release_file.read()
        logger = logger.bind(release_data=content)
        if 'NAME="Arch Linux"' in content:
            return Arch(environment=environment, no_remote_mode=no_remote_mode)
        elif 'NAME="CachyOS Linux"' in content:
            return Arch(environment=environment, no_remote_mode=no_remote_mode)
        elif 'NAME="Garuda Linux"' in content:
            return Arch(environment=environment, no_remote_mode=no_remote_mode)
        elif "ID=debian" in content or "ID_LIKE=debian" in content:
            return Debian(environment=environment, no_remote_mode=no_remote_mode)
        else:
            logger.log_error("Unknown OS")
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
    --no-remote        Skip remote activities (GitHub, SSH keys, Tailscale)
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
    DOTFILES_ENVIRONMENT=minimal uv run init.py --no-remote # Install without remote activities

ENVIRONMENT VARIABLE:
    DOTFILES_ENVIRONMENT    Required. Must be set to: minimal, work, or private
                           This prevents accidentally running the wrong environment configuration

For more information, see the README or CLAUDE.md files.
"""
    # This function is for displaying help text, so print is appropriate here
    print(help_text)


@click.command()
@click.option(
    "--no-remote",
    is_flag=True,
    help="Skip remote activities (GitHub, SSH keys, Tailscale)",
)
@click.option("--quiet", is_flag=True, help="Suppress non-essential output")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def main(no_remote: bool, quiet: bool, verbose: bool):
    """Install and configure dotfiles for Linux systems

    \\b
    Environment must be set via DOTFILES_ENVIRONMENT environment variable.

    \\b
    Examples:
      export DOTFILES_ENVIRONMENT=minimal && dotfiles-init
      export DOTFILES_ENVIRONMENT=work && dotfiles-init --no-remote
      export DOTFILES_ENVIRONMENT=private && dotfiles-init --verbose

    \\b
    Valid environments: minimal, work, private
    """
    # Initialize logging and console output
    logger = setup_logging("init").bind(
        verbose=verbose, quiet=quiet, no_remote_mode=no_remote
    )
    output = ConsoleOutput(verbose=verbose, quiet=quiet)

    logger.log_info("init_script_started")

    try:
        # Get environment from environment variable
        environment = os.environ.get("DOTFILES_ENVIRONMENT")
        logger = logger.bind(environment=environment)
        if not environment:
            output.error(
                "DOTFILES_ENVIRONMENT environment variable is not set", logger=logger
            )
            output.info(
                "You must set the environment variable to one of: minimal, work, private"
            )
            output.info("Examples:")
            output.info("   export DOTFILES_ENVIRONMENT=minimal && dotfiles-init")
            output.info("   export DOTFILES_ENVIRONMENT=work && dotfiles-init")
            output.info("   export DOTFILES_ENVIRONMENT=private && dotfiles-init")
            output.info(
                "This prevents accidentally running the wrong environment configuration"
            )
            return 1

        # Validate environment value
        valid_environments = ["minimal", "work", "private"]
        if environment not in valid_environments:
            output.error(f"Invalid DOTFILES_ENVIRONMENT '{environment}'", logger=logger)
            output.info(f"Must be one of: {', '.join(valid_environments)}")
            return 1

        logger.log_info(
            "environment_validated", environment=environment, no_remote_mode=no_remote
        )

        output.status(
            f"Installing dotfiles for {environment} environment{' (no-remote mode)' if no_remote else ''}",
            "🚀",
        )

        try:
            operating_system = detect_operating_system(
                logger, environment=environment, no_remote_mode=no_remote
            )
        except FileNotFoundError as e:
            logger.log_exception(e, "os_detection_file_missing")
            output.error(
                "Cannot detect operating system (/etc/os-release not found)",
                logger=logger,
            )
            output.info("This script only supports Linux distributions")
            return 1
        except NotImplementedError as e:
            logger.log_exception(e, "os_not_supported")
            output.error(str(e))
            output.info(
                "This script currently supports Arch Linux, Garuda Linux, and Debian-based systems"
            )
            return 1

        # Execute installation steps with individual error handling
        # Track if changes require terminal restart
        operating_system.restart_required = False

        steps: list[tuple[str, Callable[[LoggingHelpers], None | bool]]] = [
            # steps = [
            (
                "Installing dependencies",
                lambda logger: operating_system.install_dependencies(logger, output),
            ),
            (
                "Linking configurations",
                lambda logger: operating_system.link_configs(logger, output),
            ),
            (
                "Validating git credential helper",
                lambda logger: operating_system.validate_git_credential_helper(
                    logger, output
                ),
            ),
            (
                "Setting up shell",
                lambda logger: operating_system.setup_shell(logger, output),
            ),
            (
                "Setting up accounts",
                lambda logger: operating_system.link_accounts(logger, output),
            ),
        ]

        # Use Rich progress bar for the installation steps
        with output.progress_context() as progress:
            task = progress.add_task("Installing dotfiles...", total=len(steps))

            for i, (step_name, step_func) in enumerate(steps):
                step_log = logger.bind(step_num=i, step_name=step_name)
                try:
                    step_log.log_info("step_started")
                    progress.update(task, description=f"🔄 {step_name}...")
                    step_func(step_log)
                    output.success(
                        f"{step_name} completed successfully", logger=step_log
                    )
                    progress.advance(task)
                except KeyboardInterrupt:
                    output.error(f"{step_name} interrupted by user", logger=step_log)
                    return 130  # Standard exit code for SIGINT
                except Exception as e:
                    step_log.log_exception(
                        e,
                        "step_failed",
                    )
                    output.error(f"ERROR in {step_name}: {e}")
                    if verbose:
                        output.info("DETAILED ERROR INFORMATION:")
                        traceback.print_exc()
                        output.info("Check the error details above and retry")
                    return 1

        logger = logger.bind(restart_required=operating_system.restart_required)
        output.success(
            "Dotfiles installation completed successfully!", "🎉", logger=logger
        )

        # Only show restart warning if changes were made
        if operating_system.restart_required:
            output.info(
                "You may need to restart your terminal or run 'source ~/.config/fish/config.fish' for changes to take effect"
            )
        return 0

    except Exception as e:
        logger.log_exception(e, "init_script_unexpected_error")
        output.error(f"UNEXPECTED ERROR: {e}")
        if verbose:
            output.info("DETAILED ERROR INFORMATION:")
            traceback.print_exc()
        output.info("Please report this issue with the full error message")
        return 1


if __name__ == "__main__":
    sys.exit(main())
# Trigger PR update
