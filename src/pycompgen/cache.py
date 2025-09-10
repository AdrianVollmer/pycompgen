import os
from pathlib import Path
from typing import List

from .models import GeneratedCompletion, Shell
from .logger import get_logger


def get_cache_dir() -> Path:
    """Get the base cache directory for completions."""
    # Use XDG_CACHE_HOME if set, otherwise use ~/.cache
    cache_home = os.environ.get("XDG_CACHE_HOME")
    if cache_home:
        cache_dir = Path(cache_home)
    else:
        cache_dir = Path.home() / ".cache"

    return cache_dir


def get_shell_cache_dir(shell: Shell) -> Path:
    """Get the shell-specific cache directory for completions."""
    cache_home = get_cache_dir()

    if shell == Shell.BASH:
        shell_dir = cache_home / "pycompgen" / "bash"
    elif shell == Shell.ZSH:
        shell_dir = cache_home / "pycompgen" / "zsh"
    elif shell == Shell.FISH:
        shell_dir = cache_home / "fish" / "generated_completions"
    else:
        raise ValueError(f"Unsupported shell: {shell}")

    # Create directory if it doesn't exist
    shell_dir.mkdir(parents=True, exist_ok=True)
    return shell_dir


def save_completions(
    completions: List[GeneratedCompletion], base_cache_dir: Path, force: bool = False
) -> None:
    """Save completions to shell-specific cache directories."""
    logger = get_logger()

    for completion in completions:
        save_completion(completion, base_cache_dir, force)

    logger.info(f"Saved {len(completions)} completion files")


def save_completion(
    completion: GeneratedCompletion, base_cache_dir: Path, force: bool = False
) -> None:
    """Save a single completion to shell-specific cache directory."""
    # Create shell-specific directory under the provided base cache directory
    if completion.shell == Shell.BASH:
        shell_dir = base_cache_dir / "pycompgen" / "bash"
        extension = ".sh"
    elif completion.shell == Shell.ZSH:
        shell_dir = base_cache_dir / "pycompgen" / "zsh"
        extension = ".zsh"
    elif completion.shell == Shell.FISH:
        shell_dir = base_cache_dir / "fish" / "generated_completions"
        extension = ".fish"
    else:
        raise ValueError(f"Unsupported shell: {completion.shell}")

    # Create directory if it doesn't exist
    shell_dir.mkdir(parents=True, exist_ok=True)

    # Create filename
    filename = f"{completion.command}{extension}"
    filepath = shell_dir / filename

    # Check if file exists and force is not set
    if filepath.exists() and not force:
        # Don't overwrite existing files unless forced
        return

    # Write the completion content
    try:
        filepath.write_text(completion.content)
    except OSError as e:
        raise RuntimeError(f"Failed to write completion file {filepath}: {e}")


def get_completion_files(shell: Shell) -> List[Path]:
    """Get all completion files for a specific shell."""
    shell_dir = get_shell_cache_dir(shell)

    if not shell_dir.exists():
        return []

    if shell == Shell.BASH:
        pattern = "*.sh"
    elif shell == Shell.ZSH:
        pattern = "*.zsh"
    elif shell == Shell.FISH:
        pattern = "*.fish"
    else:
        raise ValueError(f"Unsupported shell: {shell}")

    return [f for f in shell_dir.glob(pattern) if f.is_file()]


def read_completion_files(shell: Shell) -> str:
    result = ""
    for f in get_completion_files(shell):
        result += open(f, "r").read() + "\n\n"

    return result
