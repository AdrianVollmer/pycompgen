import os
from pathlib import Path
import shutil
import subprocess
from typing import List, Optional, Dict

from .models import CompletionPackage, GeneratedCompletion, CompletionType, Shell
from .logger import get_logger

# Global error collector for summarizing errors at the end
_completion_errors: List[str] = []

# Hardcoded completion generators mapping command to completion generation command
HARDCODED_COMPLETION_GENERATORS = {
    "uv": {
        Shell.BASH: ["uv", "generate-shell-completion", "bash"],
        Shell.ZSH: ["uv", "generate-shell-completion", "zsh"],
    },
    "uvx": {
        Shell.BASH: ["uvx", "--generate-shell-completion", "bash"],
        Shell.ZSH: ["uvx", "--generate-shell-completion", "zsh"],
    },
}

logger = get_logger()


def generate_completions(
    packages: List[CompletionPackage], shell: Shell
) -> List[GeneratedCompletion]:
    """Generate shell completions for all packages."""
    completions = []
    _completion_errors.clear()  # Reset error list

    for package in packages:
        package_completions = generate_completion(package, shell)
        completions.extend(package_completions)

    hardcoded_completions = generate_hardcoded_completion(shell)
    completions.extend(hardcoded_completions)

    # Log summary of errors if any occurred
    if _completion_errors:
        logger.info(
            f"Completion generation failed for {len(_completion_errors)} commands."
        )

    return completions


def generate_completion(
    package: CompletionPackage, shell: Shell
) -> List[GeneratedCompletion]:
    """Generate completions for a single package (multiple shells)."""
    completions = []

    if package.completion_type == CompletionType.CLICK:
        completions.extend(generate_click_completion(package, shell))
    elif package.completion_type == CompletionType.ARGCOMPLETE:
        completions.extend(generate_argcomplete_completion(package, shell))

    return completions


def generate_click_completion(
    package: CompletionPackage,
    shell: Shell,
) -> List[GeneratedCompletion]:
    """Generate click completion scripts for a shell."""
    completions = []

    # Generate shell completions
    parts = []
    for command in package.commands:
        completion = generate_click_shell_completion(command, shell=shell)
        if completion:
            parts.append(f"# Completion for {command}\n{completion}")

    if parts:
        content = "\n".join(parts)
        completions.append(
            GeneratedCompletion(
                package_name=package.package.name,
                completion_type=CompletionType.CLICK,
                content=content,
                commands=package.commands,
                shell=shell,
            )
        )

    return completions


def generate_argcomplete_completion(
    package: CompletionPackage, shell: Shell
) -> List[GeneratedCompletion]:
    """Generate argcomplete completion scripts for bash and zsh (content is identical)."""
    completion_parts = []

    for command in package.commands:
        bash_completion = generate_argcomplete_bash_completion(command, package)
        if bash_completion:
            completion_parts.append(f"# Completion for {command}\n{bash_completion}")

    if not completion_parts:
        return []

    # Combine all completions
    content = "\n".join(completion_parts)

    # Generate for either bash or zsh since argcomplete works with both
    return [
        GeneratedCompletion(
            package_name=package.package.name,
            completion_type=CompletionType.ARGCOMPLETE,
            content=content,
            commands=package.commands,
            shell=shell,
        ),
    ]


def generate_hardcoded_completion(shell: Shell) -> List[GeneratedCompletion]:
    """Generate hardcoded completion scripts for a shell."""
    completions = []

    # Generate completions
    for name, shell_specific_commands in HARDCODED_COMPLETION_GENERATORS.items():
        command = shell_specific_commands[shell]

        if not command:
            continue

        base_command = command[0]

        # Check if command is in $HOME, otherwise shell completions should be
        # handled system-wide
        path = shutil.which(base_command)
        home = Path(os.environ.get("HOME", "/"))

        if not (path and Path(path).is_relative_to(home)):
            continue

        content = _run_completion_command(command)

        if content:
            completions.append(
                GeneratedCompletion(
                    package_name=name,
                    completion_type=CompletionType.HARDCODED,
                    content=content,
                    commands=[base_command],
                    shell=shell,
                )
            )

    return completions


def _run_completion_command(
    command: List[str],
    env: Optional[Dict[str, str]] = None,
    timeout: int = 3,
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


def generate_click_shell_completion(command: str, shell: Shell) -> Optional[str]:
    """Generate shell completion script for a click command."""
    env_var = f"_{command.upper().replace('-', '_')}_COMPLETE"

    shell_source = f"{shell.value}_source"
    env = {**os.environ, env_var: shell_source}
    logger.debug(f"Generating completions: {env_var}={shell_source} {command}")
    return _run_completion_command([command], env=env)


def generate_argcomplete_bash_completion(
    command: str, package: CompletionPackage
) -> Optional[str]:
    """Generate bash completion script for an argcomplete command."""
    cmd = str(package.package.path / "bin" / "register-python-argcomplete")
    return _run_completion_command([cmd, command])


def get_completion_errors() -> List[str]:
    """Get list of commands that failed during completion generation."""
    return _completion_errors.copy()
