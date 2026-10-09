from unittest.mock import MagicMock

from dotfiles import init


def test_setup_syncthing_ignore(tmp_path):
    projects = tmp_path / "projects"
    dotfiles = projects / "dotfiles"
    (dotfiles / "syncthing").mkdir(parents=True)
    (dotfiles / "syncthing" / "stignore").write_text(".git\n")
    (projects / ".stignore").write_text("/local/only\n")
    linux = init.Linux(homedir=tmp_path)
    logger = MagicMock()
    logger.bind.return_value = logger

    linux.setup_syncthing_ignore(dotfiles, logger, MagicMock())
    linux.setup_syncthing_ignore(dotfiles, logger, MagicMock())  # idempotent

    assert (projects / ".stignore").read_text() == (
        "#include dotfiles/syncthing/stignore\n/local/only\n"
    )


def test_enables_syncthing():
    assert "syncthing.service" in init.Linux().config.systemd_user_services
