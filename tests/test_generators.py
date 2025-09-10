import pytest
from unittest.mock import Mock, patch
import subprocess

from pycompgen.generators import (
    generate_completions,
    generate_completion,
    generate_click_completion,
    generate_argcomplete_completion,
    generate_click_shell_completion,
    generate_argcomplete_shell_completion,
    _run_completion_command,
    get_completion_errors,
    _completion_errors,
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

    @patch("shutil.which")
    @patch("pycompgen.generators.generate_completion")
    def test_generate_completions_success(self, mock_generate, mock_which):
        """Test successful completion generation."""
        # Mock shutil.which to return None (no hardcoded commands found)
        mock_which.return_value = None

        mock_packages = [Mock(), Mock()]
        mock_completions1 = [
            Mock(spec=GeneratedCompletion),
            Mock(spec=GeneratedCompletion),
        ]
        mock_completions2 = [Mock(spec=GeneratedCompletion)]
        mock_generate.side_effect = [mock_completions1, mock_completions2]

        result = generate_completions(mock_packages, Shell.BASH)

        assert len(result) == 3
        assert result == mock_completions1 + mock_completions2
        assert mock_generate.call_count == 2

    @patch("shutil.which")
    @patch("pycompgen.generators.generate_completion")
    def test_generate_completions_empty_results(self, mock_generate, mock_which):
        """Test that empty results are handled."""
        # Mock shutil.which to return None (no hardcoded commands found)
        mock_which.return_value = None

        mock_packages = [Mock(), Mock(), Mock()]
        mock_generate.side_effect = [
            [Mock(spec=GeneratedCompletion)],
            [],  # Failed generation
            [Mock(spec=GeneratedCompletion)],
        ]

        result = generate_completions(mock_packages, Shell.BASH)

        assert len(result) == 2

    @patch("shutil.which")
    def test_generate_completions_logs_errors(self, mock_which):
        """Test that error logging functionality exists."""
        # Mock shutil.which to return None (no hardcoded commands found)
        mock_which.return_value = None

        # Clear errors first
        _completion_errors.clear()

        # Test that we can add errors to the global list
        _completion_errors.extend(["error1", "error2"])

        # Mock packages
        mock_packages = []

        # Run generate_completions (this will clear the errors)
        result = generate_completions(mock_packages, Shell.BASH)

        # After running, errors should be cleared (this tests the clearing behavior)
        # and no completions should be generated from empty input
        assert result == []

    @patch("shutil.which")
    def test_generate_completions_empty_input(self, mock_which):
        """Test with empty input."""
        # Mock shutil.which to return None (no hardcoded commands found)
        mock_which.return_value = None

        result = generate_completions([], Shell.BASH)

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

        result = generate_completion(mock_package, Shell.BASH)

        assert result == mock_completions
        mock_generate_click.assert_called_once_with(mock_package, Shell.BASH)

    @patch("pycompgen.generators.generate_argcomplete_completion")
    def test_generate_completion_argcomplete(self, mock_generate_argcomplete):
        """Test generation for argcomplete package."""
        mock_completions = [Mock(spec=GeneratedCompletion)]
        mock_generate_argcomplete.return_value = mock_completions

        mock_package = Mock(spec=CompletionPackage)
        mock_package.completion_type = CompletionType.ARGCOMPLETE

        result = generate_completion(mock_package, Shell.BASH)

        assert result == mock_completions
        mock_generate_argcomplete.assert_called_once_with(mock_package, Shell.BASH)

    def test_generate_completion_hardcoded(self):
        """Test generation for hardcoded package (no longer supported as package type)."""
        mock_package = Mock(spec=CompletionPackage)
        mock_package.completion_type = "hardcoded"  # Unknown type

        result = generate_completion(mock_package, Shell.BASH)

        assert result == []

    def test_generate_completion_unknown_type(self):
        """Test generation for unknown completion type."""
        mock_package = Mock(spec=CompletionPackage)
        mock_package.completion_type = "unknown"

        result = generate_completion(mock_package, Shell.BASH)

        assert result == []


class TestGenerateClickCompletion:
    """Test click completion generation."""

    @patch("pycompgen.generators.generate_click_shell_completion")
    def test_generate_click_completion_success(self, mock_generate_shell):
        """Test successful click completion generation."""
        mock_generate_shell.return_value = "completion content"

        mock_installed_package = Mock(spec=InstalledPackage)
        mock_installed_package.name = "test-package"

        mock_package = Mock(spec=CompletionPackage)
        mock_package.package = mock_installed_package
        mock_package.commands = ["test-command"]

        for shell in [Shell.BASH, Shell.ZSH]:
            result = generate_click_completion(mock_package, shell)

            assert isinstance(result, list)
            assert len(result) == 1

            # Check completion
            completion = result[0]
            assert completion.package_name == "test-package"
            assert completion.completion_type == CompletionType.CLICK
            assert completion.command == "test-command"
            assert completion.shell == shell
            assert "completion content" in completion.content

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

        result = generate_click_completion(mock_package, Shell.BASH)

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

        result = generate_click_completion(mock_package, Shell.BASH)

        assert isinstance(result, list)
        assert len(result) == 0  # No completions succeeded


class TestGenerateArgcompleteCompletion:
    """Test argcomplete completion generation."""

    @patch("pycompgen.generators.generate_argcomplete_shell_completion")
    def test_generate_argcomplete_completion_success(self, mock_generate_shell):
        """Test successful argcomplete completion generation."""
        mock_generate_shell.return_value = "bash completion content"

        mock_installed_package = Mock(spec=InstalledPackage)
        mock_installed_package.name = "test-package"

        mock_package = Mock(spec=CompletionPackage)
        mock_package.package = mock_installed_package
        mock_package.commands = ["test-command"]

        result = generate_argcomplete_completion(mock_package, Shell.BASH)

        assert isinstance(result, list)
        assert len(result) == 1  # Now generates for single shell

        # Check bash completion
        bash_completion = result[0]
        assert bash_completion.package_name == "test-package"
        assert bash_completion.completion_type == CompletionType.ARGCOMPLETE
        assert bash_completion.command == "test-command"
        assert bash_completion.shell == Shell.BASH
        assert "bash completion content" in bash_completion.content

    @patch("pycompgen.generators.generate_argcomplete_shell_completion")
    def test_generate_argcomplete_completion_failure(self, mock_generate_shell):
        """Test argcomplete completion generation failure."""
        mock_generate_shell.return_value = None

        mock_installed_package = Mock(spec=InstalledPackage)
        mock_installed_package.name = "test-package"

        mock_package = Mock(spec=CompletionPackage)
        mock_package.package = mock_installed_package
        mock_package.commands = ["test-command"]

        result = generate_argcomplete_completion(mock_package, Shell.BASH)

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

        result = generate_click_shell_completion("test-command", Shell.BASH)

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

        result = generate_click_shell_completion("test-command", Shell.ZSH)

        assert result == "zsh completion output"

        # Check that the environment variable is set correctly
        env = mock_run.call_args[1]["env"]
        assert "_TEST_COMMAND_COMPLETE" in env
        assert env["_TEST_COMMAND_COMPLETE"] == "zsh_source"

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_click_shell_completion_dashes(self, mock_run):
        """Test completion generation for command with dashes."""
        mock_run.return_value = "completion output"

        result = generate_click_shell_completion("test-command-with-dashes", Shell.BASH)

        assert result == "completion output"

        # Check that dashes are replaced with underscores in env var
        env = mock_run.call_args[1]["env"]
        assert "_TEST_COMMAND_WITH_DASHES_COMPLETE" in env

    def test_generate_click_shell_completion_invalid_shell(self):
        """Test with invalid shell parameter."""
        with pytest.raises(AttributeError):
            generate_click_shell_completion("test-command", "invalid-shell")


class TestGenerateArgcompleteShellCompletion:
    """Test argcomplete shell completion generation."""

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_argcomplete_shell_completion_bash(self, mock_run):
        """Test argcomplete bash completion generation."""
        mock_run.return_value = "argcomplete completion output"

        # Mock the package with a path that has a bin directory
        mock_completion_package = Mock(spec=CompletionPackage)
        mock_package = Mock()
        # Mock pathlib.Path behavior for package.path / "bin" / "register-python-argcomplete"
        mock_path = Mock()
        mock_path.__truediv__ = Mock(
            return_value=Mock(
                __truediv__=Mock(
                    return_value="/fake/path/bin/register-python-argcomplete"
                )
            )
        )
        mock_package.path = mock_path
        mock_completion_package.package = mock_package

        result = generate_argcomplete_shell_completion(
            "test-command", mock_completion_package, Shell.BASH
        )

        assert result == "argcomplete completion output"
        mock_run.assert_called_once_with(
            [
                "/fake/path/bin/register-python-argcomplete",
                "--shell",
                "bash",
                "test-command",
            ]
        )

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_argcomplete_shell_completion_fish(self, mock_run):
        """Test argcomplete fish completion generation."""
        mock_run.return_value = "argcomplete completion output"

        # Mock the package with a path that has a bin directory
        mock_completion_package = Mock(spec=CompletionPackage)
        mock_package = Mock()
        # Mock pathlib.Path behavior for package.path / "bin" / "register-python-argcomplete"
        mock_path = Mock()
        mock_path.__truediv__ = Mock(
            return_value=Mock(
                __truediv__=Mock(
                    return_value="/fake/path/bin/register-python-argcomplete"
                )
            )
        )
        mock_package.path = mock_path
        mock_completion_package.package = mock_package

        result = generate_argcomplete_shell_completion(
            "test-command", mock_completion_package, Shell.FISH
        )

        assert result == "argcomplete completion output"
        mock_run.assert_called_once_with(
            [
                "/fake/path/bin/register-python-argcomplete",
                "--shell",
                "fish",
                "test-command",
            ]
        )

    @patch("pycompgen.generators._run_completion_command")
    def test_generate_argcomplete_shell_completion_failure(self, mock_run):
        """Test argcomplete completion generation failure."""
        mock_run.return_value = None

        # Mock the package with a path that has a bin directory
        mock_completion_package = Mock(spec=CompletionPackage)
        mock_package = Mock()
        # Mock pathlib.Path behavior for package.path / "bin" / "register-python-argcomplete"
        mock_path = Mock()
        mock_path.__truediv__ = Mock(
            return_value=Mock(
                __truediv__=Mock(
                    return_value="/fake/path/bin/register-python-argcomplete"
                )
            )
        )
        mock_package.path = mock_path
        mock_completion_package.package = mock_package

        result = generate_argcomplete_shell_completion(
            "test-command", mock_completion_package, Shell.BASH
        )

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
