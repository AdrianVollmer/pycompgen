import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
from pathlib import Path

from pycompgen.analyzers import (
    analyze_packages,
    analyze_package,
    detect_completion_type,
    get_python_path,
    has_dependency,
    find_package_commands,
)
from pycompgen.models import (
    InstalledPackage,
    CompletionPackage,
    PackageManager,
    CompletionType,
)


class TestAnalyzePackages:
    """Test the main analyze_packages function."""

    @patch('pycompgen.analyzers.analyze_package')
    def test_analyze_packages_filters_valid_packages(self, mock_analyze):
        """Test that analyze_packages filters out packages without completion support."""
        mock_packages = [Mock(), Mock(), Mock()]
        mock_analyze.side_effect = [
            Mock(spec=CompletionPackage),  # Valid package
            None,  # No completion support
            Mock(spec=CompletionPackage),  # Valid package
        ]
        
        result = analyze_packages(mock_packages)
        
        assert len(result) == 2
        assert mock_analyze.call_count == 3

    @patch('pycompgen.analyzers.analyze_package')
    def test_analyze_packages_empty_input(self, mock_analyze):
        """Test analyze_packages with empty input."""
        result = analyze_packages([])
        
        assert result == []
        mock_analyze.assert_not_called()


class TestAnalyzePackage:
    """Test individual package analysis."""

    @patch('pycompgen.analyzers.find_package_commands')
    @patch('pycompgen.analyzers.detect_completion_type')
    def test_analyze_package_success(self, mock_detect, mock_find_commands):
        """Test successful package analysis."""
        mock_package = Mock(spec=InstalledPackage)
        mock_detect.return_value = CompletionType.CLICK
        mock_find_commands.return_value = ["test-command"]
        
        result = analyze_package(mock_package)
        
        assert result is not None
        assert isinstance(result, CompletionPackage)
        assert result.package == mock_package
        assert result.completion_type == CompletionType.CLICK
        assert result.commands == ["test-command"]

    @patch('pycompgen.analyzers.find_package_commands')
    @patch('pycompgen.analyzers.detect_completion_type')
    def test_analyze_package_no_completion_type(self, mock_detect, mock_find_commands):
        """Test package analysis when no completion type is detected."""
        mock_package = Mock(spec=InstalledPackage)
        mock_detect.return_value = None
        
        result = analyze_package(mock_package)
        
        assert result is None
        mock_find_commands.assert_not_called()

    @patch('pycompgen.analyzers.find_package_commands')
    @patch('pycompgen.analyzers.detect_completion_type')
    def test_analyze_package_no_commands(self, mock_detect, mock_find_commands):
        """Test package analysis when no commands are found."""
        mock_package = Mock(spec=InstalledPackage)
        mock_detect.return_value = CompletionType.CLICK
        mock_find_commands.return_value = []
        
        result = analyze_package(mock_package)
        
        assert result is None


class TestDetectCompletionType:
    """Test completion type detection."""

    @patch('pycompgen.analyzers.has_dependency')
    @patch('pycompgen.analyzers.get_python_path')
    def test_detect_completion_type_click(self, mock_get_python, mock_has_dep, tmp_path):
        """Test detection of click completion type."""
        mock_package = Mock(spec=InstalledPackage)
        mock_python_path = tmp_path / "fake" / "python"
        mock_python_path.parent.mkdir(parents=True)
        mock_python_path.touch()
        mock_get_python.return_value = mock_python_path
        mock_has_dep.side_effect = lambda path, dep: dep == "click"
        
        result = detect_completion_type(mock_package)
        
        assert result == CompletionType.CLICK
        mock_has_dep.assert_called_with(mock_python_path, "click")

    @patch('pycompgen.analyzers.has_dependency')
    @patch('pycompgen.analyzers.get_python_path')
    def test_detect_completion_type_argcomplete(self, mock_get_python, mock_has_dep, tmp_path):
        """Test detection of argcomplete completion type."""
        mock_package = Mock(spec=InstalledPackage)
        mock_python_path = tmp_path / "fake" / "python"
        mock_python_path.parent.mkdir(parents=True)
        mock_python_path.touch()
        mock_get_python.return_value = mock_python_path
        mock_has_dep.side_effect = lambda path, dep: dep == "argcomplete"
        
        result = detect_completion_type(mock_package)
        
        assert result == CompletionType.ARGCOMPLETE
        assert mock_has_dep.call_count == 2  # Checks click first, then argcomplete

    @patch('pycompgen.analyzers.has_dependency')
    @patch('pycompgen.analyzers.get_python_path')
    def test_detect_completion_type_none(self, mock_get_python, mock_has_dep, tmp_path):
        """Test when no completion type is detected."""
        mock_package = Mock(spec=InstalledPackage)
        mock_python_path = tmp_path / "fake" / "python"
        mock_python_path.parent.mkdir(parents=True)
        mock_python_path.touch()
        mock_get_python.return_value = mock_python_path
        mock_has_dep.return_value = False
        
        result = detect_completion_type(mock_package)
        
        assert result is None

    @patch('pycompgen.analyzers.get_python_path')
    def test_detect_completion_type_no_python_path(self, mock_get_python):
        """Test when Python path cannot be found."""
        mock_package = Mock(spec=InstalledPackage)
        mock_get_python.return_value = None
        
        result = detect_completion_type(mock_package)
        
        assert result is None


class TestGetPythonPath:
    """Test Python path resolution."""

    def test_get_python_path_uv_tool(self, tmp_path):
        """Test Python path for uv tool package."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.UV_TOOL
        fake_venv = tmp_path / "fake" / "venv"
        fake_venv.mkdir(parents=True)
        mock_package.path = fake_venv
        
        with patch('pathlib.Path.exists', return_value=True):
            result = get_python_path(mock_package)
            
            assert result == fake_venv / "bin" / "python"

    def test_get_python_path_pipx(self, tmp_path):
        """Test Python path for pipx package."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.PIPX
        fake_pipx_venv = tmp_path / "fake" / "pipx" / "venv"
        fake_pipx_venv.mkdir(parents=True)
        mock_package.path = fake_pipx_venv
        
        with patch('pathlib.Path.exists', return_value=True):
            result = get_python_path(mock_package)
            
            assert result == fake_pipx_venv / "bin" / "python"

    def test_get_python_path_does_not_exist(self, tmp_path):
        """Test when Python path does not exist."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.UV_TOOL
        fake_venv = tmp_path / "fake" / "venv"
        fake_venv.mkdir(parents=True)
        mock_package.path = fake_venv
        
        with patch('pathlib.Path.exists', return_value=False):
            result = get_python_path(mock_package)
            
            assert result is None

    def test_get_python_path_unknown_manager(self):
        """Test with unknown package manager."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = "unknown"
        
        result = get_python_path(mock_package)
        
        assert result is None


class TestHasDependency:
    """Test dependency detection."""

    @patch('subprocess.run')
    def test_has_dependency_success(self, mock_run, tmp_path):
        """Test successful dependency detection."""
        mock_run.return_value = Mock(returncode=0)
        python_path = tmp_path / "fake" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.touch()
        
        result = has_dependency(python_path, "click")
        
        assert result is True
        mock_run.assert_called_once_with(
            [str(python_path), "-c", "import click"],
            capture_output=True,
            text=True,
            timeout=5,
        )

    @patch('subprocess.run')
    def test_has_dependency_import_error(self, mock_run, tmp_path):
        """Test when dependency import fails."""
        mock_run.return_value = Mock(returncode=1)
        python_path = tmp_path / "fake" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.touch()
        
        result = has_dependency(python_path, "nonexistent")
        
        assert result is False

    @patch('subprocess.run')
    def test_has_dependency_timeout(self, mock_run, tmp_path):
        """Test when dependency check times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["python"], timeout=5)
        python_path = tmp_path / "fake" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.touch()
        
        result = has_dependency(python_path, "click")
        
        assert result is False

    @patch('subprocess.run')
    def test_has_dependency_process_error(self, mock_run, tmp_path):
        """Test when subprocess fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["python"])
        python_path = tmp_path / "fake" / "python"
        python_path.parent.mkdir(parents=True)
        python_path.touch()
        
        result = has_dependency(python_path, "click")
        
        assert result is False


class TestFindPackageCommands:
    """Test command discovery."""

    def test_find_package_commands_uv_tool(self, temp_dir):
        """Test finding commands for uv tool package."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.UV_TOOL
        mock_package.path = temp_dir
        mock_package.name = "test-package"
        
        # Create bin directory with executable files
        bin_dir = temp_dir / "bin"
        bin_dir.mkdir()
        
        # Create executable commands
        (bin_dir / "test-command").touch()
        (bin_dir / "test-command").chmod(0o755)
        
        # Create non-executable file
        (bin_dir / "non-executable").touch()
        
        # Create python/pip executables (should be ignored)
        (bin_dir / "python").touch()
        (bin_dir / "python").chmod(0o755)
        (bin_dir / "pip").touch()
        (bin_dir / "pip").chmod(0o755)
        (bin_dir / "wheel").touch()
        (bin_dir / "wheel").chmod(0o755)
        
        result = find_package_commands(mock_package)
        
        assert "test-command" in result
        assert "python" not in result
        assert "pip" not in result
        assert "wheel" not in result
        assert "non-executable" not in result

    def test_find_package_commands_pipx(self, temp_dir):
        """Test finding commands for pipx package."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.PIPX
        mock_package.path = temp_dir
        mock_package.name = "pipx-package"
        
        # Create bin directory with executable files
        bin_dir = temp_dir / "bin"
        bin_dir.mkdir()
        
        (bin_dir / "pipx-command").touch()
        (bin_dir / "pipx-command").chmod(0o755)
        
        result = find_package_commands(mock_package)
        
        assert "pipx-command" in result

    def test_find_package_commands_no_bin_dir(self, tmp_path):
        """Test when bin directory doesn't exist."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.UV_TOOL
        nonexistent_path = tmp_path / "nonexistent"
        mock_package.path = nonexistent_path
        mock_package.name = "test-package"
        
        result = find_package_commands(mock_package)
        
        # Should fall back to package name
        assert result == ["test-package"]

    def test_find_package_commands_empty_bin_dir(self, temp_dir):
        """Test when bin directory is empty."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.UV_TOOL
        mock_package.path = temp_dir
        mock_package.name = "test-package"
        
        # Create empty bin directory
        bin_dir = temp_dir / "bin"
        bin_dir.mkdir()
        
        result = find_package_commands(mock_package)
        
        # Should fall back to package name
        assert result == ["test-package"]