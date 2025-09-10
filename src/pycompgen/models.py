from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re
from typing import List, Optional


class PackageManager(Enum):
    UV_TOOL = "uv_tool"
    PIPX = "pipx"


class CompletionType(Enum):
    CLICK = "click"
    ARGCOMPLETE = "argcomplete"
    HARDCODED = "hardcoded"


class Shell(Enum):
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"


@dataclass
class InstalledPackage:
    name: str
    path: Path
    manager: PackageManager
    version: Optional[str] = None
    commands: Optional[List[str]] = None

    def has_dependency(self, dependency: str) -> bool:
        """Check if a dependency is directly imported by the package."""
        try:
            slug = self.name.replace("-", "_")
            package_path: Path = list(
                self.path.rglob(f"lib/python*/site-packages/{slug}-*-info/")
            )[0]
        except IndexError:
            return False

        metadata = open(package_path / "METADATA", "r").read()

        if "\n\n" in metadata:
            metadata = metadata.split("\n\n")[0]

        m = re.search(
            f"^Requires-Dist: {dependency}([^a-z-].+)?$", metadata, re.MULTILINE
        )

        if m:
            return True
        return False


@dataclass
class CompletionPackage:
    package: InstalledPackage
    completion_type: CompletionType
    commands: List[str]


@dataclass
class GeneratedCompletion:
    package_name: str
    completion_type: CompletionType
    content: str
    commands: List[str]
    shell: Shell
