"""run-claude.sh builds its Docker image from packages.yaml (replaces the grep script).

The script reads the manifest from inside a heredoc, so a renamed or removed key
in packages.yaml would only surface when someone builds the image. These tests
catch that: every manifest path the script reads must exist, and the package
list it installs must be a list of strings.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).parent.parent
SCRIPT = (REPO / "local_bin" / "run-claude.sh").read_text()
MANIFEST = yaml.safe_load((REPO / "packages.yaml").read_text())

# manifest['base']['debian'] -> ("base", "debian")
MANIFEST_PATHS = [
    tuple(re.findall(r"\['(\w+)'\]", match))
    for match in re.findall(r"manifest(?:\['\w+'\])+", SCRIPT)
]


def test_the_script_reads_the_manifest():
    assert ("base", "debian") in MANIFEST_PATHS


def test_every_manifest_path_the_script_reads_exists_in_packages_yaml():
    for path in MANIFEST_PATHS:
        node = MANIFEST
        for key in path:
            assert key in node, (
                f"run-claude.sh reads manifest{list(path)}; {key!r} is missing"
            )
            node = node[key]


def test_the_debian_package_list_is_a_list_of_strings():
    packages = MANIFEST["base"]["debian"]
    assert packages
    assert all(isinstance(package, str) and package for package in packages)


def test_the_image_build_copies_the_manifest_and_can_parse_it():
    assert "COPY packages.yaml" in SCRIPT
    assert "python3-yaml" in SCRIPT
