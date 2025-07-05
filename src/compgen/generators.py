import subprocess
from typing import List, Optional

from .models import CompletionPackage, GeneratedCompletion, CompletionType


def generate_completions(
    packages: List[CompletionPackage],
) -> List[GeneratedCompletion]:
    """Generate shell completions for all packages."""
    completions = []

    for package in packages:
        completion = generate_completion(package)
        if completion:
            completions.append(completion)

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


def generate_click_bash_completion(command: str) -> Optional[str]:
    """Generate bash completion script for a click command."""
    try:
        # Use click's built-in completion generation
        env_var = f"_{command.upper().replace('-', '_')}_COMPLETE"

        result = subprocess.run(
            [command],
            env={**dict(subprocess.os.environ), env_var: "bash_source"},
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            # Generate eval statement as fallback
            return f'eval "$({env_var}=bash_source {command})"'

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        # Generate eval statement as fallback
        env_var = f"_{command.upper().replace('-', '_')}_COMPLETE"
        return f'eval "$({env_var}=bash_source {command})"'


def generate_click_zsh_completion(command: str) -> Optional[str]:
    """Generate zsh completion script for a click command."""
    try:
        # Use click's built-in completion generation for zsh
        env_var = f"_{command.upper().replace('-', '_')}_COMPLETE"

        result = subprocess.run(
            [command],
            env={**dict(subprocess.os.environ), env_var: "zsh_source"},
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            # Generate eval statement as fallback
            return f'eval "$({env_var}=zsh_source {command})"'

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        # Generate eval statement as fallback
        env_var = f"_{command.upper().replace('-', '_')}_COMPLETE"
        return f'eval "$({env_var}=zsh_source {command})"'


def generate_argcomplete_bash_completion(command: str) -> Optional[str]:
    """Generate bash completion script for an argcomplete command."""
    try:
        # Use argcomplete's register-python-argcomplete
        result = subprocess.run(
            ["register-python-argcomplete", command],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            # Generate eval statement as fallback
            return f'eval "$(register-python-argcomplete {command})"'

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        # Generate eval statement as fallback
        return f'eval "$(register-python-argcomplete {command})"'
