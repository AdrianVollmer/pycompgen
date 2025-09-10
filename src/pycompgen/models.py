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
    command: str
    shell: Shell
