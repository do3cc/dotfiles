# pyright: reportMissingImports=false, reportArgumentType=false
import random
import subprocess
from unittest.mock import MagicMock

import faker
import pytest
from hypothesis import HealthCheck, given, strategies
from hypothesis import settings as h_settings

from dotfiles import init

m_faker = faker.Faker()


@pytest.mark.parametrize(
    "email_a,email_b,email_merge",
    [
        (None, None, None),
        ("a@b.c", m_faker.email(), "a@b.c"),
        (None, "a@b.c", "a@b.c"),
        ("a@b.c", None, "a@b.c"),
    ],
)
def test_environmentconfig_merge_email(email_a: str, email_b: str, email_merge: str):
    env_config_a = init.EnvironmentConfig(ssh_key_email=email_a)
    env_config_b = init.EnvironmentConfig(ssh_key_email=email_b)
    final_config = env_config_a.merge_with(env_config_b)
    assert email_a == env_config_a.ssh_key_email
    assert email_merge == final_config.ssh_key_email


@pytest.mark.parametrize(
    "attribute", ("packages", "aur_packages", "config_dirs", "systemd_services")
)
def test_environmentconfig_merge_duplicatehandling(attribute: str, faker):
    packages_a = [faker.word() for _ in range(random.randint(1, 50))]
    packages_b = [faker.word() for _ in range(random.randint(1, 50))]
    aur_packages_a = [faker.word() for _ in range(random.randint(1, 50))]
    aur_packages_b = [faker.word() for _ in range(random.randint(1, 50))]
    config_dirs_a = [(faker.word(), faker.word()) for _ in range(random.randint(1, 50))]
    config_dirs_b = [(faker.word(), faker.word()) for _ in range(random.randint(1, 50))]
    systemd_services_a = [faker.word() for _ in range(random.randint(1, 50))]
    systemd_services_b = [faker.word() for _ in range(random.randint(1, 50))]
    env_config_a = init.EnvironmentConfig(
        packages=packages_a,
        aur_packages=aur_packages_a,
        config_dirs=config_dirs_a,
        systemd_services=systemd_services_a,
    )
    env_config_b = init.EnvironmentConfig(
        packages=packages_b,
        aur_packages=aur_packages_b,
        config_dirs=config_dirs_b,
        systemd_services=systemd_services_b,
    )
    duplicate = getattr(env_config_b, attribute)[0]
    getattr(env_config_a, attribute).append(duplicate)

    final_config = env_config_a.merge_with(env_config_b)
    # After adding a duplicate, merged list should deduplicate
    # The tested attribute has a duplicate, so total unique = len(set(a+b))
    if attribute == "packages":
        assert len(packages_a + packages_b) > len(final_config.packages)
    elif attribute == "aur_packages":
        assert len(aur_packages_b + aur_packages_a) > len(final_config.aur_packages)
    elif attribute == "config_dirs":
        assert len(config_dirs_b + config_dirs_a) > len(final_config.config_dirs)
    elif attribute == "systemd_services":
        assert len(systemd_services_b + systemd_services_a) > len(
            final_config.systemd_services
        )


def test_environmentconfig_merge(faker: faker.Faker):
    packages_a = [faker.word() for _ in range(random.randint(1, 50))]
    packages_b = [faker.word() for _ in range(random.randint(1, 50))]
    aur_packages_a = [faker.word() for _ in range(random.randint(1, 50))]
    aur_packages_b = [faker.word() for _ in range(random.randint(1, 50))]
    config_dirs_a = [(faker.word(), faker.word()) for _ in range(random.randint(1, 50))]
    config_dirs_b = [(faker.word(), faker.word()) for _ in range(random.randint(1, 50))]
    systemd_services_a = [faker.word() for _ in range(random.randint(1, 50))]
    systemd_services_b = [faker.word() for _ in range(random.randint(1, 50))]
    email_a = faker.email()
    email_b = faker.email()
    env_config_a = init.EnvironmentConfig(
        packages=packages_a,
        aur_packages=aur_packages_a,
        config_dirs=config_dirs_a,
        systemd_services=systemd_services_a,
        ssh_key_email=email_a,
    )
    env_config_b = init.EnvironmentConfig(
        packages=packages_b,
        aur_packages=aur_packages_b,
        config_dirs=config_dirs_b,
        systemd_services=systemd_services_b,
        ssh_key_email=email_b,
    )
    final_config = env_config_a.merge_with(env_config_b)
    assert set(packages_a + packages_b) == set(final_config.packages)
    assert set(aur_packages_b + aur_packages_a) == set(final_config.aur_packages)
    assert set(config_dirs_b + config_dirs_a) == set(final_config.config_dirs)
    assert set(systemd_services_b + systemd_services_a) == set(
        final_config.systemd_services
    )
    assert email_a == final_config.ssh_key_email


@pytest.mark.parametrize("no_remote_mode", (False, True))
def test_LinuxInit(no_remote_mode):
    obj = init.Linux(no_remote_mode)
    assert isinstance(obj, init.Linux)


def test_Linux_getBaseConfig():
    assert isinstance(init.Linux(False)._get_base_config(), init.EnvironmentConfig)


def test_base_config_contains_desktop_setup():
    config = init.Linux(False).config
    assert ("irssi", "irssi") in config.config_dirs
    assert ("ghostty", "ghostty") in config.config_dirs
    assert "syncthing.service" in config.systemd_user_services
    assert config.ssh_key_email == "sshkeys@patrick-gerken.de"


def test_arch_enables_tailscaled():
    assert "tailscaled" in init.Arch(False).config.systemd_services


@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    service_name=strategies.text(),
)
def test_checkSystemdServiceStatusNetworkFail(
    service_name,
    logger,
    output,
    monkeypatch,
):
    """Test that TimeoutExpired exceptions propagate from systemctl commands.

    Note: This test verifies exception propagation. The implementation was fixed to
    remove redundant returncode == 0 checks since run_command_with_error_handling
    uses check=True, making returncode always 0 when it returns successfully.
    """
    obj = init.Linux(False)

    def mockrun(*_):
        raise subprocess.TimeoutExpired("", 0)

    monkeypatch.setattr(init, "run_command_with_error_handling", mockrun)

    with pytest.raises(subprocess.TimeoutExpired):
        obj.check_systemd_service_status(service_name, logger, output)


@pytest.mark.parametrize(
    "service_name,enabled,active",
    [
        ("sshd.service", ("enabled", True), ("active", True)),
        ("sshd.service", ("disabled", False), ("active", True)),
        ("sshd.service", ("enabled", True), ("inactive", False)),
        ("sshd.service", ("disabled", False), ("inactive", False)),
        (
            "sshd.service",
            (subprocess.CalledProcessError(1, ""), False),
            ("active", False),
        ),
        (
            "sshd.service",
            ("enabled", False),
            (subprocess.CalledProcessError(1, ""), False),
        ),
    ],
)
def test_checkSystemdServiceStatus(
    service_name,
    enabled,
    active,
    logger,
    output,
    monkeypatch,
):
    obj = init.Linux(False)

    def mockrun(*args):
        retval = MagicMock()
        retval.returncode = 0
        if args[0][1] == "is-enabled":
            if isinstance(enabled[0], Exception):
                raise enabled[0]
            retval.stdout = enabled[0]
        elif args[0][1] == "is-active":
            if isinstance(active[0], Exception):
                raise active[0]
            retval.stdout = active[0]
        return retval

    monkeypatch.setattr(init, "run_command_with_error_handling", mockrun)

    assert (enabled[1], active[1]) == obj.check_systemd_service_status(
        service_name, logger, output
    )


@pytest.mark.parametrize(
    "os_content,expected_class",
    [
        ('NAME="Arch Linux"\nID=arch', init.Arch),
        ('NAME="CachyOS Linux"\nID=cachyos', init.Arch),
        ('NAME="Garuda Linux"\nID=garuda', init.Arch),
        ('ID=debian\nNAME="Debian GNU/Linux"', init.Debian),
        ('ID=ubuntu\nID_LIKE=debian\nNAME="Ubuntu"', init.Debian),
    ],
)
def test_detect_operating_system_success(
    os_content, expected_class, tmp_path, mock_logging_helpers, monkeypatch
):
    """Test OS detection returns correct class for known operating systems."""
    # Create fake /etc/os-release
    os_release = tmp_path / "os-release"
    os_release.write_text(os_content)

    # Monkey patch the open() call to use our fake file
    import builtins

    original_open = builtins.open

    def mock_open(path, *args, **kwargs):
        if path == "/etc/os-release":
            return original_open(os_release, *args, **kwargs)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", mock_open)

    result = init.detect_operating_system(mock_logging_helpers, no_remote_mode=False)
    assert isinstance(result, expected_class)


def test_detect_operating_system_unknown(tmp_path, mock_logging_helpers, monkeypatch):
    """Test OS detection raises NotImplementedError for unknown OS."""
    # Create fake /etc/os-release with unknown OS
    os_release = tmp_path / "os-release"
    os_release.write_text('NAME="Unknown OS"\nID=unknown')

    import builtins

    original_open = builtins.open

    def mock_open(path, *args, **kwargs):
        if path == "/etc/os-release":
            return original_open(os_release, *args, **kwargs)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", mock_open)

    with pytest.raises(NotImplementedError, match="Unknown operating system"):
        init.detect_operating_system(mock_logging_helpers, no_remote_mode=False)


def test_arch_check_packages_empty_list(mock_logging_helpers):
    """Test check_packages_installed returns empty lists for empty input."""
    arch = init.Arch(False)
    installed, missing = arch.check_packages_installed([], mock_logging_helpers, None)
    assert installed == []
    assert missing == []


def test_arch_check_packages_all_installed(mock_logging_helpers, monkeypatch):
    """Test check_packages_installed when all packages are installed."""
    arch = init.Arch(False)
    packages = ["git", "vim"]

    # Mock run_command_with_error_handling to return success
    def mock_run(*args):
        result = MagicMock()
        result.returncode = 0
        return result

    monkeypatch.setattr(init, "run_command_with_error_handling", mock_run)

    installed, missing = arch.check_packages_installed(
        packages, mock_logging_helpers, None
    )
    assert installed == packages
    assert missing == []


def test_arch_check_packages_some_missing(mock_logging_helpers, monkeypatch):
    """Test check_packages_installed when some packages are missing."""
    arch = init.Arch(False)
    packages = ["git", "nonexistent", "vim"]

    call_count = [0]

    def mock_run(cmd, *args):
        result = MagicMock()
        call_count[0] += 1

        # First call checks all packages - returns non-zero (some missing)
        if call_count[0] == 1:
            result.returncode = 1
            return result

        # Individual checks: git=installed, nonexistent=missing, vim=installed
        if "git" in cmd:
            result.returncode = 0
        elif "nonexistent" in cmd:
            result.returncode = 1
        elif "vim" in cmd:
            result.returncode = 0
        else:
            result.returncode = 1

        return result

    monkeypatch.setattr(init, "run_command_with_error_handling", mock_run)

    installed, missing = arch.check_packages_installed(
        packages, mock_logging_helpers, None
    )
    assert set(installed) == {"git", "vim"}
    assert missing == ["nonexistent"]


def test_arch_check_packages_exception(mock_logging_helpers, monkeypatch):
    """Test check_packages_installed handles exceptions by returning all missing."""
    arch = init.Arch(False)
    packages = ["git", "vim"]

    def mock_run(*args):
        raise RuntimeError("pacman error")

    monkeypatch.setattr(init, "run_command_with_error_handling", mock_run)

    installed, missing = arch.check_packages_installed(
        packages, mock_logging_helpers, None
    )
    assert installed == []
    assert missing == packages


def test_arch_should_update_system_no_marker(tmp_path, monkeypatch):
    """Test should_update_system returns True when marker file doesn't exist."""
    monkeypatch.setenv("HOME", str(tmp_path))
    arch = init.Arch(False)
    assert arch.should_update_system() is True


def test_arch_should_update_system_recent(tmp_path, monkeypatch):
    """Test should_update_system returns False when update was recent."""
    from datetime import datetime

    monkeypatch.setenv("HOME", str(tmp_path))
    marker_file = tmp_path / ".cache" / "dotfiles_last_update"
    marker_file.parent.mkdir(parents=True, exist_ok=True)

    # Write timestamp from 1 hour ago
    recent_time = datetime.now()
    marker_file.write_text(recent_time.isoformat())

    arch = init.Arch(False)
    assert arch.should_update_system() is False


def test_arch_should_update_system_old(tmp_path, monkeypatch):
    """Test should_update_system returns True when update was >24h ago."""
    from datetime import datetime, timedelta

    monkeypatch.setenv("HOME", str(tmp_path))
    marker_file = tmp_path / ".cache" / "dotfiles_last_update"
    marker_file.parent.mkdir(parents=True, exist_ok=True)

    # Write timestamp from 25 hours ago
    old_time = datetime.now() - timedelta(hours=25)
    marker_file.write_text(old_time.isoformat())

    arch = init.Arch(False)
    assert arch.should_update_system() is True


def test_arch_should_update_system_invalid_timestamp(tmp_path, monkeypatch):
    """Test should_update_system returns True for invalid timestamp."""
    monkeypatch.setenv("HOME", str(tmp_path))
    marker_file = tmp_path / ".cache" / "dotfiles_last_update"
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    marker_file.write_text("invalid timestamp")

    arch = init.Arch(False)
    assert arch.should_update_system() is True


def test_arch_mark_system_updated(tmp_path, monkeypatch, mock_logging_helpers):
    """Test mark_system_updated creates marker file with current timestamp."""
    from datetime import datetime

    monkeypatch.setenv("HOME", str(tmp_path))
    arch = init.Arch(False)

    arch.mark_system_updated(mock_logging_helpers)

    marker_file = tmp_path / ".cache" / "dotfiles_last_update"
    assert marker_file.exists()

    # Verify timestamp is parseable and recent (within last minute)
    timestamp_str = marker_file.read_text().strip()
    timestamp = datetime.fromisoformat(timestamp_str)
    age_seconds = (datetime.now() - timestamp).total_seconds()
    assert age_seconds < 60  # Should be very recent


@pytest.mark.property
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    packages=strategies.lists(strategies.text(min_size=1, max_size=20), max_size=50),
    aur_packages=strategies.lists(
        strategies.text(min_size=1, max_size=20), max_size=50
    ),
)
def test_environmentconfig_merge_always_deduplicates(packages, aur_packages):
    """Property test: merge always deduplicates packages and aur_packages."""
    config_a = init.EnvironmentConfig(packages=packages, aur_packages=aur_packages)
    config_b = init.EnvironmentConfig(
        packages=packages[:5], aur_packages=aur_packages[:5]
    )

    merged = config_a.merge_with(config_b)

    # Merged result should have no duplicates
    assert len(merged.packages) == len(set(merged.packages))
    assert len(merged.aur_packages) == len(set(merged.aur_packages))

    # All items from both configs should be in merged result
    assert set(packages + packages[:5]) == set(merged.packages)
    assert set(aur_packages + aur_packages[:5]) == set(merged.aur_packages)


@pytest.mark.property
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    config_dirs=strategies.lists(
        strategies.tuples(
            strategies.text(min_size=1, max_size=20),
            strategies.text(min_size=1, max_size=20),
        ),
        max_size=30,
    ),
    systemd_services=strategies.lists(
        strategies.text(min_size=1, max_size=20), max_size=30
    ),
)
def test_environmentconfig_merge_preserves_all_items(config_dirs, systemd_services):
    """Property test: merge preserves all unique items from both configs."""
    config_a = init.EnvironmentConfig(
        config_dirs=config_dirs, systemd_services=systemd_services
    )
    config_b = init.EnvironmentConfig(
        config_dirs=config_dirs[:3], systemd_services=systemd_services[:3]
    )

    merged = config_a.merge_with(config_b)

    # All unique items should be present
    assert set(config_dirs + config_dirs[:3]) == set(merged.config_dirs)
    assert set(systemd_services + systemd_services[:3]) == set(merged.systemd_services)


def test_debian_check_packages_empty_list(mock_logging_helpers):
    """Test Debian check_packages_installed returns empty lists for empty input."""
    debian = init.Debian(False)
    installed, missing = debian.check_packages_installed([], mock_logging_helpers, None)
    assert installed == []
    assert missing == []


def test_debian_check_packages_all_installed(mock_logging_helpers, monkeypatch):
    """Test Debian check_packages_installed when all packages are installed."""
    debian = init.Debian(False)
    packages = ["git", "vim"]

    def mock_run(cmd, *args):
        result = MagicMock()
        result.returncode = 0
        # dpkg -l output format: "ii  packagename  version  description"
        package_name = cmd[2]  # Third element is the package name
        result.stdout = f"ii  {package_name}  1.0  some description"
        return result

    monkeypatch.setattr(init, "run_command_with_error_handling", mock_run)

    installed, missing = debian.check_packages_installed(
        packages, mock_logging_helpers, None
    )
    assert installed == packages
    assert missing == []


def test_debian_check_packages_some_missing(mock_logging_helpers, monkeypatch):
    """Test Debian check_packages_installed when some packages are missing."""
    debian = init.Debian(False)
    packages = ["git", "nonexistent", "vim"]

    def mock_run(cmd, *args):
        result = MagicMock()
        package_name = cmd[2]

        if package_name == "nonexistent":
            # Package not installed - non-zero return or no 'ii' status
            result.returncode = 1
            result.stdout = "no packages found"
        else:
            # Package installed
            result.returncode = 0
            result.stdout = f"ii  {package_name}  1.0  description"

        return result

    monkeypatch.setattr(init, "run_command_with_error_handling", mock_run)

    installed, missing = debian.check_packages_installed(
        packages, mock_logging_helpers, None
    )
    assert set(installed) == {"git", "vim"}
    assert missing == ["nonexistent"]


def test_debian_check_packages_exception(mock_logging_helpers, monkeypatch):
    """Test Debian check_packages_installed handles exceptions."""
    debian = init.Debian(False)
    packages = ["git", "vim"]

    def mock_run(*args):
        raise RuntimeError("dpkg error")

    monkeypatch.setattr(init, "run_command_with_error_handling", mock_run)

    installed, missing = debian.check_packages_installed(
        packages, mock_logging_helpers, None
    )
    assert installed == []
    assert missing == packages


def test_main_rejects_dotfiles_environment():
    """A leftover DOTFILES_ENVIRONMENT must fail loudly, not be ignored."""
    from click.testing import CliRunner

    result = CliRunner().invoke(
        init.main, ["--quiet"], env={"DOTFILES_ENVIRONMENT": "private"}
    )
    assert result.exit_code == 1


def test_main_os_detection_failure(monkeypatch):
    """Test main() handles OS detection failures without crashing."""
    from click.testing import CliRunner

    # Mock detect_operating_system to raise FileNotFoundError
    def mock_detect(*args, **kwargs):
        raise FileNotFoundError("/etc/os-release not found")

    monkeypatch.setattr(init, "detect_operating_system", mock_detect)

    runner = CliRunner()
    result = runner.invoke(init.main, ["--quiet"])
    assert result.exit_code == 1


def test_main_unsupported_os(monkeypatch):
    """Test main() handles unsupported OS without crashing."""
    from click.testing import CliRunner

    # Mock detect_operating_system to raise NotImplementedError
    def mock_detect(*args, **kwargs):
        raise NotImplementedError("Unknown operating system")

    monkeypatch.setattr(init, "detect_operating_system", mock_detect)

    runner = CliRunner()
    result = runner.invoke(init.main, ["--quiet"])
    assert result.exit_code == 1


def _mock_os_with(monkeypatch, **overrides):
    mock_os = MagicMock(spec=init.Arch)
    mock_os.restart_required = False
    for name in (
        "install_dependencies",
        "link_configs",
        "link_local_bin",
        "validate_git_credential_helper",
        "setup_shell",
        "link_accounts",
    ):
        setattr(mock_os, name, overrides.get(name, MagicMock()))
    monkeypatch.setattr(init, "detect_operating_system", lambda *a, **k: mock_os)
    return mock_os


def test_main_exits_1_when_a_step_fails_validation(monkeypatch, tmp_path):
    from click.testing import CliRunner

    _mock_os_with(monkeypatch, install_dependencies=MagicMock(return_value=False))
    result = CliRunner().invoke(init.main, ["--quiet"], env={"HOME": str(tmp_path)})
    assert result.exit_code == 1


def test_main_exits_1_on_unexpected_error(monkeypatch, tmp_path):
    from click.testing import CliRunner

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(init, "detect_operating_system", boom)
    result = CliRunner().invoke(init.main, ["--quiet"], env={"HOME": str(tmp_path)})
    assert result.exit_code == 1


def test_main_exits_130_on_keyboard_interrupt(monkeypatch, tmp_path):
    from click.testing import CliRunner

    interrupted = MagicMock(side_effect=KeyboardInterrupt)
    _mock_os_with(monkeypatch, install_dependencies=interrupted)
    result = CliRunner().invoke(init.main, ["--quiet"], env={"HOME": str(tmp_path)})
    assert result.exit_code == 130


@pytest.mark.integration
def test_main_successful_execution(monkeypatch, tmp_path):
    """Integration test: main() executes successfully with all steps mocked."""
    from click.testing import CliRunner

    # Mock OS detection to return Arch
    mock_os = MagicMock(spec=init.Arch)
    mock_os.restart_required = False

    # Mock all the OS methods to do nothing
    mock_os.install_dependencies = MagicMock()
    mock_os.link_configs = MagicMock()
    mock_os.validate_git_credential_helper = MagicMock()
    mock_os.setup_shell = MagicMock()
    mock_os.link_accounts = MagicMock()

    def mock_detect(*args, **kwargs):
        return mock_os

    monkeypatch.setattr(init, "detect_operating_system", mock_detect)

    runner = CliRunner()
    result = runner.invoke(
        init.main,
        ["--quiet"],
        env={"HOME": str(tmp_path)},
    )

    # Should succeed (exit code 0 or None)
    assert result.exit_code == 0

    # Verify all steps were called
    mock_os.install_dependencies.assert_called_once()
    mock_os.link_configs.assert_called_once()
    mock_os.validate_git_credential_helper.assert_called_once()
    mock_os.setup_shell.assert_called_once()
    mock_os.link_accounts.assert_called_once()


def test_main_uses_status_messages_not_persistent_progress(monkeypatch, tmp_path):
    """Test that main() uses simple status messages instead of persistent progress context.

    This test verifies that the main loop does NOT use output.progress_context() as a
    persistent wrapper, which would block sudo password prompts. Instead, it should use
    simple status messages for each step.
    """
    from click.testing import CliRunner

    from dotfiles.output_formatting import ConsoleOutput

    # Mock OS detection to return Arch
    mock_os = MagicMock(spec=init.Arch)
    mock_os.restart_required = False
    mock_os.install_dependencies = MagicMock()
    mock_os.link_configs = MagicMock()
    mock_os.validate_git_credential_helper = MagicMock()
    mock_os.setup_shell = MagicMock()
    mock_os.link_accounts = MagicMock()

    def mock_detect(*args, **kwargs):
        return mock_os

    monkeypatch.setattr(init, "detect_operating_system", mock_detect)

    # Track calls to output methods
    original_progress = ConsoleOutput.progress_context
    original_status = ConsoleOutput.status
    original_success = ConsoleOutput.success

    progress_context_calls = []
    status_calls = []
    success_calls = []

    def mock_progress_context(self):
        progress_context_calls.append(True)
        return original_progress(self)

    def mock_status(self, *args, **kwargs):
        status_calls.append((args, kwargs))
        return original_status(self, *args, **kwargs)

    def mock_success(self, *args, **kwargs):
        success_calls.append((args, kwargs))
        return original_success(self, *args, **kwargs)

    monkeypatch.setattr(ConsoleOutput, "progress_context", mock_progress_context)
    monkeypatch.setattr(ConsoleOutput, "status", mock_status)
    monkeypatch.setattr(ConsoleOutput, "success", mock_success)

    runner = CliRunner()
    result = runner.invoke(
        init.main,
        [],
        env={"HOME": str(tmp_path)},
    )

    # Verify the invocation succeeded (no unhandled exceptions)
    assert result.exit_code == 0
    assert result.exception is None

    # Verify no persistent progress_context wrapper was used
    assert len(progress_context_calls) == 0, (
        "main() should not use progress_context() for persistent wrapper"
    )

    # Verify status messages were used for step progress
    assert len(status_calls) > 0, (
        "main() should use status() messages for step progress"
    )

    # Verify success messages were used
    assert len(success_calls) > 0, (
        "main() should use success() messages for completed steps"
    )


def test_debian_missing_libsecret_helper_is_not_an_error(
    monkeypatch, tmp_path, mock_logging_helpers
):
    """Debian does not package the helper binary, so a missing helper only warns."""
    monkeypatch.setattr(init.Linux, "LIBSECRET_HELPER", tmp_path / "missing")
    output = MagicMock()
    assert init.Debian(False).validate_git_credential_helper(
        mock_logging_helpers, output
    )
    output.warning.assert_called_once()


def test_arch_missing_libsecret_helper_fails_validation(
    monkeypatch, tmp_path, mock_logging_helpers
):
    monkeypatch.setattr(init.Linux, "LIBSECRET_HELPER", tmp_path / "missing")
    assert not init.Arch(False).validate_git_credential_helper(
        mock_logging_helpers, MagicMock()
    )


def _fake_helper(tmp_path, exit_code):
    helper = tmp_path / "git-credential-libsecret"
    helper.write_text(f"#!/bin/sh\nexit {exit_code}\n")
    helper.chmod(0o755)
    return helper


@pytest.mark.parametrize("in_container,expected", [(True, True), (False, False)])
def test_libsecret_helper_failing_without_secret_service(
    monkeypatch, tmp_path, mock_logging_helpers, in_container, expected
):
    """In a container the helper exits 1 (no D-Bus); on a real system that is an error."""
    monkeypatch.setattr(init.Linux, "LIBSECRET_HELPER", _fake_helper(tmp_path, 1))
    arch = init.Arch(False)
    monkeypatch.setattr(arch, "_is_running_in_container", lambda logger: in_container)
    assert (
        arch.validate_git_credential_helper(mock_logging_helpers, MagicMock())
        is expected
    )


def test_libsecret_helper_working_passes(monkeypatch, tmp_path, mock_logging_helpers):
    monkeypatch.setattr(init.Linux, "LIBSECRET_HELPER", _fake_helper(tmp_path, 0))
    arch = init.Arch(False)
    assert arch.validate_git_credential_helper(mock_logging_helpers, MagicMock())


@pytest.mark.parametrize("in_container", [True, False])
def test_reload_systemd_user_daemon_failure(
    monkeypatch, mock_logging_helpers, in_container
):
    """No systemd user session in containers: warn there, raise on a real system."""

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["systemctl"])

    monkeypatch.setattr(init, "run_command_with_error_handling", fail)
    arch = init.Arch(False)
    monkeypatch.setattr(arch, "_is_running_in_container", lambda logger: in_container)
    output = MagicMock()
    if in_container:
        arch._reload_systemd_user_daemon(mock_logging_helpers, output)
        output.warning.assert_called_once()
        assert "container" in output.warning.call_args.args[0]
        mock_logging_helpers.log_exception.assert_called_once()
    else:
        with pytest.raises(subprocess.CalledProcessError):
            arch._reload_systemd_user_daemon(mock_logging_helpers, output)
        output.warning.assert_not_called()
