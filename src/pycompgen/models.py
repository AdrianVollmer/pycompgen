from dataclasses import dataclass
from enum import Enum
from pathlib import Path
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

    @property
    def package_path(self) -> Optional[Path]:
        try:
            package_path: Path = list(
                self.path.rglob("lib/python*/site-packages/" + self.name)
            )[0]
            return package_path
        except IndexError:
            return None


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
