from unittest.mock import Mock, patch

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

    @patch("pycompgen.analyzers.analyze_package")
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

    @patch("pycompgen.analyzers.analyze_package")
    def test_analyze_packages_empty_input(self, mock_analyze):
        """Test analyze_packages with empty input."""
        result = analyze_packages([])

        assert result == []
        mock_analyze.assert_not_called()


class TestAnalyzePackage:
    """Test individual package analysis."""

    @patch("pycompgen.analyzers.find_package_commands")
    @patch("pycompgen.analyzers.detect_completion_type")
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

    @patch("pycompgen.analyzers.find_package_commands")
    @patch("pycompgen.analyzers.detect_completion_type")
    def test_analyze_package_no_completion_type(self, mock_detect, mock_find_commands):
        """Test package analysis when no completion type is detected."""
        mock_package = Mock(spec=InstalledPackage)
        mock_detect.return_value = None

        result = analyze_package(mock_package)

        assert result is None
        mock_find_commands.assert_not_called()

    @patch("pycompgen.analyzers.find_package_commands")
    @patch("pycompgen.analyzers.detect_completion_type")
    def test_analyze_package_no_commands(self, mock_detect, mock_find_commands):
        """Test package analysis when no commands are found."""
        mock_package = Mock(spec=InstalledPackage)
        mock_detect.return_value = CompletionType.CLICK
        mock_find_commands.return_value = []

        result = analyze_package(mock_package)

        assert result is None


class TestDetectCompletionType:
    """Test completion type detection."""

    @patch("pycompgen.analyzers.find_package_commands")
    @patch("pycompgen.analyzers.has_dependency")
    @patch("pycompgen.analyzers.get_python_path")
    def test_detect_completion_type_click(
        self, mock_get_python, mock_has_dep, mock_find_commands, tmp_path
    ):
        """Test detection of click completion type."""
        # Create package directory structure
        package_base = tmp_path / "packages" / "test-package"
        package_dir = (
            package_base / "lib" / "python3.11" / "site-packages" / "test-package"
        )
        package_dir.mkdir(parents=True)

        mock_package = Mock(spec=InstalledPackage)
        mock_package.path = package_base
        mock_package.name = "test-package"

        mock_python_path = tmp_path / "fake" / "python"
        mock_python_path.parent.mkdir(parents=True)
        mock_python_path.touch()
        mock_get_python.return_value = mock_python_path
        mock_has_dep.side_effect = lambda package, dep: dep == "click"
        mock_find_commands.return_value = ["regular-command"]  # No hardcoded commands

        result = detect_completion_type(mock_package)

        assert result == CompletionType.CLICK
        mock_has_dep.assert_called_with(mock_package, "click")

    @patch("pycompgen.analyzers.find_package_commands")
    @patch("pycompgen.analyzers.has_dependency")
    @patch("pycompgen.analyzers.get_python_path")
    def test_detect_completion_type_argcomplete(
        self, mock_get_python, mock_has_dep, mock_find_commands, tmp_path
    ):
        """Test detection of argcomplete completion type."""
        # Create package directory structure
        package_base = tmp_path / "packages" / "test-package"
        package_dir = (
            package_base / "lib" / "python3.11" / "site-packages" / "test-package"
        )
        package_dir.mkdir(parents=True)

        mock_package = Mock(spec=InstalledPackage)
        mock_package.path = package_base
        mock_package.name = "test-package"

        mock_python_path = tmp_path / "fake" / "python"
        mock_python_path.parent.mkdir(parents=True)
        mock_python_path.touch()
        mock_get_python.return_value = mock_python_path
        mock_has_dep.side_effect = lambda package, dep: dep == "argcomplete"
        mock_find_commands.return_value = ["regular-command"]  # No hardcoded commands

        result = detect_completion_type(mock_package)

        assert result == CompletionType.ARGCOMPLETE
        assert mock_has_dep.call_count == 2  # Checks click first, then argcomplete

    @patch("pycompgen.analyzers.find_package_commands")
    @patch("pycompgen.analyzers.has_dependency")
    @patch("pycompgen.analyzers.get_python_path")
    def test_detect_completion_type_none(
        self, mock_get_python, mock_has_dep, mock_find_commands, tmp_path
    ):
        """Test when no completion type is detected."""
        # Create package directory structure
        package_base = tmp_path / "packages" / "test-package"
        package_dir = (
            package_base / "lib" / "python3.11" / "site-packages" / "test-package"
        )
        package_dir.mkdir(parents=True)

        mock_package = Mock(spec=InstalledPackage)
        mock_package.path = package_base
        mock_package.name = "test-package"

        mock_python_path = tmp_path / "fake" / "python"
        mock_python_path.parent.mkdir(parents=True)
        mock_python_path.touch()
        mock_get_python.return_value = mock_python_path
        mock_has_dep.return_value = False
        mock_find_commands.return_value = ["regular-command"]  # No hardcoded commands

        result = detect_completion_type(mock_package)

        assert result is None

    @patch("pycompgen.analyzers.find_package_commands")
    @patch("pycompgen.analyzers.get_python_path")
    def test_detect_completion_type_no_python_path(
        self, mock_get_python, mock_find_commands, tmp_path
    ):
        """Test when Python path cannot be found."""
        # Create package directory structure but python path will be None
        package_base = tmp_path / "packages" / "test-package"
        package_dir = (
            package_base / "lib" / "python3.11" / "site-packages" / "test-package"
        )
        package_dir.mkdir(parents=True)

        mock_package = Mock(spec=InstalledPackage)
        mock_package.path = package_base
        mock_package.name = "test-package"

        mock_get_python.return_value = None
        mock_find_commands.return_value = ["regular-command"]  # No hardcoded commands

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

        with patch("pathlib.Path.exists", return_value=True):
            result = get_python_path(mock_package)

            assert result == fake_venv / "bin" / "python"

    def test_get_python_path_pipx(self, tmp_path):
        """Test Python path for pipx package."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.PIPX
        fake_pipx_venv = tmp_path / "fake" / "pipx" / "venv"
        fake_pipx_venv.mkdir(parents=True)
        mock_package.path = fake_pipx_venv

        with patch("pathlib.Path.exists", return_value=True):
            result = get_python_path(mock_package)

            assert result == fake_pipx_venv / "bin" / "python"

    def test_get_python_path_does_not_exist(self, tmp_path):
        """Test when Python path does not exist."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.UV_TOOL
        fake_venv = tmp_path / "fake" / "venv"
        fake_venv.mkdir(parents=True)
        mock_package.path = fake_venv

        with patch("pathlib.Path.exists", return_value=False):
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

    def test_has_dependency_success(self, tmp_path):
        """Test successful dependency detection."""
        # Create package structure with METADATA
        package_base = tmp_path / "test-package"
        metadata_dir = (
            package_base
            / "lib"
            / "python3.11"
            / "site-packages"
            / "test_package-1.0.0-info"
        )
        metadata_dir.mkdir(parents=True)

        metadata_file = metadata_dir / "METADATA"
        metadata_content = """Name: test-package
Version: 1.0.0
Requires-Dist: click>=7.0
Requires-Dist: requests>=2.25.0

This is the package description."""
        metadata_file.write_text(metadata_content)

        mock_package = Mock(spec=InstalledPackage)
        mock_package.name = "test-package"
        mock_package.path = package_base

        result = has_dependency(mock_package, "click")

        assert result is True

    def test_has_dependency_not_found(self, tmp_path):
        """Test when dependency is not found."""
        # Create package structure with METADATA
        package_base = tmp_path / "test-package"
        metadata_dir = (
            package_base
            / "lib"
            / "python3.11"
            / "site-packages"
            / "test_package-1.0.0-info"
        )
        metadata_dir.mkdir(parents=True)

        metadata_file = metadata_dir / "METADATA"
        metadata_content = """Name: test-package
Version: 1.0.0
Requires-Dist: requests>=2.25.0

This is the package description."""
        metadata_file.write_text(metadata_content)

        mock_package = Mock(spec=InstalledPackage)
        mock_package.name = "test-package"
        mock_package.path = package_base

        result = has_dependency(mock_package, "click")

        assert result is False

    def test_has_dependency_no_metadata_dir(self, tmp_path):
        """Test when metadata directory is not found."""
        package_base = tmp_path / "test-package"
        package_base.mkdir()

        mock_package = Mock(spec=InstalledPackage)
        mock_package.name = "test-package"
        mock_package.path = package_base

        result = has_dependency(mock_package, "click")

        assert result is False

    def test_has_dependency_with_version_constraints(self, tmp_path):
        """Test dependency detection with version constraints."""
        # Create package structure with METADATA
        package_base = tmp_path / "test-package"
        metadata_dir = (
            package_base
            / "lib"
            / "python3.11"
            / "site-packages"
            / "test_package-1.0.0-info"
        )
        metadata_dir.mkdir(parents=True)

        metadata_file = metadata_dir / "METADATA"
        metadata_content = """Name: test-package
Version: 1.0.0
Requires-Dist: click>=7.0,<9.0
Requires-Dist: requests>=2.25.0; python_version>="3.7"

This is the package description."""
        metadata_file.write_text(metadata_content)

        mock_package = Mock(spec=InstalledPackage)
        mock_package.name = "test-package"
        mock_package.path = package_base

        result = has_dependency(mock_package, "click")

        assert result is True

    def test_has_dependency_hyphen_to_underscore_conversion(self, tmp_path):
        """Test package name conversion from hyphen to underscore."""
        # Create package structure with METADATA for package with hyphen in name
        package_base = tmp_path / "my-test-package"
        metadata_dir = (
            package_base
            / "lib"
            / "python3.11"
            / "site-packages"
            / "my_test_package-1.0.0-info"
        )
        metadata_dir.mkdir(parents=True)

        metadata_file = metadata_dir / "METADATA"
        metadata_content = """Name: my-test-package
Version: 1.0.0
Requires-Dist: click>=7.0

This is the package description."""
        metadata_file.write_text(metadata_content)

        mock_package = Mock(spec=InstalledPackage)
        mock_package.name = "my-test-package"
        mock_package.path = package_base

        result = has_dependency(mock_package, "click")

        assert result is True


class TestFindPackageCommands:
    """Test command discovery."""

    def test_find_package_commands_uv_tool(self, temp_dir):
        """Test finding commands for uv tool package with commands from package manager."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.UV_TOOL
        mock_package.path = temp_dir
        mock_package.name = "test-package"
        mock_package.commands = ["test-command", "another-cmd"]

        result = find_package_commands(mock_package)

        assert result == ["test-command", "another-cmd"]

    def test_find_package_commands_pipx(self, temp_dir):
        """Test finding commands for pipx package with commands from package manager."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.PIPX
        mock_package.path = temp_dir
        mock_package.name = "pipx-package"
        mock_package.commands = ["pipx-command"]

        result = find_package_commands(mock_package)

        assert result == ["pipx-command"]

    def test_find_package_commands_no_commands(self, tmp_path):
        """Test fallback when no commands are available."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.UV_TOOL
        mock_package.path = tmp_path
        mock_package.name = "test-package"
        mock_package.commands = None

        result = find_package_commands(mock_package)

        # Should fall back to package name
        assert result == ["test-package"]

    def test_find_package_commands_empty_commands(self, temp_dir):
        """Test fallback when commands list is empty."""
        mock_package = Mock(spec=InstalledPackage)
        mock_package.manager = PackageManager.UV_TOOL
        mock_package.path = temp_dir
        mock_package.name = "test-package"
        mock_package.commands = []

        result = find_package_commands(mock_package)

        # Should fall back to package name
        assert result == ["test-package"]
