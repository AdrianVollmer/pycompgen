import os
import subprocess
from typing import List, Optional, Dict

from .models import CompletionPackage, GeneratedCompletion, CompletionType
from .logger import get_logger

# Global error collector for summarizing errors at the end
_completion_errors: List[str] = []

logger = get_logger()


def generate_completions(
    packages: List[CompletionPackage],
) -> List[GeneratedCompletion]:
    """Generate shell completions for all packages."""
    completions = []
    _completion_errors.clear()  # Reset error list

    for package in packages:
        completion = generate_completion(package)
        if completion:
            completions.append(completion)

    # Log summary of errors if any occurred
    if _completion_errors:
        logger.warning(
            f"Completion generation failed for {len(_completion_errors)} commands:"
        )
        for error in _completion_errors:
            logger.warning(f"  - {error}")

    return completions


def generate_completion(package: CompletionPackage) -> Optional[GeneratedCompletion]:
    """Generate completion for a single package."""
    if package.completion_type == CompletionType.CLICK:
        return generate_click_completion(package)
    elif package.completion_type == CompletionType.ARGCOMPLETE:
        return generate_argcomplete_completion(package)

    return None


def generate_click_completion(
    package: CompletionPackage,
) -> Optional[GeneratedCompletion]:
    """Generate click completion script."""
    completion_parts = []

    for command in package.commands:
        # Generate for both bash and zsh
        bash_completion = generate_click_bash_completion(command)
        zsh_completion = generate_click_zsh_completion(command)

        if bash_completion or zsh_completion:
            command_completion = f"# Completion for {command}\n"
            if bash_completion:
                command_completion += f"# Bash completion\n{bash_completion}\n"
            if zsh_completion:
                command_completion += f"# Zsh completion\n{zsh_completion}\n"
            completion_parts.append(command_completion)

    if not completion_parts:
        return None

    # Combine all completions
    content = "\n".join(completion_parts)

    return GeneratedCompletion(
        package_name=package.package.name,
        completion_type=CompletionType.CLICK,
        content=content,
        commands=package.commands,
    )


def generate_argcomplete_completion(
    package: CompletionPackage,
) -> Optional[GeneratedCompletion]:
    """Generate argcomplete completion script."""
    completion_parts = []

    for command in package.commands:
        bash_completion = generate_argcomplete_bash_completion(command)
        if bash_completion:
            completion_parts.append(f"# Completion for {command}\n{bash_completion}")

    if not completion_parts:
        return None

    # Combine all completions
    content = "\n".join(completion_parts)

    return GeneratedCompletion(
        package_name=package.package.name,
        completion_type=CompletionType.ARGCOMPLETE,
        content=content,
        commands=package.commands,
    )


def _run_completion_command(
    command: List[str], env: Optional[Dict[str, str]] = None, timeout: int = 10
) -> Optional[str]:
    """Run a completion command and return the output or None if failed."""
    try:
        result = subprocess.run(
            command,
            env=env or os.environ,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )

        if result.stdout.strip():
            return result.stdout.strip()
        else:
            return None

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ) as e:
        # Log the error and add to error summary
        command_str = " ".join(command)
        error_msg = f"Command '{command_str}' failed: {type(e).__name__}: {e}"
        logger.debug(error_msg)
        _completion_errors.append(command_str)
        return None


def generate_click_bash_completion(command: str) -> Optional[str]:
    """Generate bash completion script for a click command."""
    env_var = f"_{command.upper().replace('-', '_')}_COMPLETE"
    env = {**os.environ, env_var: "bash_source"}
    return _run_completion_command([command], env=env)


def generate_click_zsh_completion(command: str) -> Optional[str]:
    """Generate zsh completion script for a click command."""
    env_var = f"_{command.upper().replace('-', '_')}_COMPLETE"
    env = {**os.environ, env_var: "zsh_source"}
    return _run_completion_command([command], env=env)


def generate_argcomplete_bash_completion(command: str) -> Optional[str]:
    """Generate bash completion script for an argcomplete command."""
    return _run_completion_command(["register-python-argcomplete", command])


def get_completion_errors() -> List[str]:
    """Get list of commands that failed during completion generation."""
    return _completion_errors.copy()
