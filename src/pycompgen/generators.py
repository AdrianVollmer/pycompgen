import os
import subprocess
from typing import List, Optional, Dict, Literal

from .models import CompletionPackage, GeneratedCompletion, CompletionType, Shell
from .logger import get_logger

# Global error collector for summarizing errors at the end
_completion_errors: List[str] = []

# Hardcoded completion generators mapping command to completion generation command
HARDCODED_COMPLETION_GENERATORS = {
    "uv": ["uv", "generate-shell-completion"],
    "uvx": ["uvx", "--generate-shell-completion"],
    "pipx": ["pipx", "completions"],
}

logger = get_logger()


def generate_completions(
    packages: List[CompletionPackage],
) -> List[GeneratedCompletion]:
    """Generate shell completions for all packages."""
    completions = []
    _completion_errors.clear()  # Reset error list

    for package in packages:
        package_completions = generate_completion(package)
        completions.extend(package_completions)

    # Log summary of errors if any occurred
    if _completion_errors:
        logger.warning(
            f"Completion generation failed for {len(_completion_errors)} commands."
        )

    return completions


def generate_completion(package: CompletionPackage) -> List[GeneratedCompletion]:
    """Generate completions for a single package (multiple shells)."""
    completions = []

    if package.completion_type == CompletionType.CLICK:
        completions.extend(generate_click_completion(package))
    elif package.completion_type == CompletionType.ARGCOMPLETE:
        completions.extend(generate_argcomplete_completion(package))
    elif package.completion_type == CompletionType.HARDCODED:
        completions.extend(generate_hardcoded_completion(package))

    return completions


def generate_click_completion(
    package: CompletionPackage,
) -> List[GeneratedCompletion]:
    """Generate click completion scripts for multiple shells."""
    completions = []

    # Generate bash completions
    bash_parts = []
    for command in package.commands:
        bash_completion = generate_click_shell_completion(command, shell="bash")
        if bash_completion:
            bash_parts.append(f"# Completion for {command}\n{bash_completion}")

    if bash_parts:
        bash_content = "\n".join(bash_parts)
        completions.append(
            GeneratedCompletion(
                package_name=package.package.name,
                completion_type=CompletionType.CLICK,
                content=bash_content,
                commands=package.commands,
                shell=Shell.BASH,
            )
        )

    # Generate zsh completions
    zsh_parts = []
    for command in package.commands:
        zsh_completion = generate_click_shell_completion(command, shell="zsh")
        if zsh_completion:
            zsh_parts.append(f"# Completion for {command}\n{zsh_completion}")

    if zsh_parts:
        zsh_content = "\n".join(zsh_parts)
        completions.append(
            GeneratedCompletion(
                package_name=package.package.name,
                completion_type=CompletionType.CLICK,
                content=zsh_content,
                commands=package.commands,
                shell=Shell.ZSH,
            )
        )

    return completions


def generate_argcomplete_completion(
    package: CompletionPackage,
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

    # Generate for both bash and zsh since argcomplete works with both
    return [
        GeneratedCompletion(
            package_name=package.package.name,
            completion_type=CompletionType.ARGCOMPLETE,
            content=content,
            commands=package.commands,
            shell=Shell.BASH,
        ),
        GeneratedCompletion(
            package_name=package.package.name,
            completion_type=CompletionType.ARGCOMPLETE,
            content=content,
            commands=package.commands,
            shell=Shell.ZSH,
        ),
    ]


def generate_hardcoded_completion(
    package: CompletionPackage,
) -> List[GeneratedCompletion]:
    """Generate hardcoded completion scripts for multiple shells."""
    completions = []

    # Generate bash completions
    bash_parts = []
    for command in package.commands:
        bash_completion = generate_hardcoded_shell_completion(command, shell="bash")
        if bash_completion:
            bash_parts.append(f"# Completion for {command}\n{bash_completion}")

    if bash_parts:
        bash_content = "\n".join(bash_parts)
        completions.append(
            GeneratedCompletion(
                package_name=package.package.name,
                completion_type=CompletionType.HARDCODED,
                content=bash_content,
                commands=package.commands,
                shell=Shell.BASH,
            )
        )

    # Generate zsh completions
    zsh_parts = []
    for command in package.commands:
        zsh_completion = generate_hardcoded_shell_completion(command, shell="zsh")
        if zsh_completion:
            zsh_parts.append(f"# Completion for {command}\n{zsh_completion}")

    if zsh_parts:
        zsh_content = "\n".join(zsh_parts)
        completions.append(
            GeneratedCompletion(
                package_name=package.package.name,
                completion_type=CompletionType.HARDCODED,
                content=zsh_content,
                commands=package.commands,
                shell=Shell.ZSH,
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


def generate_click_shell_completion(
    command: str, shell: Literal["bash", "zsh"]
) -> Optional[str]:
    """Generate shell completion script for a click command."""
    env_var = f"_{command.upper().replace('-', '_')}_COMPLETE"

    assert shell in ["bash", "zsh"]
    shell_source = f"{shell}_source"
    env = {**os.environ, env_var: shell_source}
    logger.debug(f"Generating completions: {env_var}={shell_source} {command}")
    return _run_completion_command([command], env=env)


def generate_argcomplete_bash_completion(
    command: str, package: CompletionPackage
) -> Optional[str]:
    """Generate bash completion script for an argcomplete command."""
    cmd = str(package.package.path / "bin" / "register-python-argcomplete")
    return _run_completion_command([cmd, command])


def generate_hardcoded_shell_completion(
    command: str, shell: Literal["bash", "zsh"]
) -> Optional[str]:
    """Generate shell completion script for a hardcoded command."""
    if command not in HARDCODED_COMPLETION_GENERATORS:
        return None

    base_command = HARDCODED_COMPLETION_GENERATORS[command]
    completion_command = base_command + [shell]

    logger.debug(f"Generating hardcoded completions: {' '.join(completion_command)}")
    return _run_completion_command(completion_command)


def get_completion_errors() -> List[str]:
    """Get list of commands that failed during completion generation."""
    return _completion_errors.copy()
