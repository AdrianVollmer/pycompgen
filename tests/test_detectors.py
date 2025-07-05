from unittest.mock import Mock, patch
import subprocess
import json
from pathlib import Path

from pycompgen.detectors import (
    detect_packages,
    detect_uv_packages,
    detect_pipx_packages,
    parse_uv_output,
    parse_pipx_output,
)
from pycompgen.models import PackageManager


class TestDetectPackages:
    """Test the main detect_packages function."""

    @patch("pycompgen.detectors.detect_uv_packages")
    @patch("pycompgen.detectors.detect_pipx_packages")
    def test_detect_packages_combines_results(self, mock_pipx, mock_uv):
        """Test that detect_packages combines results from both sources."""
        mock_uv.return_value = [Mock(name="uv-package")]
        mock_pipx.return_value = [Mock(name="pipx-package")]

        result = detect_packages()

        assert len(result) == 2
        mock_uv.assert_called_once()
        mock_pipx.assert_called_once()


class TestDetectUvPackages:
    """Test uv tool package detection."""

    @patch("subprocess.run")
    def test_detect_uv_packages_success(self, mock_run):
        """Test successful uv tool detection."""
        mock_run.return_value = Mock(
            stdout="test-package v1.0.0 (/fake/path/to/venv)\n"
            "another-package v2.0.0 (/fake/path/to/another)\n",
            returncode=0,
        )

        result = detect_uv_packages()

        assert len(result) == 2
        assert result[0].name == "test-package"
        assert result[0].version == "1.0.0"
        # Path should be parsed from output, not hardcoded
        assert str(result[0].path) == "/fake/path/to/venv"
        assert result[0].manager == PackageManager.UV_TOOL

        mock_run.assert_called_once_with(
            ["uv", "tool", "list", "--show-paths"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_detect_uv_packages_command_not_found(self, mock_run):
        """Test handling when uv command is not found."""
        mock_run.side_effect = FileNotFoundError()

        result = detect_uv_packages()

        assert result == []

    @patch("subprocess.run")
    def test_detect_uv_packages_command_error(self, mock_run):
        """Test handling when uv command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["uv"])

        result = detect_uv_packages()

        assert result == []


class TestDetectPipxPackages:
    """Test pipx package detection."""

    @patch("subprocess.run")
    def test_detect_pipx_packages_success(self, mock_run):
        """Test successful pipx detection."""
        pipx_output = {
            "venvs": {
                "test-package": {
                    "pyvenv_cfg": {"home": "/fake/venv/bin"},
                    "metadata": {"main_package": {"package_version": "1.0.0"}},
                }
            }
        }

        mock_run.return_value = Mock(stdout=json.dumps(pipx_output), returncode=0)

        result = detect_pipx_packages()

        assert len(result) == 1
        assert result[0].name == "test-package"
        assert result[0].version == "1.0.0"
        assert result[0].path == Path("/fake/venv")
        assert result[0].manager == PackageManager.PIPX

    @patch("subprocess.run")
    def test_detect_pipx_packages_command_not_found(self, mock_run):
        """Test handling when pipx command is not found."""
        mock_run.side_effect = FileNotFoundError()

        result = detect_pipx_packages()

        assert result == []


class TestParseUvOutput:
    """Test parsing of uv tool output."""

    def test_parse_uv_output_valid_format(self):
        """Test parsing valid uv tool output."""
        output = """test-package v1.0.0 (/fake/path/to/venv)
- test-cmd (/fake/path/to/venv/bin/test-cmd)
another-package v2.1.0 (/another/path)
- another-cmd (/another/path/bin/another-cmd)
- second-cmd (/another/path/bin/second-cmd)
"""

        result = parse_uv_output(output)

        assert len(result) == 2
        assert result[0].name == "test-package"
        assert result[0].version == "1.0.0"
        assert result[0].path == Path("/fake/path/to/venv")
        assert result[0].commands == ["test-cmd"]
        assert result[1].name == "another-package"
        assert result[1].version == "2.1.0"
        assert result[1].commands == ["another-cmd", "second-cmd"]

    def test_parse_uv_output_no_path(self):
        """Test parsing uv output without path information."""
        output = "test-package v1.0.0\n"

        result = parse_uv_output(output)

        assert result == []

    def test_parse_uv_output_no_commands(self):
        """Test parsing uv output without command lines."""
        output = "test-package v1.0.0 (path: /fake/path/to/venv)\n"

        result = parse_uv_output(output)

        assert len(result) == 1
        assert result[0].name == "test-package"
        assert result[0].commands == []

    def test_parse_uv_output_empty(self):
        """Test parsing empty uv output."""
        result = parse_uv_output("")

        assert result == []

    def test_parse_uv_output_invalid_format(self):
        """Test parsing invalid uv output format."""
        output = "invalid-line\n"

        result = parse_uv_output(output)

        assert result == []


class TestParsePipxOutput:
    """Test parsing of pipx JSON output."""

    def test_parse_pipx_output_valid_json(self):
        """Test parsing valid pipx JSON output."""
        pipx_data = {
            "venvs": {
                "test-package": {
                    "pyvenv_cfg": {"home": "/fake/venv/bin"},
                    "metadata": {
                        "main_package": {
                            "package_version": "1.0.0",
                            "apps": ["test-cmd"],
                        }
                    },
                },
                "another-package": {
                    "pyvenv_cfg": {},
                    "metadata": {
                        "main_package": {
                            "package_version": "2.0.0",
                            "apps": ["another-cmd", "second-cmd"],
                        }
                    },
                },
            }
        }

        result = parse_pipx_output(json.dumps(pipx_data))

        assert len(result) == 2
        assert result[0].name == "test-package"
        assert result[0].version == "1.0.0"
        assert result[0].path == Path("/fake/venv")
        assert result[0].commands == ["test-cmd"]

        # Second package should use fallback path
        assert result[1].name == "another-package"
        assert result[1].version == "2.0.0"
        assert result[1].commands == ["another-cmd", "second-cmd"]

    def test_parse_pipx_output_invalid_json(self):
        """Test parsing invalid JSON."""
        result = parse_pipx_output("invalid json")

        assert result == []

    def test_parse_pipx_output_empty_venvs(self):
        """Test parsing pipx output with empty venvs."""
        pipx_data = {"venvs": {}}

        result = parse_pipx_output(json.dumps(pipx_data))

        assert result == []

    def test_parse_pipx_output_no_venvs_key(self):
        """Test parsing pipx output without venvs key."""
        pipx_data = {"other": "data"}

        result = parse_pipx_output(json.dumps(pipx_data))

        assert result == []

    def test_parse_pipx_output_no_apps(self):
        """Test parsing pipx output without apps field."""
        pipx_data = {
            "venvs": {
                "test-package": {
                    "pyvenv_cfg": {"home": "/fake/venv/bin"},
                    "metadata": {"main_package": {"package_version": "1.0.0"}},
                }
            }
        }

        result = parse_pipx_output(json.dumps(pipx_data))

        assert len(result) == 1
        assert result[0].name == "test-package"
        assert result[0].commands == []

    @patch("pathlib.Path.home")
    def test_parse_pipx_output_fallback_path(self, mock_home):
        """Test fallback path construction when home is not in pyvenv_cfg."""
        mock_home.return_value = Path("/home/user")

        pipx_data = {
            "venvs": {
                "test-package": {
                    "pyvenv_cfg": {},
                    "metadata": {"main_package": {"package_version": "1.0.0"}},
                }
            }
        }

        result = parse_pipx_output(json.dumps(pipx_data))

        assert len(result) == 1
        assert result[0].path == Path("/home/user/.local/pipx/venvs/test-package")
