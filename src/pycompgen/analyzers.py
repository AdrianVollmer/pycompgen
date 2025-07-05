import subprocess
from pathlib import Path
from typing import List, Optional

from .models import InstalledPackage, CompletionPackage, CompletionType, PackageManager


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


def detect_completion_type(package: InstalledPackage) -> Optional[CompletionType]:
    """Detect if package uses click or argcomplete."""
    # Look for click or argcomplete in the package's environment
    python_path = get_python_path(package)

    if not python_path:
        return None

    # Check for click
    if has_dependency(python_path, "click"):
        return CompletionType.CLICK

    # Check for argcomplete
    if has_dependency(python_path, "argcomplete"):
        return CompletionType.ARGCOMPLETE

    return None


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


def has_dependency(python_path: Path, dependency: str) -> bool:
    """Check if a dependency is installed in the Python environment."""
    try:
        result = subprocess.run(
            [str(python_path), "-c", f"import {dependency}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False


def find_package_commands(package: InstalledPackage) -> List[str]:
    """Find the main command(s) for a package."""
    # Use commands from package manager output if available
    if package.commands:
        return package.commands
    
    # Fallback to package name if no commands found
    return [package.name]


def verify_completion_support(package: CompletionPackage) -> bool:
    """Verify that the package actually supports completion generation."""
    python_path = get_python_path(package.package)
    if not python_path:
        return False

    for command in package.commands:
        if package.completion_type == CompletionType.CLICK:
            # Try to generate click completion
            if test_click_completion(python_path, command):
                return True
        elif package.completion_type == CompletionType.ARGCOMPLETE:
            # Try to verify argcomplete support
            if test_argcomplete_completion(python_path, command):
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
