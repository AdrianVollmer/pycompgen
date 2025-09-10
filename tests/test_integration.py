import pytest
from unittest.mock import Mock, patch
import subprocess
import json
from pathlib import Path
import tempfile
import logging

from pycompgen import main


class TestMainWorkflow:
    """Integration tests for the main workflow."""

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

        # Run main function
        with patch("sys.argv", ["pycompgen", "--shel", "bash"]):
            main()

        # Verify workflow
        mock_detect.assert_called_once()
        mock_analyze.assert_called_once_with(mock_packages)
        # Should be called with completion packages and shell
        assert mock_generate.call_count == 1
        call_args = mock_generate.call_args[0]
        assert call_args[0] == mock_completion_packages
        # Second argument should be a Shell enum
        mock_save_completions.assert_called_once_with(
            mock_completions, temp_dir, force=False
        )

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

    @patch("pycompgen.cache.get_cache_dir")
    @patch("pycompgen.save_completions")
    @patch("pycompgen.generate_completions")
    @patch("pycompgen.analyze_packages")
    @patch("pycompgen.detect_packages")
    @patch("pycompgen.get_cache_dir")
    def test_main_workflow_verbose_mode(
        self,
        mock_get_cache_dir,
        mock_detect,
        mock_analyze,
        mock_generate,
        mock_save_completions,
        temp_dir,
        caplog,
    ):
        """Test verbose mode output."""
        # Setup mocks
        mock_get_cache_dir.return_value = temp_dir
        mock_detect.return_value = []
        mock_analyze.return_value = []
        mock_generate.return_value = []

        # Run with verbose flag
        with patch("sys.argv", ["pycompgen", "--verbose"]):
            with caplog.at_level(logging.INFO, logger="pycompgen"):
                main()

        # Check console output
        assert "Detecting installed packages" in caplog.record_tuples[0][2]

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

        # Run with custom cache dir
        with patch("sys.argv", ["pycompgen", "--cache-dir", str(custom_cache_dir)]):
            main()

        # Verify custom cache dir was used
        mock_save_completions.assert_called_once()
        args = mock_save_completions.call_args[0]
        assert args[1] == custom_cache_dir

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

        # Run with force flag
        with patch("sys.argv", ["pycompgen", "--force"]):
            main()

        # Verify force=True was passed
        mock_save_completions.assert_called_once()
        args, kwargs = mock_save_completions.call_args
        assert kwargs["force"] is True


class TestEndToEndWorkflow:
    """End-to-end tests with minimal mocking."""

    @patch("shutil.which")
    @patch("pycompgen.generators.generate_hardcoded_completion")
    @patch("subprocess.run")
    def test_e2e_no_packages_found(
        self, mock_run, mock_hardcoded, mock_which, temp_dir, capsys
    ):
        """Test end-to-end workflow when no packages are found."""
        # Mock hardcoded completion to return empty list
        mock_hardcoded.return_value = []

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

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_e2e_uv_packages_no_completion_support(
        self, mock_run, mock_which, temp_dir, capsys
    ):
        """Test workflow with uv packages that don't support completions."""
        # Mock shutil.which to return None (no hardcoded commands found)
        mock_which.return_value = None

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

    @patch("pycompgen.generators.generate_hardcoded_completion")
    @patch("subprocess.run")
    def test_e2e_pipx_argcomplete_package(
        self, mock_run, mock_hardcoded, temp_dir, capsys
    ):
        """Test workflow with pipx argcomplete package."""
        # Mock hardcoded completion to return empty list
        mock_hardcoded.return_value = []

        # Create a temporary directory for the pipx venv
        with tempfile.TemporaryDirectory() as temp_venv:
            venv_path = Path(temp_venv)

            # Create the bin directory and python executable that get_python_path expects
            bin_dir = venv_path / "bin"
            bin_dir.mkdir(parents=True)
            python_exe = bin_dir / "python"
            python_exe.touch()
            python_exe.chmod(0o755)

            # Create the package directory structure that the new has_dependency expects
            package_dir = (
                venv_path / "lib" / "python3.11" / "site-packages" / "argcomplete"
            )
            package_dir.mkdir(parents=True)
            # Create a test Python file that imports argcomplete
            (package_dir / "__init__.py").write_text("import argcomplete\n")

            # Create METADATA structure for the new has_dependency function
            metadata_dir = (
                venv_path
                / "lib"
                / "python3.11"
                / "site-packages"
                / "argcomplete-2.0.0-info"
            )
            metadata_dir.mkdir(parents=True)
            metadata_file = metadata_dir / "METADATA"
            metadata_content = """Name: argcomplete
Version: 2.0.0
Requires-Dist: argcomplete

This package provides argcomplete functionality."""
            metadata_file.write_text(metadata_content)

            # Mock pipx list output
            pipx_output = {
                "venvs": {
                    "argcomplete": {
                        "pyvenv_cfg": {"home": f"{venv_path}/bin"},
                        "metadata": {"main_package": {"package_version": "2.0.0"}},
                    }
                }
            }

            mock_run.side_effect = [
                # uv tool list (fails)
                subprocess.CalledProcessError(1, ["uv"]),
                # pipx list
                Mock(stdout=json.dumps(pipx_output), returncode=0),
                # argcomplete completion generation (bash)
                Mock(stdout="argcomplete completion output", returncode=0),
                # argcomplete completion generation (zsh)
                Mock(stdout="argcomplete zsh completion output", returncode=0),
            ]

            with patch(
                "pycompgen.analyzers.find_package_commands",
                return_value=["argcomplete"],
            ):
                with patch(
                    "sys.argv", ["pycompgen", "--cache-dir", str(temp_dir), "--verbose"]
                ):
                    main()

        captured = capsys.readouterr()
        assert "Found 1 packages" in captured.err  # Log messages go to stderr
        assert "Found 1 packages with completion support" in captured.err
        assert (
            "Generated 1 completions" in captured.err
        )  # Argcomplete now generates for single shell


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


class TestCooldownFeature:
    """Test cooldown functionality."""

    @patch("pycompgen.cache.get_cache_dir")
    @patch("pycompgen.get_cache_dir")
    @patch("pycompgen.setup_logging")
    @patch("pycompgen.time.time")
    def test_cooldown_skips_recent_completions(
        self,
        mock_time,
        mock_setup_logging,
        mock_get_cache_dir,
        mock_cache_get_cache_dir,
        temp_dir,
    ):
        """Test that recent completions are skipped due to cooldown."""
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_get_cache_dir.return_value = temp_dir
        mock_cache_get_cache_dir.return_value = temp_dir

        # Create a recent completion file in the shell-specific directory
        bash_dir = temp_dir / "pycompgen" / "bash"
        bash_dir.mkdir(parents=True)
        completion_file = bash_dir / "test-package.sh"
        completion_file.write_text("# test completion")

        # Mock current time as 30 seconds after file creation
        file_mtime = completion_file.stat().st_mtime
        mock_time.return_value = file_mtime + 30  # 30 seconds later

        with patch(
            "sys.argv", ["pycompgen", "--shell", "bash", "--cooldown-time", "60"]
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        # Should exit with code 0 (success, but skipped)
        assert exc_info.value.code == 0

        # Should log cooldown message
        mock_logger.info.assert_called()
        log_message = mock_logger.info.call_args[0][0]
        assert "Skipping regeneration" in log_message
        assert "30.0s ago" in log_message

    @patch("pycompgen.cache.get_cache_dir")
    @patch("pycompgen.save_completions")
    @patch("pycompgen.generate_completions")
    @patch("pycompgen.analyze_packages")
    @patch("pycompgen.detect_packages")
    @patch("pycompgen.get_cache_dir")
    @patch("pycompgen.setup_logging")
    @patch("pycompgen.time.time")
    def test_cooldown_allows_old_completions(
        self,
        mock_time,
        mock_setup_logging,
        mock_get_cache_dir,
        mock_detect,
        mock_analyze,
        mock_generate,
        mock_save_completions,
        mock_cache_get_cache_dir,
        temp_dir,
    ):
        """Test that old completions are regenerated after cooldown period."""
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_get_cache_dir.return_value = temp_dir
        mock_cache_get_cache_dir.return_value = temp_dir
        # Setup mocks for normal workflow
        mock_detect.return_value = []
        mock_analyze.return_value = []
        mock_generate.return_value = []

        # Create an old completion file in the shell-specific directory
        bash_dir = temp_dir / "pycompgen" / "bash"
        bash_dir.mkdir(parents=True)
        completion_file = bash_dir / "old-package.sh"
        completion_file.write_text("# old completion")

        # Mock current time as 90 seconds after file creation (past 60s cooldown)
        file_mtime = completion_file.stat().st_mtime
        mock_time.return_value = file_mtime + 90  # 90 seconds later

        with patch("sys.argv", ["pycompgen", "--cooldown-time", "60"]):
            main()

        # Should proceed with normal workflow
        mock_detect.assert_called_once()
        mock_analyze.assert_called_once()
        mock_generate.assert_called_once()

    @patch("pycompgen.cache.get_cache_dir")
    @patch("pycompgen.save_completions")
    @patch("pycompgen.generate_completions")
    @patch("pycompgen.analyze_packages")
    @patch("pycompgen.detect_packages")
    @patch("pycompgen.get_cache_dir")
    @patch("pycompgen.setup_logging")
    @patch("pycompgen.time.time")
    def test_cooldown_bypassed_by_force(
        self,
        mock_time,
        mock_setup_logging,
        mock_get_cache_dir,
        mock_detect,
        mock_analyze,
        mock_generate,
        mock_save_completions,
        mock_cache_get_cache_dir,
        temp_dir,
    ):
        """Test that --force bypasses cooldown check."""
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_get_cache_dir.return_value = temp_dir
        mock_cache_get_cache_dir.return_value = temp_dir
        # Setup mocks for normal workflow
        mock_detect.return_value = []
        mock_analyze.return_value = []
        mock_generate.return_value = []

        # Create a very recent completion file in the shell-specific directory
        bash_dir = temp_dir / "pycompgen" / "bash"
        bash_dir.mkdir(parents=True)
        completion_file = bash_dir / "recent-package.sh"
        completion_file.write_text("# recent completion")

        # Mock current time as 10 seconds after file creation (well within cooldown)
        file_mtime = completion_file.stat().st_mtime
        mock_time.return_value = file_mtime + 10  # 10 seconds later

        with patch("sys.argv", ["pycompgen", "--cooldown-time", "60", "--force"]):
            main()

        # Should proceed with normal workflow despite recent completion
        mock_detect.assert_called_once()
        mock_analyze.assert_called_once()
        mock_generate.assert_called_once()

    @patch("pycompgen.get_cache_dir")
    @patch("pycompgen.setup_logging")
    def test_cooldown_handles_missing_source_script(
        self, mock_setup_logging, mock_get_cache_dir, temp_dir
    ):
        """Test that missing source script doesn't cause cooldown to fail."""
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_get_cache_dir.return_value = temp_dir

        # Don't create source script - it should not exist
        with patch("pycompgen.detect_packages") as mock_detect:
            mock_detect.return_value = []
            with patch("pycompgen.analyze_packages") as mock_analyze:
                mock_analyze.return_value = []
                with patch("pycompgen.generate_completions") as mock_generate:
                    mock_generate.return_value = []
                    with patch("pycompgen.save_completions"):
                        with patch(
                            "sys.argv",
                            [
                                "pycompgen",
                                "--shell",
                                "bash",
                                "--cooldown-time",
                                "60",
                            ],
                        ):
                            main()

        # Should proceed normally when source script doesn't exist
        mock_detect.assert_called_once()

    @patch("pycompgen.get_cache_dir")
    @patch("pycompgen.setup_logging")
    def test_source_flag_bypasses_cooldown(
        self, mock_setup_logging, mock_get_cache_dir, temp_dir
    ):
        """Test that --source flag bypasses cooldown check."""
        mock_logger = Mock()
        mock_setup_logging.return_value = mock_logger
        mock_get_cache_dir.return_value = temp_dir

        # Create a recent source script
        source_script = temp_dir / "__completions__.bash.sh"
        source_script.write_text("# test completion content")

        with patch(
            "sys.argv",
            ["pycompgen", "--shell", "bash", "--source", "--cooldown-time", "60"],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        # Should exit with code 0 (success)
        assert exc_info.value.code == 0
