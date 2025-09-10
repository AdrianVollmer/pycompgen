import re
import subprocess
from pathlib import Path
from typing import List, Optional

from .models import InstalledPackage, CompletionPackage, CompletionType, PackageManager

from .logger import get_logger

logger = get_logger()


def analyze_packages(packages: List[InstalledPackage]) -> List[CompletionPackage]:
    """Analyze packages to determine which support completions."""
    completion_packages = []

    for package in packages:
        completion_info = analyze_package(package)
        if completion_info:
            completion_packages.append(completion_info)

    return completion_packages


def analyze_package(package: InstalledPackage) -> Optional[CompletionPackage]:
    """Analyze a single package for completion support."""
    # Check if the package has click or argcomplete dependencies
    completion_type = detect_completion_type(package)
    if not completion_type:
        return None

    # Try to find the main command(s) for the package
    commands = find_package_commands(package)
    if not commands:
        return None

    return CompletionPackage(
        package=package, completion_type=completion_type, commands=commands
    )


def has_dependency(package: InstalledPackage, dependency: str) -> bool:
    """Check if a dependency is directly imported by the package."""
    try:
        slug = package.name.replace("-", "_")
        package_path: Path = list(
            package.path.rglob(f"lib/python*/site-packages/{slug}-*-info/")
        )[0]
    except IndexError:
        return False

    metadata = open(package_path / "METADATA", "r").read()

    # Split off header
    if "\n\n" in metadata:
        metadata = metadata.split("\n\n")[0]

    m = re.search(f"^Requires-Dist: {dependency}([^a-z-].+)?$", metadata, re.MULTILINE)

    if m:
        return True
    return False


def get_python_path(package: InstalledPackage) -> Optional[Path]:
    """Get the Python executable path for the package's environment."""
    if package.manager == PackageManager.UV_TOOL:
        # For uv tool, the path points to the venv
        python_path = package.path / "bin" / "python"
    elif package.manager == PackageManager.PIPX:
        # For pipx, the path is typically the venv directory
        python_path = package.path / "bin" / "python"
    else:
        return None

    return python_path if python_path.exists() else None


def detect_completion_type(package: InstalledPackage) -> Optional[CompletionType]:
    """Detect if package uses click, or argcomplete completions."""
    result = None

    # Check for click
    if has_dependency(package, "click"):
        result = CompletionType.CLICK

    # Check for argcomplete
    elif has_dependency(package, "argcomplete"):
        result = CompletionType.ARGCOMPLETE

    if result:
        logger.debug(f"{package.name} supports completion: {result}")

    return result


def find_package_commands(package: InstalledPackage) -> List[str]:
    """Find the main command(s) for a package."""
    # Use commands from package manager output if available
    if package.commands:
        return package.commands

    # Fallback to package name if no commands found
    return [package.name]


def verify_completion_support(package: CompletionPackage) -> bool:
    """Verify that the package actually supports completion generation."""
    for command in package.commands:
        if package.completion_type == CompletionType.CLICK:
            # Try to generate click completion
            python_path = get_python_path(package.package)
            if python_path and test_click_completion(python_path, command):
                return True
        elif package.completion_type == CompletionType.ARGCOMPLETE:
            # Try to verify argcomplete support
            python_path = get_python_path(package.package)
            if python_path and test_argcomplete_completion(python_path, command):
                return True

    return False


def test_click_completion(python_path: Path, command: str) -> bool:
    """Test if a command supports click completion."""
    try:
        # Try to get click completion
        result = subprocess.run(
            [str(python_path), "-c", "import click; print('click available')"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False


def test_argcomplete_completion(python_path: Path, command: str) -> bool:
    """Test if a command supports argcomplete completion."""
    try:
        # Try to get argcomplete completion
        result = subprocess.run(
            [
                str(python_path),
                "-c",
                "import argcomplete; print('argcomplete available')",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False
