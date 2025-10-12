from dotfiles import init
import subprocess
from unittest.mock import MagicMock
from hypothesis import given, strategies, settings as h_settings, HealthCheck
import random
import faker
import pytest

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
        packages=packages_a.copy(),
        aur_packages=aur_packages_a.copy(),
        config_dirs=config_dirs_a.copy(),
        systemd_services=systemd_services_a.copy(),
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
        assert len(set(packages_b + packages_a)) == len(final_config.packages)
    elif attribute == "aur_packages":
        assert len(set(aur_packages_b + aur_packages_a)) == len(
            final_config.aur_packages
        )
    elif attribute == "config_dirs":
        assert len(set(config_dirs_b + config_dirs_a)) == len(final_config.config_dirs)
    elif attribute == "systemd_services":
        assert len(set(systemd_services_b + systemd_services_a)) == len(
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
    assert (packages_b + packages_a) == final_config.packages
    assert (aur_packages_b + aur_packages_a) == final_config.aur_packages
    assert (config_dirs_b + config_dirs_a) == final_config.config_dirs
    assert (systemd_services_b + systemd_services_a) == final_config.systemd_services
    assert (email_a) == final_config.ssh_key_email


def test_help():
    assert init.show_help() is None


@pytest.mark.parametrize(
    "environment,no_remote_mode,should_succeed",
    (
        ("illegal", False, False),
        ("minimal", False, True),
        ("minimal", True, True),
    ),
)
def test_LinuxInit(environment, no_remote_mode, should_succeed):
    if should_succeed:
        obj = init.Linux(environment, no_remote_mode)
        assert isinstance(obj, init.Linux)
    else:
        with pytest.raises(AttributeError):
            init.Linux(environment, no_remote_mode)


def test_Linux_getBaseConfig():
    assert isinstance(
        init.Linux("minimal", False)._get_base_config(), init.EnvironmentConfig
    )


def test_getEnvironmentConfigs():
    for config in init.Linux("minimal", False)._get_environment_configs().values():
        assert isinstance(config, init.EnvironmentConfig)


@given(
    environments=strategies.lists(
        strategies.sampled_from(init.VALID_ENVIRONMENTS),
        min_size=2,
        max_size=2,
        unique=True,
    )
)
def test_buildEnvironmentConfig(environments):
    a = init.Linux(environments[0], False)
    b = init.Linux(environments[1], False)
    assert str(a) != str(b)


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
    obj = init.Linux("minimal", False)

    def mockrun():
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
            ("active", True),
        ),
        (
            "sshd.service",
            ("enabled", True),
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
    obj = init.Linux("minimal", False)

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


def test_install_dependencies(logger, output):
    pass  # TODO: Implement
