import os
from pathlib import Path
from typing import List, Optional

from .models import GeneratedCompletion


def get_cache_dir() -> Path:
    """Get the cache directory for completions."""
    # Use XDG_CACHE_HOME if set, otherwise use ~/.cache
    cache_home = os.environ.get("XDG_CACHE_HOME")
    if cache_home:
        cache_dir = Path(cache_home) / "compgen"
    else:
        cache_dir = Path.home() / ".cache" / "compgen"
    
    # Create directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def save_completions(completions: List[GeneratedCompletion], cache_dir: Path, force: bool = False) -> None:
    """Save completions to cache directory."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    for completion in completions:
        save_completion(completion, cache_dir, force)


def save_completion(completion: GeneratedCompletion, cache_dir: Path, force: bool = False) -> None:
    """Save a single completion to cache."""
    # Create filename based on package name
    filename = f"{completion.package_name}.sh"
    filepath = cache_dir / filename
    
    # Check if file exists and force is not set
    if filepath.exists() and not force:
        # Only update if content is different
        try:
            existing_content = filepath.read_text()
            if existing_content == completion.content:
                return  # No changes needed
        except OSError:
            pass  # File might be corrupted, overwrite it
    
    # Write the completion content
    try:
        filepath.write_text(completion.content)
    except OSError as e:
        raise RuntimeError(f"Failed to write completion file {filepath}: {e}")


def get_completion_files(cache_dir: Path) -> List[Path]:
    """Get all completion files in the cache directory."""
    if not cache_dir.exists():
        return []
    
    return [f for f in cache_dir.glob("*.sh") if f.is_file()]


def clean_cache(cache_dir: Path, keep_packages: List[str]) -> None:
    """Clean cache directory, removing completions for packages not in keep_packages."""
    if not cache_dir.exists():
        return
    
    keep_files = {f"{package}.sh" for package in keep_packages}
    
    for filepath in cache_dir.glob("*.sh"):
        if filepath.name not in keep_files:
            try:
                filepath.unlink()
            except OSError:
                pass  # Ignore errors when removing files


def generate_source_script(cache_dir: Path) -> str:
    """Generate a script that sources all completion files."""
    completion_files = get_completion_files(cache_dir)
    
    if not completion_files:
        return "# No completions found"
    
    script_lines = ["# Auto-generated completion script"]
    script_lines.append("# Source this file in your shell configuration (.zshrc, .bashrc)")
    script_lines.append("")
    
    for filepath in sorted(completion_files):
        script_lines.append(f"# Completions from {filepath.stem}")
        script_lines.append(f"source {filepath}")
        script_lines.append("")
    
    return "\n".join(script_lines)


def save_source_script(cache_dir: Path) -> Path:
    """Save the source script to cache directory."""
    script_content = generate_source_script(cache_dir)
    script_path = cache_dir / "completions.sh"
    
    try:
        script_path.write_text(script_content)
    except OSError as e:
        raise RuntimeError(f"Failed to write source script {script_path}: {e}")
    
    return script_path