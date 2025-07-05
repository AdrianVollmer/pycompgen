import pytest
from unittest.mock import Mock, patch
import subprocess
import json
from pathlib import Path
import tempfile

from pycompgen import main


class TestMainWorkflow:
    """Integration tests for the main workflow."""

    @patch("pycompgen.save_source_script")
    @patch("pycompgen.save_completions")
    @patch("pycompgen.generate_completions")
    @patch("pycompgen.analyze_packages")
    @patch("pycompgen.detect_packages")
    @patch("pycompgen.setup_logging")
    @patch("pycompgen.get_cache_dir")
    def test_main_workflow_success(
        self,
        mock_get_cache_dir,
        mock_setup_logging,
        mock_detect,
        mock_analyze,
        mock_generate,
        mock_save_completions,
        mock_save_source_script,
        temp_dir,
    ):
        """Test successful end-to-end workflow."""
        # Setup mocks
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_get_cache_dir.return_value = temp_dir

        # Mock detected packages
        mock_packages = [Mock(name="test-package")]
        mock_detect.return_value = mock_packages

        # Mock analyzed packages
        mock_completion_packages = [Mock(name="completion-package")]
        mock_analyze.return_value = mock_completion_packages

        # Mock generated completions
        mock_completions = [Mock(name="generated-completion")]
        mock_generate.return_value = mock_completions

        # Mock source script path
        source_script_path = temp_dir / "completions.sh"
        mock_save_source_script.return_value = source_script_path

        # Run main function
        with patch("sys.argv", ["pycompgen"]):
            main()

        # Verify workflow
        mock_detect.assert_called_once()
        mock_analyze.assert_called_once_with(mock_packages)
        mock_generate.assert_called_once_with(mock_completion_packages)
        mock_save_completions.assert_called_once_with(
            mock_completions, temp_dir, force=False
        )
        mock_save_source_script.assert_called_once_with(temp_dir)

        # Verify logging
        assert mock_logger.info.call_count >= 4

    @patch("pycompgen.setup_logging")
    @patch("sys.exit")
    def test_main_workflow_exception_handling(self, mock_exit, mock_setup_logging):
        """Test exception handling in main workflow."""
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger

        with patch("pycompgen.detect_packages", side_effect=Exception("Test error")):
            with patch("sys.argv", ["pycompgen"]):
                main()

        # Should log error and exit
        mock_logger.error.assert_called_once()
        mock_exit.assert_called_once_with(1)

    @patch("pycompgen.save_source_script")
    @patch("pycompgen.save_completions")
    @patch("pycompgen.generate_completions")
    @patch("pycompgen.analyze_packages")
    @patch("pycompgen.detect_packages")
    @patch("pycompgen.setup_logging")
    @patch("pycompgen.get_cache_dir")
    def test_main_workflow_verbose_mode(
        self,
        mock_get_cache_dir,
        mock_setup_logging,
        mock_detect,
        mock_analyze,
        mock_generate,
        mock_save_completions,
        mock_save_source_script,
        temp_dir,
        capsys,
    ):
        """Test verbose mode output."""
        # Setup mocks
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_get_cache_dir.return_value = temp_dir
        mock_detect.return_value = []
        mock_analyze.return_value = []
        mock_generate.return_value = []

        source_script_path = temp_dir / "completions.sh"
        mock_save_source_script.return_value = source_script_path

        # Run with verbose flag
        with patch("sys.argv", ["pycompgen", "--verbose"]):
            main()

        # Check console output
        captured = capsys.readouterr()
        assert "Completions saved to" in captured.out
        assert "Source script:" in captured.out
        assert "Add this to your shell config:" in captured.out

    @patch("pycompgen.save_source_script")
    @patch("pycompgen.save_completions")
    @patch("pycompgen.generate_completions")
    @patch("pycompgen.analyze_packages")
    @patch("pycompgen.detect_packages")
    @patch("pycompgen.setup_logging")
    def test_main_workflow_custom_cache_dir(
        self,
        mock_setup_logging,
        mock_detect,
        mock_analyze,
        mock_generate,
        mock_save_completions,
        mock_save_source_script,
        temp_dir,
    ):
        """Test workflow with custom cache directory."""
        # Setup mocks
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_detect.return_value = []
        mock_analyze.return_value = []
        mock_generate.return_value = []

        custom_cache_dir = temp_dir / "custom-cache"
        source_script_path = custom_cache_dir / "completions.sh"
        mock_save_source_script.return_value = source_script_path

        # Run with custom cache dir
        with patch("sys.argv", ["pycompgen", "--cache-dir", str(custom_cache_dir)]):
            main()

        # Verify custom cache dir was used
        mock_save_completions.assert_called_once()
        args = mock_save_completions.call_args[0]
        assert args[1] == custom_cache_dir

    @patch("pycompgen.save_source_script")
    @patch("pycompgen.save_completions")
    @patch("pycompgen.generate_completions")
    @patch("pycompgen.analyze_packages")
    @patch("pycompgen.detect_packages")
    @patch("pycompgen.setup_logging")
    @patch("pycompgen.get_cache_dir")
    def test_main_workflow_force_flag(
        self,
        mock_get_cache_dir,
        mock_setup_logging,
        mock_detect,
        mock_analyze,
        mock_generate,
        mock_save_completions,
        mock_save_source_script,
        temp_dir,
    ):
        """Test workflow with force flag."""
        # Setup mocks
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_get_cache_dir.return_value = temp_dir
        mock_detect.return_value = []
        mock_analyze.return_value = []
        mock_generate.return_value = []
        mock_save_source_script.return_value = temp_dir / "completions.sh"

        # Run with force flag
        with patch("sys.argv", ["pycompgen", "--force"]):
            main()

        # Verify force=True was passed
        mock_save_completions.assert_called_once()
        args, kwargs = mock_save_completions.call_args
        assert kwargs["force"] is True


class TestEndToEndWorkflow:
    """End-to-end tests with minimal mocking."""

    @patch("subprocess.run")
    def test_e2e_no_packages_found(self, mock_run, temp_dir, capsys):
        """Test end-to-end workflow when no packages are found."""
        # Mock subprocess calls to return empty results
        mock_run.side_effect = [
            # uv tool list
            subprocess.CalledProcessError(1, ["uv"]),
            # pipx list
            subprocess.CalledProcessError(1, ["pipx"]),
        ]

        with patch(
            "sys.argv", ["pycompgen", "--cache-dir", str(temp_dir), "--verbose"]
        ):
            main()

        # Should complete without error
        captured = capsys.readouterr()
        assert "Found 0 packages" in captured.err  # Log messages go to stderr
        assert "Found 0 packages with completion support" in captured.err
        assert "Generated 0 completions" in captured.err

    @patch("subprocess.run")
    def test_e2e_uv_packages_no_completion_support(self, mock_run, temp_dir, capsys):
        """Test workflow with uv packages that don't support completions."""
        # Mock uv tool list output
        uv_output = "test-package v1.0.0 (path: /fake/venv)\n"

        mock_run.side_effect = [
            # uv tool list
            Mock(stdout=uv_output, returncode=0),
            # pipx list (fails)
            subprocess.CalledProcessError(1, ["pipx"]),
            # Python dependency checks (both fail)
            Mock(returncode=1),  # click import fails
            Mock(returncode=1),  # argcomplete import fails
        ]

        with patch(
            "sys.argv", ["pycompgen", "--cache-dir", str(temp_dir), "--verbose"]
        ):
            main()

        captured = capsys.readouterr()
        assert "Found 1 packages" in captured.err  # Log messages go to stderr
        assert "Found 0 packages with completion support" in captured.err

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_e2e_click_package_with_completion(
        self, mock_exists, mock_run, temp_dir, capsys
    ):
        """Test workflow with click package that supports completions."""
        # Mock uv tool list output

        # Mock file system
        def mock_exists_func():
            # This needs access to the mock object to get the path
            # Let's use the mock's call history to get the path object
            return True  # Just return True for all paths to simplify

        mock_exists.return_value = True

        # Create a mock bin directory with executable
        with tempfile.TemporaryDirectory() as temp_venv:
            venv_path = Path(temp_venv)
            bin_dir = venv_path / "bin"
            bin_dir.mkdir()
            click_command = bin_dir / "click-command"
            click_command.touch()
            click_command.chmod(0o755)

            mock_run.side_effect = [
                # uv tool list
                Mock(
                    stdout=f"click-package v1.0.0 (path: {venv_path})\n", returncode=0
                ),
                # pipx list (fails)
                subprocess.CalledProcessError(1, ["pipx"]),
                # click import succeeds
                Mock(returncode=0),
                # click completion generation
                Mock(stdout="click completion output", returncode=0),
                # click completion generation (zsh)
                Mock(stdout="click zsh completion output", returncode=0),
            ]

            with patch(
                "pycompgen.analyzers.find_package_commands",
                return_value=["click-command"],
            ):
                with patch(
                    "sys.argv", ["pycompgen", "--cache-dir", str(temp_dir), "--verbose"]
                ):
                    main()

        captured = capsys.readouterr()
        assert "Found 1 packages" in captured.err  # Log messages go to stderr
        assert "Found 1 packages with completion support" in captured.err
        assert "Generated 1 completions" in captured.err

        # Check that completion file was created
        completion_files = list(temp_dir.glob("*.sh"))
        assert len(completion_files) >= 1  # At least the source script

        # Check that source script was created
        source_script = temp_dir / "completions.sh"
        assert source_script.exists()

    @patch("subprocess.run")
    def test_e2e_pipx_argcomplete_package(self, mock_run, temp_dir, capsys):
        """Test workflow with pipx argcomplete package."""
        # Mock pipx list output
        pipx_output = {
            "venvs": {
                "argcomplete-package": {
                    "pyvenv_cfg": {"home": "/fake/pipx/venv/bin"},
                    "metadata": {"main_package": {"package_version": "2.0.0"}},
                }
            }
        }

        mock_run.side_effect = [
            # uv tool list (fails)
            subprocess.CalledProcessError(1, ["uv"]),
            # pipx list
            Mock(stdout=json.dumps(pipx_output), returncode=0),
            # click import fails
            Mock(returncode=1),
            # argcomplete import succeeds
            Mock(returncode=0),
            # argcomplete completion generation
            Mock(stdout="argcomplete completion output", returncode=0),
        ]

        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "pycompgen.analyzers.find_package_commands",
                return_value=["argcomplete-command"],
            ):
                with patch(
                    "sys.argv", ["pycompgen", "--cache-dir", str(temp_dir), "--verbose"]
                ):
                    main()

        captured = capsys.readouterr()
        assert "Found 1 packages" in captured.err  # Log messages go to stderr
        assert "Found 1 packages with completion support" in captured.err
        assert "Generated 1 completions" in captured.err


class TestErrorScenarios:
    """Test various error scenarios."""

    @patch("pycompgen.detect_packages")
    @patch("pycompgen.setup_logging")
    def test_detection_error_handling(self, mock_setup_logging, mock_detect, capsys):
        """Test handling of package detection errors."""
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_detect.side_effect = Exception("Detection failed")

        with patch("sys.argv", ["pycompgen", "--verbose"]):
            with pytest.raises(SystemExit):
                main()

        # Should log error
        mock_logger.error.assert_called_once()

        # Should print error in verbose mode
        captured = capsys.readouterr()
        assert "Error: Detection failed" in captured.err

    @patch("pycompgen.analyze_packages")
    @patch("pycompgen.detect_packages")
    @patch("pycompgen.setup_logging")
    def test_analysis_error_handling(
        self, mock_setup_logging, mock_detect, mock_analyze
    ):
        """Test handling of package analysis errors."""
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_detect.return_value = [Mock()]
        mock_analyze.side_effect = Exception("Analysis failed")

        with patch("sys.argv", ["pycompgen"]):
            with pytest.raises(SystemExit):
                main()

        mock_logger.error.assert_called_once()

    @patch("pycompgen.generate_completions")
    @patch("pycompgen.analyze_packages")
    @patch("pycompgen.detect_packages")
    @patch("pycompgen.setup_logging")
    def test_generation_error_handling(
        self, mock_setup_logging, mock_detect, mock_analyze, mock_generate
    ):
        """Test handling of completion generation errors."""
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_detect.return_value = [Mock()]
        mock_analyze.return_value = [Mock()]
        mock_generate.side_effect = Exception("Generation failed")

        with patch("sys.argv", ["pycompgen"]):
            with pytest.raises(SystemExit):
                main()

        mock_logger.error.assert_called_once()
