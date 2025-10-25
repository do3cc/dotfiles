"""Tests for package manifest loading."""

from pathlib import Path
from dotfiles.init import Linux, Arch


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


def test_arch_reads_base_packages_from_manifest():
    """Arch class should read base packages from manifest"""
    arch = Arch(environment="minimal")

    # Verify base packages match manifest
    base_packages = arch.config.packages
    manifest_packages = arch.package_manifest["base"]["arch"]

    # Should include all base arch packages
    for pkg in manifest_packages:
        assert pkg in base_packages, f"Base package {pkg} missing from config"


def test_arch_reads_aur_packages_from_manifest():
    """Arch class should read AUR packages from manifest"""
    arch = Arch(environment="minimal")

    # Verify AUR packages match manifest
    aur_packages = arch.config.aur_packages
    manifest_aur = arch.package_manifest["aur"]["base"]

    # Should include all base AUR packages
    for pkg in manifest_aur:
        assert pkg in aur_packages, f"AUR package {pkg} missing from config"


def test_arch_environment_packages():
    """Arch private environment should include environment-specific packages"""
    arch = Arch(environment="private")

    packages = arch.config.packages
    env_packages = arch.package_manifest["environments"]["private"]["arch"]

    # Should include environment-specific packages
    for pkg in env_packages:
        assert pkg in packages, f"Private env package {pkg} missing"
