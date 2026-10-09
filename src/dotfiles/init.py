# pyright: strict
import os
import socket
import sys
import time
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess, TimeoutExpired
from typing import TYPE_CHECKING, Any, cast

import click
import yaml

from .logging_config import (
    LoggingHelpers,
    setup_logging,
)
from .output_formatting import ConsoleOutput
from .process_helper import run_command_with_error_handling, run_interactive_command
from .swman import DebianSystemManager, PacmanManager

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class EnvironmentConfig:
    """Type-safe installation configuration."""

    # Package management
    packages: list[str] = field(default_factory=list[str])
    aur_packages: list[str] = field(default_factory=list[str])

    # Configuration directories: (source_dir, target_dir)
    config_dirs: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])

    # Local bin files to link
    local_bin_files: list[str] = field(default_factory=list[str])

    # System services to enable (uses sudo systemctl)
    systemd_services: list[str] = field(default_factory=list[str])

    # User services to enable (uses systemctl --user)
    systemd_user_services: list[str] = field(default_factory=list[str])

    # Email used in the SSH key comment
    ssh_key_email: str | None = None

    def merge_with(self, base_config: "EnvironmentConfig") -> "EnvironmentConfig":
        """Merge this config with a base, with this taking priority."""
        return EnvironmentConfig(
            packages=list(set(base_config.packages).union(set(self.packages))),
            aur_packages=list(
                set(base_config.aur_packages).union(set(self.aur_packages))
            ),
            config_dirs=list(set(base_config.config_dirs).union(set(self.config_dirs))),
            local_bin_files=list(
                set(base_config.local_bin_files).union(set(self.local_bin_files))
            ),
            systemd_services=list(
                set(base_config.systemd_services).union(set(self.systemd_services))
            ),
            systemd_user_services=list(
                set(base_config.systemd_user_services).union(
                    set(self.systemd_user_services)
                )
            ),
            ssh_key_email=self.ssh_key_email or base_config.ssh_key_email,
        )


class Linux:
    # Where git's libsecret credential helper lives (Arch ships it with git)
    LIBSECRET_HELPER = Path("/usr/lib/git-core/git-credential-libsecret")

    def __init__(
        self,
        no_remote_mode: bool = False,
        homedir: Path | None = None,
    ):
        self.no_remote_mode = no_remote_mode
        # Load package manifest BEFORE building config
        self.package_manifest = self._load_package_manifest()
        # Single source of truth for the configuration
        self.config = self._get_base_config()
        self.homedir = homedir if homedir is not None else Path("~").expanduser()

    def _load_package_manifest(self) -> dict[str, Any]:
        """Load package manifest from packages.yaml

        Returns:
            dict: Package manifest with 'base' and 'aur' keys

        Raises:
            FileNotFoundError: If packages.yaml doesn't exist
            yaml.YAMLError: If packages.yaml is invalid
        """
        manifest_path = Path(__file__).parent.parent.parent / "packages.yaml"

        if not manifest_path.exists():
            raise FileNotFoundError(
                f"Package manifest not found at {manifest_path}. "
                "Please ensure packages.yaml exists in repository root."
            )

        with open(manifest_path) as f:
            return yaml.safe_load(f) or {}

    def _get_base_config(self) -> EnvironmentConfig:
        """Get base configuration for Linux systems."""
        return EnvironmentConfig(
            config_dirs=[
                ("direnv", "direnv"),
                ("fish", "fish"),
                ("lazy_nvim", "nvim"),
                ("git", "git"),
                ("irssi", "irssi"),
                ("ghostty", "ghostty"),
            ],
            local_bin_files=["*"],
            systemd_user_services=["pkgstatus-update.timer", "syncthing.service"],
            ssh_key_email="sshkeys@patrick-gerken.de",
        )

    def _reload_systemd_user_daemon(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> None:
        """Run `systemctl --user daemon-reload`.

        Containers have no systemd user session, so a failure there is a known
        limitation and only warns. On a real system it still raises.
        """
        try:
            run_command_with_error_handling(
                ["systemctl", "--user", "daemon-reload"],
                logger,
                output,
                "systemctl --user daemon-reload",
            )
        except CalledProcessError as e:
            if not self._is_running_in_container(logger):
                raise
            logger.log_exception(e, "systemd_user_daemon_reload_in_container_failed")
            output.warning(
                "Cannot reload the systemd user daemon in a container environment"
            )

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
                Path("/.dockerenv"),  # Docker creates this file in all containers
                Path(
                    "/run/.containerenv"
                ),  # Podman creates this file in all containers
            ]

            for indicator in container_indicators:
                if indicator.exists():
                    return True

            # Check /proc/1/cgroup for container runtime signatures
            # Container runtimes modify the cgroup hierarchy for process 1 (init)
            if Path("/proc/1/cgroup").exists():
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
            return Path("/proc/vz").exists()  # OpenVZ/Virtuozzo container system
        except Exception as e:  # noqa: BLE001
            logger.log_exception(e, "container_detection_failed")
            # If we can't determine container status (permissions, missing files, etc.),
            # assume we're NOT in a container. This is safer for real user systems
            # where we don't want to accidentally modify timezone settings.
            return False

    def check_systemd_service_status(
        self,
        service: str,
        logger: LoggingHelpers,
        output: ConsoleOutput,
        user: bool = False,
    ) -> tuple[bool, bool]:
        """Check if a systemd service is enabled and active

        Args:
            service: Service name to check
            logger: Logger instance
            output: Console output instance
            user: If True, use systemctl --user (no sudo)

        Note: run_command_with_error_handling uses check=True, so if returncode != 0,
        it raises CalledProcessError. Therefore, if we reach the result, returncode is always 0.
        We only need to check the stdout content.
        """
        systemctl = ["systemctl", "--user"] if user else ["systemctl"]
        try:
            # Check if service is enabled
            enabled_result = run_command_with_error_handling(
                [*systemctl, "is-enabled", service],
                logger,
                output,
                "systemctl is-enabled",
            )
            is_enabled = "enabled" in enabled_result.stdout

            # Check if service is active
            active_result = run_command_with_error_handling(
                [*systemctl, "is-active", service],
                logger,
                output,
                "systemctl is-active",
            )
            is_active = active_result.stdout.startswith("active")

            return is_enabled, is_active
        except CalledProcessError as e:
            # systemctl returns non-zero for disabled/inactive services
            logger.log_exception(e, "systemd_service_check_failed", service=service)
            # If systemctl check fails, assume service needs setup
            return False, False

    def install_dependencies(self, logger: LoggingHelpers, output: ConsoleOutput):
        """Install NVM and Pyenv with proper error handling"""
        logger.log_progress("starting_dependency_installation")

        # Get dotfiles repo root directory
        dotfiles_dir = Path(__file__).parent.parent.parent  # Go up from src/dotfiles/
        install_scripts_dir = dotfiles_dir / "install_scripts"

        # Install NVM
        nvm_path = self.homedir / ".local/share/nvm"
        logger = logger.bind(nvm_path=nvm_path)
        logger.log_info("checking_nvm_installation")

        if not nvm_path.exists():
            nvm_script = "doesnotexist"
            try:
                output.status("Installing NVM...", logger=logger)
                nvm_script = install_scripts_dir / "install_nvm.sh"
                logger = logger.bind(nvm_script_path=nvm_script)

                if not nvm_script.exists():
                    output.error("NVM installation script not found", logger=logger)
                    output.info(f"Expected: {nvm_script}")
                    raise FileNotFoundError(f"NVM script not found: {nvm_script}")

                run_command_with_error_handling(
                    ["/usr/bin/bash", str(nvm_script)], logger, output
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
        pyenv_path = self.homedir / ".config/pyenv"
        if not pyenv_path.exists():
            try:
                output.status("Installing Pyenv...")
                pyenv_script = install_scripts_dir / "install_pyenv.sh"
                logger = logger.bind(pyenv_script=pyenv_script)
                if not pyenv_script.exists():
                    output.error(
                        "ERROR: Pyenv installation script not found", logger=logger
                    )
                    output.info(f"Expected: {pyenv_script}")
                    raise FileNotFoundError(f"Pyenv script not found: {pyenv_script}")

                run_command_with_error_handling(
                    ["/usr/bin/bash", str(pyenv_script)], logger, output
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
                ["uv", "tool", "install", "--editable", str(dotfiles_dir)],
                logger,
                output,
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

        self.install_git_hooks(dotfiles_dir, logger, output)
        if "syncthing.service" in self.config.systemd_user_services:
            self.setup_syncthing_ignore(dotfiles_dir, logger, output)

    def setup_syncthing_ignore(
        self, dotfiles_dir: Path, logger: LoggingHelpers, output: ConsoleOutput
    ):
        """Make ~/projects/.stignore include the shared patterns from the repo.

        .stignore is per device and not synced by Syncthing, so the shared
        rules live in syncthing/stignore and are pulled in via #include.
        Existing machine-specific lines are kept.
        """
        logger = logger.bind(operation="setup_syncthing_ignore")
        projects_dir = self.homedir / "projects"
        shared = dotfiles_dir / "syncthing" / "stignore"
        if not projects_dir.is_dir() or not shared.is_file():
            logger.log_info("syncthing_ignore_skipped")
            return
        try:
            relative = shared.relative_to(projects_dir)
        except ValueError:
            output.warning(
                f"{shared} is not inside {projects_dir}; skipping Syncthing ignore setup",
                logger=logger,
            )
            return

        include = f"#include {relative}"
        stignore = projects_dir / ".stignore"
        existing = stignore.read_text() if stignore.exists() else ""
        if include in existing.splitlines():
            output.success("Syncthing ignore patterns already included", logger=logger)
            return
        stignore.write_text(f"{include}\n{existing}")
        output.success(f"Added '{include}' to {stignore}", logger=logger)
        logger.log_info("syncthing_ignore_included", include=include)

    def install_git_hooks(
        self, dotfiles_dir: Path, logger: LoggingHelpers, output: ConsoleOutput
    ):
        """Install prek and ruff as uv tools and activate the repo's git hooks.

        Failures are reported but not fatal: hooks are a development convenience.
        """
        logger = logger.bind(operation="install_git_hooks")
        try:
            output.status("Installing prek and git hooks...", logger=logger)
            # ruff is required on PATH by the language: system hooks
            for tool in ("prek", "ruff"):
                run_command_with_error_handling(
                    ["uv", "tool", "install", tool], logger, output
                )
            run_command_with_error_handling(
                ["prek", "install"], logger, output, cwd=str(dotfiles_dir)
            )
            output.success("prek installed and git hooks activated", logger=logger)
            logger.log_info("git_hooks_installed")
        except (CalledProcessError, TimeoutExpired, FileNotFoundError) as e:
            logger.log_exception(e, "git_hooks_installation_failed")
            output.warning(f"Could not set up git hooks: {e}", logger=logger)
            output.info(
                "Try: uv tool install prek && uv tool install ruff && prek install",
                emoji="💡",
            )

    def link_configs(self, logger: LoggingHelpers, output: ConsoleOutput):
        """Create symlinks with comprehensive error handling"""
        # Get dotfiles repo root directory
        dotfiles_dir = Path(__file__).parent.parent.parent  # Go up from src/dotfiles/

        # Ensure ~/.config exists
        config_base_dir = self.homedir / ".config"
        try:
            config_base_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            output.error(
                f"ERROR: Cannot create {config_base_dir} directory: {e}", logger=logger
            )
            output.info("Try: Check home directory permissions", emoji="💡")
            raise

        for config_dir_src, config_dir_target in self.config.config_dirs:
            target_path = self.homedir / f".config/{config_dir_target}"
            source_path = dotfiles_dir / config_dir_src
            logger = logger.bind(target_path=target_path, source_path=source_path)

            try:
                # Verify source exists
                if not source_path.exists():
                    output.error(
                        f"Source directory {source_path} does not exist", logger=logger
                    )
                    output.info(
                        f"Expected config directory: {config_dir_src}", emoji="💡"
                    )
                    continue

                if not target_path.exists():
                    try:
                        os.symlink(source_path, target_path)
                        output.success(f"{target_path} → {source_path}", logger=logger)
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
                                current_target = Path(os.readlink(target_path))
                                expected_target = source_path
                                # Resolve both paths to absolute for comparison
                                current_resolved = current_target.resolve()
                                expected_resolved = expected_target.resolve()

                                if current_resolved != expected_resolved:
                                    output.warning(
                                        f"{target_path} → {current_target}, but should link to {expected_target}",
                                        logger=logger,
                                    )
                                else:
                                    output.success(
                                        f"{target_path} → {source_path}",
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
            except Exception as e:  # noqa: BLE001
                logger.log_exception(e, "config_linking_unexpected_error")
                output.error(f"Unexpected error processing {config_dir_target}: {e}")
                continue

    def link_local_bin(self, logger: LoggingHelpers, output: ConsoleOutput):
        """Create symlinks for local_bin files with comprehensive error handling"""

        # Ensure ~/.local/bin exists
        local_bin_dir = self.homedir / ".local/bin"
        logger = logger.bind(local_bin_dir=str(local_bin_dir))
        try:
            local_bin_dir.mkdir(parents=True, exist_ok=True)
            logger.log_info("local_bin_directory_created")
        except OSError as e:
            logger.log_exception(e, "local_bin_directory_creation_failed")
            output.error(f"Cannot create {local_bin_dir} directory: {e}", logger=logger)
            output.info("Try: Check home directory permissions", emoji="💡")
            raise

        # Determine source directory
        # Assuming we're in the dotfiles directory or can find it via path resolution
        # Get the project root by finding where local_bin/ directory exists
        dotfiles_dir = Path(__file__).parent.parent.parent  # Go up from src/dotfiles/
        source_dir = dotfiles_dir / "local_bin"
        logger = logger.bind(source_dir=str(source_dir), dotfiles_dir=str(dotfiles_dir))

        # Handle "*" pattern (all files) or specific file list
        if "*" in self.config.local_bin_files:
            # Link all files in local_bin/
            if not source_dir.exists():
                logger.log_warning("local_bin_source_not_found")
                output.warning(
                    f"local_bin directory not found: {source_dir}", logger=logger
                )
                return

            try:
                files_to_link = [f.name for f in source_dir.iterdir() if f.is_file()]
                logger = logger.bind(
                    files_count=len(files_to_link), files=files_to_link
                )
                logger.log_info("local_bin_files_discovered")
            except OSError as e:
                logger.log_exception(e, "local_bin_directory_read_failed")
                output.error(f"Cannot read local_bin directory: {e}", logger=logger)
                return
        else:
            # Link only specified files
            files_to_link = self.config.local_bin_files
            logger = logger.bind(files_count=len(files_to_link), files=files_to_link)
            logger.log_info("local_bin_files_from_config")

        if not files_to_link:
            output.success("No files to link in local_bin/", logger=logger)
            return

        # Link each file
        for filename in files_to_link:
            source_path = source_dir / filename
            target_path = local_bin_dir / filename
            logger_bound = logger.bind(
                filename=filename,
                source_path=str(source_path),
                target_path=str(target_path),
            )

            # Check if source exists
            if not source_path.exists():
                logger_bound.log_warning("local_bin_source_file_not_found")
                output.warning(
                    f"Source file not found: {source_path}", logger=logger_bound
                )
                continue

            # Check if target already exists
            if target_path.exists():
                if target_path.is_symlink():
                    # Check if it points to the right place
                    try:
                        current_target = os.readlink(target_path)
                        if Path(current_target) == source_path:
                            logger_bound.log_info("local_bin_link_already_correct")
                            output.success(
                                f"{filename} already correctly linked",
                                logger=logger_bound,
                            )
                        else:
                            logger_bound = logger_bound.bind(
                                current_target=current_target
                            )
                            logger_bound.log_warning("local_bin_link_incorrect_target")
                            output.warning(
                                f"{filename} is linked to {current_target}, but should link to {source_path}",
                                logger=logger_bound,
                            )
                    except OSError as e:
                        logger_bound.log_exception(e, "local_bin_readlink_failed")
                        output.warning(
                            f"Cannot read symlink for {filename}: {e}",
                            logger=logger_bound,
                        )
                else:
                    # It's a regular file - conflict!
                    logger_bound.log_warning("local_bin_file_conflict")
                    output.warning(
                        f"{filename} exists as a regular file in ~/.local/bin, skipping symlink",
                        logger=logger_bound,
                    )
            else:
                # Create the symlink
                try:
                    os.symlink(source_path, target_path)
                    logger_bound.log_info("local_bin_link_created")
                    output.success(f"Linked {filename}", logger=logger_bound)
                    self.restart_required = True
                except OSError as e:
                    logger_bound.log_exception(e, "local_bin_symlink_creation_failed")
                    output.error(f"Failed to link {filename}: {e}", logger=logger_bound)
                    output.info("Try: Check permissions on ~/.local/bin", emoji="💡")
                    continue

    def validate_git_credential_helper(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> bool:
        """Validate that git credential helper is properly configured"""
        try:
            # Check if libsecret binary exists
            libsecret_path = self.LIBSECRET_HELPER
            logger = logger.bind(libsecret_path=libsecret_path)
            if not libsecret_path.exists():
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

            # Test if credential helper responds to 'get' command
            # According to git credential protocol, helpers must receive a command
            # (get, store, or erase) and input via stdin in key=value format
            #
            # The libsecret helper requires at minimum:
            # - protocol field
            # - host OR path field
            # Without these, it exits with status 1
            try:
                # Test with 'get' command and minimal valid protocol input
                # This is a dummy query that won't match any stored credentials
                test_input = "protocol=https\nhost=example.com\n\n"
                result = run_command_with_error_handling(
                    [str(libsecret_path), "get"],
                    logger,
                    output,
                    timeout=5,
                    input=test_input,
                )
                # Helper should exit with code 0 (success) even if no credentials found
                # An empty output is expected for this test query
                # This confirms the helper can be invoked and follows the protocol
                output.success(
                    "Git credential helper (libsecret) is properly configured",
                    logger=logger,
                )
                logger = logger.bind(returncode=result.returncode)
                logger.log_info("git_credential_helper_validated")
                return True
            except TimeoutExpired:
                output.warning("Git credential helper test timed out", logger=logger)
                return False
            except CalledProcessError as e:
                # Without D-Bus and a secret service (containers) the helper
                # exits 1 even for a valid query; the binary itself is fine.
                if self._is_running_in_container(logger):
                    logger.log_exception(e, "git_credential_helper_in_container_failed")
                    output.warning(
                        "Git credential helper cannot reach a secret service in a "
                        "container; skipping the functional check",
                        logger=logger,
                    )
                    return True
                output.warning(
                    f"Error testing git credential helper: {e}", logger=logger
                )
                return False
            except Exception as e:  # noqa: BLE001
                output.warning(
                    f"Error testing git credential helper: {e}", logger=logger
                )
                return False

        except Exception as e:  # noqa: BLE001
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
                    run_interactive_command(
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
        except Exception as e:  # noqa: BLE001
            logger.log_exception(e, "shell_setup_failed")
            output.warning(f"Could not check/change shell: {e}")

    def setup_ssh_key(self, logger: LoggingHelpers, output: ConsoleOutput):
        """Ensure ~/.ssh/id_ed25519 exists, is cached by the agent and is on GitHub.

        Every step is idempotent, so re-running repairs a partial setup.
        Host is recorded in the key comment and GitHub title.
        """
        hostname = socket.gethostname()
        ssh_dir = self.homedir / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        key = ssh_dir / "id_ed25519"
        pub_key = ssh_dir / "id_ed25519.pub"

        if not key.exists():
            # Interactive so a passphrase can be entered (empty is allowed)
            run_interactive_command(
                [
                    "ssh-keygen",
                    "-t",
                    "ed25519",
                    "-C",
                    f"{hostname} {self.config.ssh_key_email}",
                    "-f",
                    str(key),
                ],
                logger,
                output,
                "Generate SSH key",
                timeout=600,
            )
            output.success(f"Created SSH key {key}", logger=logger)

        # Let ssh cache the key in the running agent on first use
        ssh_config = ssh_dir / "config"
        existing = ssh_config.read_text() if ssh_config.exists() else ""
        if "AddKeysToAgent" not in existing:
            with open(ssh_config, "a") as f:
                f.write("\nHost *\n    AddKeysToAgent yes\n")
            ssh_config.chmod(0o600)
            output.success("Enabled AddKeysToAgent in ~/.ssh/config", logger=logger)

        key_blob = pub_key.read_text().split()[1]
        listed = run_command_with_error_handling(
            ["/usr/bin/gh", "ssh-key", "list"], logger, output, "List GitHub SSH keys"
        )
        has_auth, has_signing = parse_ssh_key_list(listed.stdout, key_blob)
        if has_auth:
            output.success("SSH key already on GitHub", logger=logger)
        else:
            run_command_with_error_handling(
                [
                    "/usr/bin/gh",
                    "ssh-key",
                    "add",
                    str(pub_key),
                    "-t",
                    hostname,
                ],
                logger,
                output,
                "Add SSH key to GitHub",
            )
            output.success("Uploaded SSH key to GitHub", logger=logger)

        self.setup_ssh_signing(logger, output, pub_key, has_signing)

    def setup_ssh_signing(
        self,
        logger: LoggingHelpers,
        output: ConsoleOutput,
        pub_key: Path,
        registered: bool,
    ) -> None:
        """Register the SSH key as a GitHub signing key and write allowed_signers.

        git/config signs commits and tags with this key (gpg.format = ssh).
        GitHub needs it as a separate "signing" key to show "Verified", and
        git needs ~/.ssh/allowed_signers to verify signatures locally.
        """
        hostname = socket.gethostname()
        if registered:
            output.success("SSH signing key already on GitHub", logger=logger)
        else:
            # The token needs an extra scope; this opens the browser flow
            run_interactive_command(
                [
                    "/usr/bin/gh",
                    "auth",
                    "refresh",
                    "-h",
                    "github.com",
                    "-s",
                    "admin:ssh_signing_key",
                ],
                logger,
                output,
                "Add GitHub scope for SSH signing keys",
                timeout=600,
            )
            run_command_with_error_handling(
                [
                    "/usr/bin/gh",
                    "ssh-key",
                    "add",
                    str(pub_key),
                    "--type",
                    "signing",
                    "-t",
                    f"{hostname} signing",
                ],
                logger,
                output,
                "Add SSH signing key to GitHub",
            )
            output.success("Uploaded SSH signing key to GitHub", logger=logger)

        try:
            email = run_command_with_error_handling(
                ["git", "config", "--get", "user.email"],
                logger,
                output,
                "Read git user.email",
            ).stdout.strip()
        except CalledProcessError:
            output.warning(
                "git user.email is not set, skipping ~/.ssh/allowed_signers",
                logger=logger,
            )
            return

        keys = [" ".join(pub_key.read_text().split()[:2])]
        try:
            api = run_command_with_error_handling(
                [
                    "/usr/bin/gh",
                    "api",
                    "user/ssh_signing_keys",
                    "--jq",
                    ".[].key",
                ],
                logger,
                output,
                "List GitHub signing keys",
            )
            keys.extend(api.stdout.split("\n"))
        except CalledProcessError:
            logger.log_warning("github_signing_keys_unavailable")

        allowed_signers = self.homedir / ".ssh" / "allowed_signers"
        if write_allowed_signers(allowed_signers, email, keys):
            output.success(f"Updated {allowed_signers}", logger=logger)

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

        self.setup_ssh_key(logger, output)

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
                run_interactive_command(
                    ["sudo", "tailscale", "up", "--operator=do3cc"], logger, output
                )
            else:
                output.success("Tailscale is connected", logger=logger)
        except CalledProcessError:
            output.status("Tailscale not available, running setup...", logger=logger)
            run_interactive_command(
                ["sudo", "tailscale", "up", "--operator=do3cc"], logger, output
            )


class Arch(Linux):
    def _get_base_config(self) -> EnvironmentConfig:
        """Get base configuration for Arch Linux systems."""
        base = super()._get_base_config()

        # Read packages from manifest instead of hardcoding
        base_packages = cast(
            list[str], self.package_manifest.get("base", {}).get("arch", [])
        )
        aur_packages = cast(
            list[str], self.package_manifest.get("aur", {}).get("base", [])
        )

        arch_config = EnvironmentConfig(
            packages=base_packages,
            aur_packages=aur_packages,
            systemd_services=["tailscaled"],
        )
        return arch_config.merge_with(base)

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
                ["pacman", "-Q"] + list(packages), logger, output
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
        except Exception as e:  # noqa: BLE001
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
            age = datetime.now() - last_update  # noqa: DTZ005
            return age.total_seconds() > 86400  # 24 hours
        except (ValueError, OSError):
            return True

    def mark_system_updated(self, logger: LoggingHelpers) -> None:
        """Mark system as updated with current timestamp"""
        marker_file = Path.home() / ".cache" / "dotfiles_last_update"
        marker_file.parent.mkdir(exist_ok=True)
        timestamp = datetime.now().isoformat()  # noqa: DTZ005
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
                        # Don't mark as updated if it failed - let it retry next time
                        # Raise exception so it's tracked in error summary
                        raise RuntimeError(f"System update failed: {result.message}")
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

        def pacman(
            *args: str, logger: LoggingHelpers, **kwargs: Any
        ) -> CompletedProcess[str]:
            """
            Execute pacman commands with real-time output, error handling, and retry logic.

            Key improvements implemented here:
            1. Real-time output streaming via run_interactive_command
            2. Interactive sudo password prompt support
            3. Reduced timeout for faster failure detection
            4. Comprehensive error handling with retries
            5. Consistent timeout with APT operations (600s)

            Arch Linux advantages:
            - Uses --noconfirm to prevent interactive prompts (no timezone issues)
            - No environment variable complications like APT
            - Generally faster package operations than APT
            """
            max_retries = 3
            for attempt in range(max_retries):
                pacman_logger = logger.bind(attempt=attempt)
                try:
                    # Use interactive command to allow sudo password prompt
                    result = run_interactive_command(
                        ["sudo", "pacman"] + list(args),
                        pacman_logger,
                        output,
                        "pacman operation",
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
                    # Note: No stdout/stderr available since we don't capture interactive output
                    raise
            raise RuntimeError("pacman retry loop exited unexpectedly")

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
                pacman("-S", "--needed", "--noconfirm", *missing, logger=logger)
                output.success("Base development tools installed", logger=logger)
                self.restart_required = True
            else:
                output.success("All base development tools already installed")

            # Create projects directory safely
            projects_dir = self.homedir / "projects"
            logger = logger.bind(projects_dir=projects_dir)
            try:
                projects_dir.mkdir(parents=True, exist_ok=True)
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
                yay_dir = self.homedir / "projects/yay-bin"
                logger = logger.bind(yay_dir=yay_dir)
                if not yay_dir.exists():
                    try:
                        output.status("Cloning yay AUR helper...", logger=logger)
                        # Use streaming subprocess for git clone to show progress
                        # Git clone can take time depending on network speed
                        run_command_with_error_handling(
                            [
                                "git",
                                "clone",
                                "https://aur.archlinux.org/yay-bin.git",
                                str(yay_dir),
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
                    raise
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
                            ["yay", "-S", "--needed", "--noconfirm"]
                            + list(missing_aur),
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
                        run_interactive_command(
                            ["sudo", "systemctl", "start", service], logger, output
                        )
                        output.success(f"Started service: {service}", logger=logger)
                    else:
                        output.status(
                            f"Enabling and starting service: {service}",
                            emoji="🔄",
                            logger=logger,
                        )
                        run_interactive_command(
                            ["sudo", "systemctl", "enable", "--now", service],
                            logger,
                            output,
                        )
                        output.success(
                            f"Enabled and started service: {service}", logger=logger
                        )

                except CalledProcessError as e:
                    # In containers, systemd services often fail - this is expected
                    stderr_lower = (e.stderr or "").lower()
                    if (
                        "chroot" in stderr_lower
                        or "failed to connect to bus" in stderr_lower
                        or "not available" in stderr_lower
                    ):
                        logger.log_exception(e, "service_enable_in_container_failed")
                        output.warning(
                            f"Cannot enable {service} in container environment"
                        )
                    else:
                        logger.log_exception(e, "service_enable_failed")
                        output.error(f"Failed to enable service {service}: {e.stderr}")
                        # Don't raise here - continue with other services

            # Link and enable systemd user services
            user_services = self.config.systemd_user_services
            if user_services:
                logger = logger.bind(user_services=user_services)
                output.status(
                    f"Checking {len(user_services)} systemd user services...",
                    logger=logger,
                )

                # Symlink unit files into ~/.config/systemd/user/
                dotfiles_dir = Path(__file__).parent.parent.parent
                systemd_user_dir = self.homedir / ".config/systemd/user"
                systemd_user_dir.mkdir(parents=True, exist_ok=True)

                for unit_file in (dotfiles_dir / "systemd").iterdir():
                    target = systemd_user_dir / unit_file.name
                    if target.is_symlink() and target.resolve() == unit_file.resolve():
                        continue
                    if target.exists() or target.is_symlink():
                        target.unlink()
                    os.symlink(unit_file, target)
                    output.success(f"{target} → {unit_file}", logger=logger)

                # Reload systemd user daemon to pick up new unit files
                self._reload_systemd_user_daemon(logger, output)

                for service in user_services:
                    try:
                        is_enabled, is_active = self.check_systemd_service_status(
                            service, logger, output, user=True
                        )

                        if is_enabled and is_active:
                            output.success(
                                f"User service already enabled and active: {service}",
                                logger=logger,
                            )
                            continue
                        elif is_enabled and not is_active:
                            output.status(
                                f"Starting user service: {service}",
                                emoji="🔄",
                                logger=logger,
                            )
                            run_command_with_error_handling(
                                ["systemctl", "--user", "start", service],
                                logger,
                                output,
                                f"systemctl --user start {service}",
                            )
                            output.success(
                                f"Started user service: {service}", logger=logger
                            )
                        else:
                            output.status(
                                f"Enabling user service: {service}",
                                emoji="🔄",
                                logger=logger,
                            )
                            run_command_with_error_handling(
                                ["systemctl", "--user", "enable", "--now", service],
                                logger,
                                output,
                                f"systemctl --user enable --now {service}",
                            )
                            output.success(
                                f"Enabled user service: {service}", logger=logger
                            )

                    except CalledProcessError as e:
                        stderr_lower = (e.stderr or "").lower()
                        if (
                            "chroot" in stderr_lower
                            or "failed to connect to bus" in stderr_lower
                            or "not available" in stderr_lower
                        ):
                            logger.log_exception(
                                e, "user_service_enable_in_container_failed"
                            )
                            output.warning(
                                f"Cannot enable {service} in container environment"
                            )
                        else:
                            logger.log_exception(e, "user_service_enable_failed")
                            output.error(
                                f"Failed to enable user service {service}: {e.stderr}"
                            )

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
    def validate_git_credential_helper(
        self, logger: LoggingHelpers, output: ConsoleOutput
    ) -> bool:
        """Debian and Ubuntu do not package the libsecret helper as a binary.

        git only ships its source under /usr/share/doc/git/contrib, so a
        missing helper is a known limitation here, not an installation error.
        """
        if not self.LIBSECRET_HELPER.exists():
            logger = logger.bind(libsecret_path=self.LIBSECRET_HELPER)
            output.warning(
                f"git-credential-libsecret not found at {self.LIBSECRET_HELPER}; "
                "it is not packaged for Debian/Ubuntu (build it from "
                "/usr/share/doc/git/contrib/credential/libsecret)",
                logger=logger,
            )
            logger.log_warning("git_credential_helper_not_packaged")
            return True
        return super().validate_git_credential_helper(logger, output)

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
        except Exception as e:  # noqa: BLE001
            logger.log_exception(e, "dpkg_check_failed", packages=packages)
            # If dpkg check fails, assume all packages need installation
            return [], packages

    @property
    def apt_packages(self) -> list[str]:
        """Get Debian/Ubuntu package list from manifest"""
        return self.package_manifest["base"]["debian"]

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
                run_interactive_command(
                    ["sudo", "ln", "-fs", "/usr/share/zoneinfo/UTC", "/etc/localtime"],
                    logger,
                    output,
                    "Set timezone symlink to UTC",
                    timeout=30,
                )

                # Step 2: Set the timezone name in /etc/timezone for consistency
                # Some tools and packages read this file to determine the timezone name
                run_interactive_command(
                    ["sudo", "sh", "-c", "echo 'UTC' > /etc/timezone"],
                    logger,
                    output,
                    "Set timezone name to UTC",
                    timeout=30,
                )

                output.success("Timezone pre-configured to UTC", logger=logger)
            except Exception as e:  # noqa: BLE001
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
            1. Real-time output streaming via run_interactive_command
            2. Interactive sudo password prompt support
            3. Non-interactive environment setup (DEBIAN_FRONTEND=noninteractive)
            4. Reduced timeout for faster failure detection
            5. Comprehensive error handling with retries

            Note: DEBIAN_FRONTEND=noninteractive may not work with sudo due to
            environment variable filtering, but we set it anyway as a fallback.
            The primary solution is timezone pre-configuration above.
            """
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger = logger.bind(retry_attempt=attempt)
                    # Set up non-interactive environment to prevent prompts
                    env = os.environ.copy()
                    env["DEBIAN_FRONTEND"] = "noninteractive"

                    # Use interactive command to allow sudo password prompt
                    result = run_interactive_command(
                        ["sudo", "apt-get"] + list(args),
                        logger,
                        output,
                        "apt-get operation",
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
                    logger.log_exception(e, "apt_operation_failed")
                    # Note: No stderr available since we don't capture interactive output
                    # Provide generic guidance based on common apt-get errors
                    output.error(f"APT operation failed with exit code {e.returncode}")
                    output.info(
                        "Try: Check for lock files or permission issues", emoji="💡"
                    )
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
            nvim_appimage = self.homedir / "nvim.appimage"
            logger = logger.bind(nvim_appimage=nvim_appimage)
            if not nvim_appimage.exists():
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

                        with (
                            urllib.request.urlopen(request, timeout=300) as response,
                            open(nvim_appimage, "wb") as f,
                        ):
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
                bin_dir = self.homedir / "bin"
                logger = logger.bind()
                try:
                    bin_dir.mkdir(parents=True)
                    output.success("~/bin directory created", logger=logger)
                except OSError as e:
                    logger.log_exception(e, "neovim_appimage_permissions_failed")
                    output.error(f"Cannot create ~/bin directory: {e}")
                    output.info("Try: Check home directory permissions", emoji="💡")
                    raise

                # Create symlink to nvim
                nvim_symlink = self.homedir / "bin/nvim"
                logger = logger.bind(nvim_symlink=nvim_symlink)
                if not nvim_symlink.exists():
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


def parse_ssh_key_list(stdout: str, key_blob: str) -> tuple[bool, bool]:
    """Return (authentication key present, signing key present) for a key blob.

    `gh ssh-key list` prints one line per registered key; the same public key can
    appear twice, once as authentication and once as signing key.
    """
    has_auth = has_signing = False
    for line in stdout.splitlines():
        if key_blob not in line:
            continue
        if "signing" in line.lower().split():
            has_signing = True
        else:
            has_auth = True
    return has_auth, has_signing


def write_allowed_signers(path: Path, email: str, keys: list[str]) -> bool:
    """Make sure every key is listed for `email` in an ssh allowed_signers file.

    Existing lines are kept. Returns True if the file changed.
    """
    existing = path.read_text().splitlines() if path.exists() else []
    lines = list(existing)
    for key in keys:
        key = key.strip()
        if not key:
            continue
        line = f'{email} namespaces="git" {key}'
        if line not in lines:
            lines.append(line)
    if lines == existing:
        return False
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return True


def detect_operating_system(logger: LoggingHelpers, no_remote_mode: bool = False):
    """Detect and return the appropriate operating system class"""
    with open("/etc/os-release") as release_file:
        content = release_file.read()
        logger = logger.bind(release_data=content)
        if (
            'NAME="Arch Linux"' in content
            or 'NAME="CachyOS Linux"' in content
            or 'NAME="Garuda Linux"' in content
        ):
            return Arch(no_remote_mode=no_remote_mode)
        elif "ID=debian" in content or "ID_LIKE=debian" in content:
            return Debian(no_remote_mode=no_remote_mode)
        else:
            logger.log_error("Unknown OS")
            raise NotImplementedError(f"Unknown operating system, found {content}")


@click.command()
@click.option(
    "--no-remote",
    is_flag=True,
    help="Skip remote activities (GitHub, SSH keys, Tailscale)",
)
@click.option("--quiet", is_flag=True, help="Suppress non-essential output")
@click.option("--verbose", is_flag=True, help="Show detailed output")
@click.option(
    "--clear-cache",
    is_flag=True,
    help="Clear cached state (system update timestamp) before running",
)
def main(no_remote: bool, quiet: bool, verbose: bool, clear_cache: bool):
    """Install and configure dotfiles for Linux systems

    \\b
    Examples:
      dotfiles-init
      dotfiles-init --no-remote
      dotfiles-init --verbose
    """
    # Initialize logging and console output
    logger = setup_logging("init").bind(
        verbose=verbose, quiet=quiet, no_remote_mode=no_remote, clear_cache=clear_cache
    )
    output = ConsoleOutput(verbose=verbose, quiet=quiet)

    logger.log_info("init_script_started")

    # Clear cache if requested (useful for testing)
    if clear_cache:
        cache_file = Path.home() / ".cache" / "dotfiles_last_update"
        if cache_file.exists():
            try:
                cache_file.unlink()
                output.status("Cleared cache: dotfiles_last_update", logger=logger)
                logger.log_info("cache_cleared", cache_file=str(cache_file))
            except OSError as e:
                output.warning(f"Could not clear cache: {e}", logger=logger)
                logger.log_exception(e, "cache_clear_failed")
        else:
            output.status("No cache to clear", logger=logger)

    try:
        if "DOTFILES_ENVIRONMENT" in os.environ:
            output.error(
                "DOTFILES_ENVIRONMENT is no longer supported: there are no profiles",
                logger=logger,
            )
            output.info("Unset it and run dotfiles-init again", emoji="💡")
            sys.exit(1)

        logger.log_info("init_started", no_remote_mode=no_remote)

        output.status(
            f"Installing dotfiles{' (no-remote mode)' if no_remote else ''}",
            "🚀",
        )

        try:
            operating_system = detect_operating_system(logger, no_remote_mode=no_remote)
        except FileNotFoundError as e:
            logger.log_exception(e, "os_detection_file_missing")
            output.error(
                "Cannot detect operating system (/etc/os-release not found)",
                logger=logger,
            )
            output.info("This script only supports Linux distributions")
            sys.exit(1)
        except NotImplementedError as e:
            logger.log_exception(e, "os_not_supported")
            output.error(str(e))
            output.info(
                "This script currently supports Arch Linux, Garuda Linux, and Debian-based systems"
            )
            sys.exit(1)

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
                "Linking local bin scripts",
                lambda logger: operating_system.link_local_bin(logger, output),
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

        # Execute steps with simple status messages (no persistent progress context)
        # This allows sudo password prompts to display clearly
        errors: list[str] = []  # Track failures

        for i, (step_name, step_func) in enumerate(steps):
            step_log = logger.bind(step_num=i, step_name=step_name)
            try:
                step_log.log_info("step_started")
                output.status(f"[{i + 1}/{len(steps)}] {step_name}...", emoji="🔄")
                result = step_func(step_log)

                # Check if step returned False (validation failure)
                # Some steps return bool, some return None
                if result is False:
                    error_msg = f"{step_name} validation failed"
                    errors.append(error_msg)
                    output.error(error_msg, logger=step_log)
                else:
                    output.success(
                        f"[{i + 1}/{len(steps)}] {step_name} completed", logger=step_log
                    )
            except KeyboardInterrupt:
                output.error(f"{step_name} interrupted by user", logger=step_log)
                sys.exit(130)
            except Exception as e:  # noqa: BLE001
                step_log.log_exception(
                    e,
                    "step_failed",
                )
                error_msg = f"{step_name}: {e}"
                errors.append(error_msg)
                output.error(f"ERROR in {step_name}: {e}")
                if verbose:
                    output.info("DETAILED ERROR INFORMATION:")
                    traceback.print_exc()
                    output.info("Check the error details above and retry")
                # Continue to next step instead of exiting immediately

        # Report final status
        if errors:
            logger = logger.bind(error_count=len(errors), errors=errors)
            output.error(
                f"Dotfiles installation completed with {len(errors)} error(s):",
                "❌",
                logger=logger,
            )
            for error in errors:
                output.error(f"  - {error}")
            sys.exit(1)

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

    except Exception as e:  # noqa: BLE001
        logger.log_exception(e, "init_script_unexpected_error")
        output.error(f"UNEXPECTED ERROR: {e}")
        if verbose:
            output.info("DETAILED ERROR INFORMATION:")
            traceback.print_exc()
        output.info("Please report this issue with the full error message")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
# Trigger PR update
