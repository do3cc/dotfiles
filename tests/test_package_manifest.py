"""Tests for package manifest loading."""

from pathlib import Path
from dotfiles.init import Linux


def test_package_manifest_loads():
    """Package manifest should load from packages.yaml"""
    linux = Linux(environment="minimal")

    assert hasattr(linux, "package_manifest")
    assert "base" in linux.package_manifest
    assert "arch" in linux.package_manifest["base"]
    assert "debian" in linux.package_manifest["base"]


def test_package_manifest_structure():
    """Package manifest should have expected structure"""
    linux = Linux(environment="minimal")
    manifest = linux.package_manifest

    # Check top-level keys
    assert "base" in manifest
    assert "environments" in manifest
    assert "aur" in manifest

    # Check base has OS-specific lists
    assert isinstance(manifest["base"]["arch"], list)
    assert isinstance(manifest["base"]["debian"], list)

    # Check environments
    for env in ["minimal", "work", "private"]:
        assert env in manifest["environments"]


def test_package_manifest_file_exists():
    """packages.yaml should exist in repo root"""
    manifest_path = Path(__file__).parent.parent / "packages.yaml"
    assert manifest_path.exists(), f"packages.yaml not found at {manifest_path}"
