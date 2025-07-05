import json
import subprocess
from pathlib import Path
from typing import List, Optional

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
    """
    packages = []
    for line in output.strip().split('\n'):
        if not line.strip():
            continue
            
        # Parse format: "package-name v1.0.0 (path: /path/to/package)"
        parts = line.strip().split(' ', 2)
        if len(parts) < 2:
            continue
            
        name = parts[0]
        version = parts[1].lstrip('v')
        
        # Extract path from parentheses
        if len(parts) > 2 and parts[2].startswith('(path: ') and parts[2].endswith(')'):
            path_str = parts[2][7:-1]  # Remove "(path: " and ")"
            path = Path(path_str)
        else:
            # If no path info, skip this package
            continue
            
        packages.append(InstalledPackage(
            name=name,
            path=path,
            manager=PackageManager.UV_TOOL,
            version=version
        ))
    
    return packages


def parse_pipx_output(output: str) -> List[InstalledPackage]:
    """Parse pipx list JSON output."""
    try:
        data = json.loads(output)
        packages = []
        
        for name, info in data.get('venvs', {}).items():
            pyvenv_cfg = info.get('pyvenv_cfg', {})
            if 'home' in pyvenv_cfg:
                # Get the venv path from the home directory
                venv_path = Path(pyvenv_cfg['home']).parent
            else:
                # Fallback to constructing path from standard pipx location
                venv_path = Path.home() / '.local' / 'share' / 'pipx' / 'venvs' / name
            
            version = info.get('metadata', {}).get('main_package', {}).get('package_version')
            
            packages.append(InstalledPackage(
                name=name,
                path=venv_path,
                manager=PackageManager.PIPX,
                version=version
            ))
        
        return packages
    except json.JSONDecodeError:
        return []