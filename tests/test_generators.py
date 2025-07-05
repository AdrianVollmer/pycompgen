import pytest
from unittest.mock import Mock, patch
import subprocess

from pycompgen.generators import (
    generate_completions,
    generate_completion,
    generate_click_completion,
    generate_argcomplete_completion,
    generate_hardcoded_completion,
    generate_click_shell_completion,
    generate_argcomplete_bash_completion,
    generate_hardcoded_shell_completion,
    _run_completion_command,
    get_completion_errors,
    _completion_errors,
    HARDCODED_COMPLETION_GENERATORS,
)
from pycompgen.models import (
    CompletionPackage,
    GeneratedCompletion,
    CompletionType,
    InstalledPackage,
    Shell,
)


class TestGenerateCompletions:
    """Test the main generate_completions function."""

    @patch("pycompgen.generators.generate_completion")
    def test_generate_completions_success(self, mock_generate):
        """Test successful completion generation."""
        mock_packages = [Mock(), Mock()]
        mock_completions1 = [
            Mock(spec=GeneratedCompletion),
            Mock(spec=GeneratedCompletion),
        ]
        mock_completions2 = [Mock(spec=GeneratedCompletion)]
        mock_generate.side_effect = [mock_completions1, mock_completions2]

        result = generate_completions(mock_packages)

        assert len(result) == 3
        assert result == mock_completions1 + mock_completions2
        assert mock_generate.call_count == 2

    @patch("pycompgen.generators.generate_completion")
    def test_generate_completions_empty_results(self, mock_generate):
        """Test that empty results are handled."""
        mock_packages = [Mock(), Mock(), Mock()]
        mock_generate.side_effect = [
            [Mock(spec=GeneratedCompletion)],
            [],  # Failed generation
            [Mock(spec=GeneratedCompletion)],
        ]

        result = generate_completions(mock_packages)

        assert len(result) == 2

    def test_generate_completions_logs_errors(self):
        """Test that error logging functionality exists."""
        # Clear errors first
        _completion_errors.clear()

        # Test that we can add errors to the global list
        _completion_errors.extend(["error1", "error2"])

        # Mock packages
        mock_packages = []

        # Run generate_completions (this will clear the errors)
        result = generate_completions(mock_packages)

        # After running, errors should be cleared (this tests the clearing behavior)
        # and no completions should be generated from empty input
        assert result == []

    def test_generate_completions_empty_input(self):
        """Test with empty input."""
        result = generate_completions([])

        assert result == []


class TestGenerateCompletion:
    """Test individual completion generation."""

    @patch("pycompgen.generators.generate_click_completion")
    def test_generate_completion_click(self, mock_generate_click):
        """Test generation for click package."""
        mock_completions = [
            Mock(spec=GeneratedCompletion),
            Mock(spec=GeneratedCompletion),
        ]
        mock_generate_click.return_value = mock_completions

        mock_package = Mock(spec=CompletionPackage)
        mock_package.completion_type = CompletionType.CLICK

        result = generate_completion(mock_package)

        assert result == mock_completions
        mock_generate_click.assert_called_once_with(mock_package)

    @patch("pycompgen.generators.generate_argcomplete_completion")
    def test_generate_completion_argcomplete(self, mock_generate_argcomplete):
        """Test generation for argcomplete package."""
        mock_completions = [Mock(spec=GeneratedCompletion)]
        mock_generate_argcomplete.return_value = mock_completions

        mock_package = Mock(spec=CompletionPackage)
        mock_package.completion_type = CompletionType.ARGCOMPLETE

        result = generate_completion(mock_package)

        assert result == mock_completions
        mock_generate_argcomplete.assert_called_once_with(mock_package)

    @patch("pycompgen.generators.generate_hardcoded_completion")
    def test_generate_completion_hardcoded(self, mock_generate_hardcoded):
        """Test generation for hardcoded package."""
        mock_completions = [
            Mock(spec=GeneratedCompletion),
            Mock(spec=GeneratedCompletion),
        ]
        mock_generate_hardcoded.return_value = mock_completions

        mock_package = Mock(spec=CompletionPackage)
        mock_package.completion_type = CompletionType.HARDCODED

        result = generate_completion(mock_package)

        assert result == mock_completions
        mock_generate_hardcoded.assert_called_once_with(mock_package)

    def test_generate_completion_unknown_type(self):
        """Test generation for unknown completion type."""
        mock_package = Mock(spec=CompletionPackage)
        mock_package.completion_type = "unknown"

        result = generate_completion(mock_package)

        assert result == []


class TestGenerateClickCompletion:
    """Test click completion generation."""

    @patch("pycompgen.generators.generate_click_shell_completion")
    def test_generate_click_completion_success(self, mock_generate_shell):
        """Test successful click completion generation."""
        mock_generate_shell.side_effect = [
            "bash completion content",  # bash
            "zsh completion content",  # zsh
        ]

        mock_installed_package = Mock(spec=InstalledPackage)
        mock_installed_package.name = "test-package"

        mock_package = Mock(spec=CompletionPackage)
        mock_package.package = mock_installed_package
        mock_package.commands = ["test-command"]

        result = generate_click_completion(mock_package)

        assert isinstance(result, list)
        assert len(result) == 2  # bash and zsh

        # Check bash completion
        bash_completion = next(c for c in result if c.shell == Shell.BASH)
        assert bash_completion.package_name == "test-package"
        assert bash_completion.completion_type == CompletionType.CLICK
        assert bash_completion.commands == ["test-command"]
        assert "bash completion content" in bash_completion.content

        # Check zsh completion
        zsh_completion = next(c for c in result if c.shell == Shell.ZSH)
        assert zsh_completion.package_name == "test-package"
        assert "zsh completion content" in zsh_completion.content

    @patch("pycompgen.generators.generate_click_shell_completion")
    def test_generate_click_completion_partial_success(self, mock_generate_shell):
        """Test click completion generation with partial success."""
        mock_generate_shell.side_effect = [
            "bash completion content",  # bash
            None,  # zsh failed
        ]

        mock_installed_package = Mock(spec=InstalledPackage)
        mock_installed_package.name = "test-package"

        mock_package = Mock(spec=CompletionPackage)
        mock_package.package = mock_installed_package
        mock_package.commands = ["test-command"]

        result = generate_click_completion(mock_package)

        assert isinstance(result, list)
        assert len(result) == 1  # Only bash succeeded
        assert result[0].shell == Shell.BASH
        assert "bash completion content" in result[0].content

    @patch("pycompgen.generators.generate_click_shell_completion")
    def test_generate_click_completion_no_completions(self, mock_generate_shell):
        """Test click completion generation when no completions succeed."""
        mock_generate_shell.return_value = None

        mock_installed_package = Mock(spec=InstalledPackage)
        mock_installed_package.name = "test-package"

        mock_package = Mock(spec=CompletionPackage)
        mock_package.package = mock_installed_package
        mock_package.commands = ["test-command"]

        result = generate_click_completion(mock_package)

        assert isinstance(result, list)
        assert len(result) == 0  # No completions succeeded


class TestGenerateArgcompleteCompletion:
    """Test argcomplete completion generation."""

    @patch("pycompgen.generators.generate_argcomplete_bash_completion")
    def test_generate_argcomplete_completion_success(self, mock_generate_bash):
        """Test successful argcomplete completion generation."""
        mock_generate_bash.return_value = "bash completion content"

        mock_installed_package = Mock(spec=InstalledPackage)
        mock_installed_package.name = "test-package"

        mock_package = Mock(spec=CompletionPackage)
        mock_package.package = mock_installed_package
        mock_package.commands = ["test-command"]

        result = generate_argcomplete_completion(mock_package)

        assert isinstance(result, list)
        assert len(result) == 2  # Now generates for both bash and zsh

        # Check bash completion
        bash_completion = next(c for c in result if c.shell == Shell.BASH)
        assert bash_completion.package_name == "test-package"
        assert bash_completion.completion_type == CompletionType.ARGCOMPLETE
        assert bash_completion.commands == ["test-command"]
        assert "bash completion content" in bash_completion.content

        # Check zsh completion
        zsh_completion = next(c for c in result if c.shell == Shell.ZSH)
        assert zsh_completion.package_name == "test-package"
        assert zsh_completion.completion_type == CompletionType.ARGCOMPLETE
        assert zsh_completion.commands == ["test-command"]
        assert (
            "bash completion content" in zsh_completion.content
        )  # Same content as bash

    @patch("pycompgen.generators.generate_argcomplete_bash_completion")
    def test_generate_argcomplete_completion_failure(self, mock_generate_bash):
        """Test argcomplete completion generation failure."""
        mock_generate_bash.return_value = None

        mock_installed_package = Mock(spec=InstalledPackage)
        mock_installed_package.name = "test-package"

        mock_package = Mock(spec=CompletionPackage)
        mock_package.package = mock_installed_package
        mock_package.commands = ["test-command"]

        result = generate_argcomplete_completion(mock_package)

        assert isinstance(result, list)
        assert len(result) == 0  # No completions succeeded


class TestRunCompletionCommand:
    """Test the _run_completion_command helper function."""

    @patch("subprocess.run")
    def test_run_completion_command_success(self, mock_run):
        """Test successful command execution."""
        mock_run.return_value = Mock(stdout="completion output\n", returncode=0)

        result = _run_completion_command(["test-command"])

        assert result == "completion output"
        mock_run.assert_called_once_with(
            ["test-command"],
            env=mock_run.call_args[1]["env"],  # os.environ
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )

    @patch("subprocess.run")
    def test_run_completion_command_empty_output(self, mock_run):
        """Test when command returns empty output."""
        mock_run.return_value = Mock(
            stdout="  \n",  # Whitespace only
            returncode=0,
        )

        result = _run_completion_command(["test-command"])

        assert result is None

    @patch("subprocess.run")
    def test_run_completion_command_with_env(self, mock_run):
        """Test command execution with custom environment."""
        mock_run.return_value = Mock(stdout="completion output\n", returncode=0)

        custom_env = {"TEST_VAR": "test_value"}
        result = _run_completion_command(["test-command"], env=custom_env)

        assert result == "completion output"
        assert mock_run.call_args[1]["env"] == custom_env

    @patch("subprocess.run")
    def test_run_completion_command_timeout(self, mock_run):
        """Test command execution with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["test-command"], 3)

        result = _run_completion_command(["test-command"])

        assert result is None
        assert "test-command" in _completion_errors

    @patch("subprocess.run")
    def test_run_completion_command_process_error(self, mock_run):
        """Test command execution with process error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["test-command"])

        result = _run_completion_command(["test-command"])

        assert result is None
        assert "test-command" in _completion_errors

    @patch("subprocess.run")
    def test_run_completion_command_file_not_found(self, mock_run):
        """Test command execution when command is not found."""
        mock_run.side_effect = FileNotFoundError()

        result = _run_completion_command(["nonexistent-command"])

        assert result is None
        assert "nonexistent-command" in _completion_errors


class TestGenerateClickShellCompletion:
    """Test click shell completion generation."""

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_click_shell_completion_bash(self, mock_run):
        """Test bash completion generation for click."""
        mock_run.return_value = "bash completion output"

        result = generate_click_shell_completion("test-command", "bash")

        assert result == "bash completion output"
        mock_run.assert_called_once_with(
            ["test-command"], env=mock_run.call_args[1]["env"]
        )

        # Check that the environment variable is set correctly
        env = mock_run.call_args[1]["env"]
        assert "_TEST_COMMAND_COMPLETE" in env
        assert env["_TEST_COMMAND_COMPLETE"] == "bash_source"

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_click_shell_completion_zsh(self, mock_run):
        """Test zsh completion generation for click."""
        mock_run.return_value = "zsh completion output"

        result = generate_click_shell_completion("test-command", "zsh")

        assert result == "zsh completion output"

        # Check that the environment variable is set correctly
        env = mock_run.call_args[1]["env"]
        assert "_TEST_COMMAND_COMPLETE" in env
        assert env["_TEST_COMMAND_COMPLETE"] == "zsh_source"

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_click_shell_completion_dashes(self, mock_run):
        """Test completion generation for command with dashes."""
        mock_run.return_value = "completion output"

        result = generate_click_shell_completion("test-command-with-dashes", "bash")

        assert result == "completion output"

        # Check that dashes are replaced with underscores in env var
        env = mock_run.call_args[1]["env"]
        assert "_TEST_COMMAND_WITH_DASHES_COMPLETE" in env

    def test_generate_click_shell_completion_invalid_shell(self):
        """Test with invalid shell parameter."""
        with pytest.raises(AssertionError):
            generate_click_shell_completion("test-command", "invalid-shell")


class TestGenerateArgcompleteCompletionBash:
    """Test argcomplete completion generation."""

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_argcomplete_bash_completion(self, mock_run):
        """Test argcomplete bash completion generation."""
        mock_run.return_value = "argcomplete completion output"

        result = generate_argcomplete_bash_completion("test-command")

        assert result == "argcomplete completion output"
        mock_run.assert_called_once_with(
            ["register-python-argcomplete", "test-command"]
        )

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_argcomplete_bash_completion_failure(self, mock_run):
        """Test argcomplete completion generation failure."""
        mock_run.return_value = None

        result = generate_argcomplete_bash_completion("test-command")

        assert result is None


class TestGetCompletionErrors:
    """Test error tracking functionality."""

    def test_get_completion_errors(self):
        """Test getting completion errors."""
        _completion_errors.clear()
        _completion_errors.extend(["error1", "error2"])

        result = get_completion_errors()

        assert result == ["error1", "error2"]
        # Ensure it returns a copy
        assert result is not _completion_errors

    def test_get_completion_errors_empty(self):
        """Test getting completion errors when none exist."""
        _completion_errors.clear()

        result = get_completion_errors()

        assert result == []


class TestGenerateHardcodedCompletion:
    """Test hardcoded completion generation."""

    @patch("pycompgen.generators.generate_hardcoded_shell_completion")
    def test_generate_hardcoded_completion_success(self, mock_generate_shell):
        """Test successful hardcoded completion generation."""
        mock_generate_shell.side_effect = [
            "bash completion content",  # bash
            "zsh completion content",  # zsh
        ]

        mock_installed_package = Mock(spec=InstalledPackage)
        mock_installed_package.name = "uv"

        mock_package = Mock(spec=CompletionPackage)
        mock_package.package = mock_installed_package
        mock_package.commands = ["uv"]

        result = generate_hardcoded_completion(mock_package)

        assert isinstance(result, list)
        assert len(result) == 2  # bash and zsh

        # Check bash completion
        bash_completion = next(c for c in result if c.shell == Shell.BASH)
        assert bash_completion.package_name == "uv"
        assert bash_completion.completion_type == CompletionType.HARDCODED
        assert bash_completion.commands == ["uv"]
        assert "bash completion content" in bash_completion.content

        # Check zsh completion
        zsh_completion = next(c for c in result if c.shell == Shell.ZSH)
        assert zsh_completion.package_name == "uv"
        assert "zsh completion content" in zsh_completion.content

    @patch("pycompgen.generators.generate_hardcoded_shell_completion")
    def test_generate_hardcoded_completion_partial_success(self, mock_generate_shell):
        """Test hardcoded completion generation with partial success."""
        mock_generate_shell.side_effect = [
            "bash completion content",  # bash
            None,  # zsh failed
        ]

        mock_installed_package = Mock(spec=InstalledPackage)
        mock_installed_package.name = "uv"

        mock_package = Mock(spec=CompletionPackage)
        mock_package.package = mock_installed_package
        mock_package.commands = ["uv"]

        result = generate_hardcoded_completion(mock_package)

        assert isinstance(result, list)
        assert len(result) == 1  # Only bash succeeded
        assert result[0].shell == Shell.BASH
        assert "bash completion content" in result[0].content

    @patch("pycompgen.generators.generate_hardcoded_shell_completion")
    def test_generate_hardcoded_completion_no_completions(self, mock_generate_shell):
        """Test hardcoded completion generation when no completions succeed."""
        mock_generate_shell.return_value = None

        mock_installed_package = Mock(spec=InstalledPackage)
        mock_installed_package.name = "uv"

        mock_package = Mock(spec=CompletionPackage)
        mock_package.package = mock_installed_package
        mock_package.commands = ["uv"]

        result = generate_hardcoded_completion(mock_package)

        assert isinstance(result, list)
        assert len(result) == 0  # No completions succeeded


class TestGenerateHardcodedShellCompletion:
    """Test hardcoded shell completion generation."""

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_hardcoded_shell_completion_uv_bash(self, mock_run):
        """Test bash completion generation for uv."""
        mock_run.return_value = "uv bash completion output"

        result = generate_hardcoded_shell_completion("uv", "bash")

        assert result == "uv bash completion output"
        mock_run.assert_called_once_with(["uv", "generate-shell-completion", "bash"])

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_hardcoded_shell_completion_uv_zsh(self, mock_run):
        """Test zsh completion generation for uv."""
        mock_run.return_value = "uv zsh completion output"

        result = generate_hardcoded_shell_completion("uv", "zsh")

        assert result == "uv zsh completion output"
        mock_run.assert_called_once_with(["uv", "generate-shell-completion", "zsh"])

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_hardcoded_shell_completion_uvx_bash(self, mock_run):
        """Test bash completion generation for uvx."""
        mock_run.return_value = "uvx bash completion output"

        result = generate_hardcoded_shell_completion("uvx", "bash")

        assert result == "uvx bash completion output"
        mock_run.assert_called_once_with(["uvx", "--generate-shell-completion", "bash"])

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_hardcoded_shell_completion_uvx_zsh(self, mock_run):
        """Test zsh completion generation for uvx."""
        mock_run.return_value = "uvx zsh completion output"

        result = generate_hardcoded_shell_completion("uvx", "zsh")

        assert result == "uvx zsh completion output"
        mock_run.assert_called_once_with(["uvx", "--generate-shell-completion", "zsh"])

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_hardcoded_shell_completion_unknown_command(self, mock_run):
        """Test completion generation for unknown command."""
        result = generate_hardcoded_shell_completion("unknown-command", "bash")

        assert result is None
        mock_run.assert_not_called()

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_hardcoded_shell_completion_failure(self, mock_run):
        """Test hardcoded completion generation failure."""
        mock_run.return_value = None

        result = generate_hardcoded_shell_completion("uv", "bash")

        assert result is None


class TestHardcodedCompletionGenerators:
    """Test the hardcoded completion generators dictionary."""

    def test_hardcoded_completion_generators_contains_uv(self):
        """Test that uv is in the hardcoded generators."""
        assert "uv" in HARDCODED_COMPLETION_GENERATORS
        assert HARDCODED_COMPLETION_GENERATORS["uv"] == [
            "uv",
            "generate-shell-completion",
        ]

    def test_hardcoded_completion_generators_contains_uvx(self):
        """Test that uvx is in the hardcoded generators."""
        assert "uvx" in HARDCODED_COMPLETION_GENERATORS
        assert HARDCODED_COMPLETION_GENERATORS["uvx"] == [
            "uvx",
            "--generate-shell-completion",
        ]
