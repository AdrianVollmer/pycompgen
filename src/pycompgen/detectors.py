import json
import subprocess
from pathlib import Path
from typing import List

from .models import InstalledPackage, PackageManager


def detect_packages() -> List[InstalledPackage]:
    """Detect all installed packages from uv tool and pipx."""
    packages = []
    packages.extend(detect_uv_packages())
    packages.extend(detect_pipx_packages())
    return packages


def detect_uv_packages() -> List[InstalledPackage]:
    """Detect packages installed via uv tool."""

    try:
        result = subprocess.run(
            ["uv", "tool", "list", "--show-paths"],
            capture_output=True,
            text=True,
            check=True,
        )
        return parse_uv_output(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def detect_pipx_packages() -> List[InstalledPackage]:
    """Detect packages installed via pipx."""

    try:
        result = subprocess.run(
            ["pipx", "list", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        return parse_pipx_output(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def parse_uv_output(output: str) -> List[InstalledPackage]:
    """Parse uv tool list output.

    Expected format:
    package-name v1.0.0 (path: /path/to/package)
    - command1 (/path/to/bin/command1)
    - command2 (/path/to/bin/command2)
    """
    packages = []
    current_package = None
    commands = []

    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("- "):
            # This is a command line
            if current_package is not None:
                # Extract command name from "- command (/path/to/bin/command)"
                command_part = line[2:]  # Remove "- "
                if " (" in command_part:
                    command_name = command_part.split(" (")[0]
                    commands.append(command_name)
        else:
            # This is a package line - save previous package if exists
            if current_package is not None:
                current_package.commands = commands
                packages.append(current_package)
                commands = []

            # Parse format: "package-name v1.0.0 (path: /path/to/package)"
            parts = line.split(" ", 2)
            if len(parts) < 2:
                current_package = None
                continue

            name = parts[0]
            version = parts[1].lstrip("v")

            # Extract path from parentheses - new format: "(/path/to/package)"
            if len(parts) > 2 and parts[2].startswith("(") and parts[2].endswith(")"):
                path_str = parts[2][1:-1]  # Remove "(" and ")"
                path = Path(path_str)
            else:
                # If no path info, skip this package
                current_package = None
                continue

            current_package = InstalledPackage(
                name=name, path=path, manager=PackageManager.UV_TOOL, version=version
            )

    # Don't forget the last package
    if current_package is not None:
        current_package.commands = commands
        packages.append(current_package)

    return packages


def parse_pipx_output(output: str) -> List[InstalledPackage]:
    """Parse pipx list JSON output."""
    # Sample format:
    #  {
    #      "pipx_spec_version": "0.1",
    #      "venvs": {
    #          "black": {
    #              "metadata": {
    #                  "injected_packages": {},
    #                  "main_package": {
    #                      "app_paths": [
    #                          {
    #                              "__Path__": "/home/user/.local/pipx/venvs/black/bin/black",
    #                              "__type__": "Path"
    #                          },
    #                          {
    #                              "__Path__": "/home/user/.local/pipx/venvs/black/bin/blackd",
    #                              "__type__": "Path"
    #                          }
    #                      ],
    # ...

    try:
        data = json.loads(output)
        packages = []

        for name, info in data.get("venvs", {}).items():
            pyvenv_cfg = info.get("pyvenv_cfg", {})
            if "home" in pyvenv_cfg:
                # Get the venv path from the home directory
                venv_path = Path(pyvenv_cfg["home"]).parent
            else:
                # Fallback to constructing path from standard pipx location
                venv_path = Path.home() / ".local" / "pipx" / "venvs" / name

            main_package = info.get("metadata", {}).get("main_package", {})
            version = main_package.get("package_version")

            # Extract commands from the "apps" field
            commands = main_package.get("apps", [])

            packages.append(
                InstalledPackage(
                    name=name,
                    path=venv_path,
                    manager=PackageManager.PIPX,
                    version=version,
                    commands=commands,
                )
            )

        return packages
    except json.JSONDecodeError:
        return []
