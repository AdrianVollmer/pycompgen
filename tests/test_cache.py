import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import tempfile
import os

from pycompgen.cache import (
    get_cache_dir,
    save_completions,
    save_source_script,
    generate_source_script,
)
from pycompgen.models import GeneratedCompletion, CompletionType


class TestGetCacheDir:
    """Test cache directory resolution."""

    def test_get_cache_dir_xdg_cache_home(self, tmp_path):
        """Test cache directory with XDG_CACHE_HOME set."""
        custom_cache = tmp_path / "custom" / "cache"
        custom_cache.mkdir(parents=True)
        
        with patch.dict(os.environ, {"XDG_CACHE_HOME": str(custom_cache)}):
            result = get_cache_dir()
            assert result == custom_cache / "pycompgen"

    def test_get_cache_dir_fallback(self, tmp_path):
        """Test cache directory fallback to ~/.cache."""
        mock_home = tmp_path / "home" / "user"
        mock_home.mkdir(parents=True)
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('pathlib.Path.home', return_value=mock_home):
                result = get_cache_dir()
                assert result == mock_home / ".cache" / "pycompgen"

    def test_get_cache_dir_empty_xdg(self, tmp_path):
        """Test cache directory with empty XDG_CACHE_HOME."""
        mock_home = tmp_path / "home" / "user"
        mock_home.mkdir(parents=True)
        
        with patch.dict(os.environ, {"XDG_CACHE_HOME": ""}):
            with patch('pathlib.Path.home', return_value=mock_home):
                result = get_cache_dir()
                assert result == mock_home / ".cache" / "pycompgen"


class TestSaveCompletions:
    """Test saving completions to cache."""

    def test_save_completions_success(self, temp_dir):
        """Test successful completion saving."""
        completions = [
            GeneratedCompletion(
                package_name="test-package",
                completion_type=CompletionType.CLICK,
                content="test completion content",
                commands=["test-command"]
            ),
            GeneratedCompletion(
                package_name="another-package",
                completion_type=CompletionType.ARGCOMPLETE,
                content="another completion content",
                commands=["another-command"]
            )
        ]
        
        save_completions(completions, temp_dir)
        
        # Check that files were created
        assert (temp_dir / "test-package.sh").exists()
        assert (temp_dir / "another-package.sh").exists()
        
        # Check content
        content1 = (temp_dir / "test-package.sh").read_text()
        assert "test completion content" in content1
        
        content2 = (temp_dir / "another-package.sh").read_text()
        assert "another completion content" in content2

    def test_save_completions_creates_directory(self, temp_dir):
        """Test that cache directory is created if it doesn't exist."""
        cache_dir = temp_dir / "new-cache-dir"
        assert not cache_dir.exists()
        
        completions = [
            GeneratedCompletion(
                package_name="test-package",
                completion_type=CompletionType.CLICK,
                content="test content",
                commands=["test-command"]
            )
        ]
        
        save_completions(completions, cache_dir)
        
        assert cache_dir.exists()
        assert (cache_dir / "test-package.sh").exists()

    def test_save_completions_no_overwrite_without_force(self, temp_dir):
        """Test that existing files are not overwritten without force."""
        completion_file = temp_dir / "test-package.sh"
        completion_file.write_text("original content")
        original_mtime = completion_file.stat().st_mtime
        
        completions = [
            GeneratedCompletion(
                package_name="test-package",
                completion_type=CompletionType.CLICK,
                content="new content",
                commands=["test-command"]
            )
        ]
        
        save_completions(completions, temp_dir, force=False)
        
        # File should not be overwritten
        assert completion_file.read_text() == "original content"
        assert completion_file.stat().st_mtime == original_mtime

    def test_save_completions_overwrite_with_force(self, temp_dir):
        """Test that existing files are overwritten with force."""
        completion_file = temp_dir / "test-package.sh"
        completion_file.write_text("original content")
        
        completions = [
            GeneratedCompletion(
                package_name="test-package",
                completion_type=CompletionType.CLICK,
                content="new content",
                commands=["test-command"]
            )
        ]
        
        save_completions(completions, temp_dir, force=True)
        
        # File should be overwritten
        assert "new content" in completion_file.read_text()

    def test_save_completions_empty_list(self, temp_dir):
        """Test saving empty completion list."""
        save_completions([], temp_dir)
        
        # Should not fail, directory should be created
        assert temp_dir.exists()

    @patch('pycompgen.cache.get_logger')
    def test_save_completions_logging(self, mock_get_logger, temp_dir):
        """Test that completion saving is logged."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        completions = [
            GeneratedCompletion(
                package_name="test-package",
                completion_type=CompletionType.CLICK,
                content="test content",
                commands=["test-command"]
            )
        ]
        
        save_completions(completions, temp_dir)
        
        # Should log the saving operation
        mock_logger.info.assert_called()


class TestSaveSourceScript:
    """Test saving the source script."""

    def test_save_source_script_success(self, temp_dir):
        """Test successful source script saving."""
        # Create some completion files
        (temp_dir / "package1.sh").write_text("completion 1")
        (temp_dir / "package2.sh").write_text("completion 2")
        
        result = save_source_script(temp_dir)
        
        assert result == temp_dir / "completions.sh"
        assert result.exists()
        
        content = result.read_text()
        assert "source" in content
        assert "package1.sh" in content
        assert "package2.sh" in content

    def test_save_source_script_empty_directory(self, temp_dir):
        """Test source script with empty directory."""
        result = save_source_script(temp_dir)
        
        assert result == temp_dir / "completions.sh"
        assert result.exists()
        
        content = result.read_text()
        # Should have header but no source lines
        assert "# Generated by pycompgen" in content

    def test_save_source_script_creates_directory(self, temp_dir):
        """Test that directory is created if it doesn't exist."""
        cache_dir = temp_dir / "new-cache-dir"
        assert not cache_dir.exists()
        
        result = save_source_script(cache_dir)
        
        assert cache_dir.exists()
        assert result.exists()

    @patch('pycompgen.cache.get_logger')
    def test_save_source_script_logging(self, mock_get_logger, temp_dir):
        """Test that source script creation is logged."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        save_source_script(temp_dir)
        
        # Should log the creation
        mock_logger.info.assert_called()


class TestGenerateSourceScript:
    """Test source script generation."""

    def test_generate_source_script_with_files(self, temp_dir):
        """Test generating source script with completion files."""
        # Create completion files
        (temp_dir / "package1.sh").write_text("completion 1")
        (temp_dir / "package2.sh").write_text("completion 2")
        (temp_dir / "other.txt").write_text("not a completion")  # Should be ignored
        
        result = generate_source_script(temp_dir)
        
        assert "# Generated by pycompgen" in result
        assert f"source {temp_dir / 'package1.sh'}" in result
        assert f"source {temp_dir / 'package2.sh'}" in result
        assert "other.txt" not in result

    def test_generate_source_script_empty_directory(self, temp_dir):
        """Test generating source script with no completion files."""
        result = generate_source_script(temp_dir)
        
        assert "# Generated by pycompgen" in result
        assert "source" not in result.split('\n')[1:]  # No source lines after header

    def test_generate_source_script_nonexistent_directory(self, tmp_path):
        """Test generating source script for nonexistent directory."""
        nonexistent_dir = tmp_path / "nonexistent" / "directory"
        
        result = generate_source_script(nonexistent_dir)
        
        assert "# Generated by pycompgen" in result
        assert "source" not in result.split('\n')[1:]  # No source lines after header

    def test_generate_source_script_sorted_output(self, temp_dir):
        """Test that source script files are sorted."""
        # Create files in non-alphabetical order
        (temp_dir / "z-package.sh").write_text("completion z")
        (temp_dir / "a-package.sh").write_text("completion a")
        (temp_dir / "m-package.sh").write_text("completion m")
        
        result = generate_source_script(temp_dir)
        
        lines = result.split('\n')
        source_lines = [line for line in lines if line.startswith('source')]
        
        # Should be sorted alphabetically
        assert source_lines[0].endswith('a-package.sh')
        assert source_lines[1].endswith('m-package.sh')
        assert source_lines[2].endswith('z-package.sh')

    def test_generate_source_script_header_format(self, temp_dir):
        """Test source script header format."""
        result = generate_source_script(temp_dir)
        
        lines = result.split('\n')
        assert lines[0].startswith('# Generated by pycompgen')
        assert lines[1].startswith('# This file sources all completion scripts')
        assert lines[2] == ''  # Empty line after header

    def test_generate_source_script_executable_comment(self, temp_dir):
        """Test that source script includes usage instructions."""
        result = generate_source_script(temp_dir)
        
        assert "Add this to your shell config:" in result
        assert "source" in result


class TestIntegrationWithMockEnv:
    """Integration tests with mocked environment."""

    def test_full_cache_workflow(self, tmp_path):
        """Test complete cache workflow with mocked file operations."""
        test_cache = tmp_path / "test" / "cache"
        test_cache.mkdir(parents=True)
        
        with patch.dict(os.environ, {"XDG_CACHE_HOME": str(test_cache)}):
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                with patch('pathlib.Path.exists', return_value=False) as mock_exists:
                    with patch('pathlib.Path.write_text') as mock_write:
                        with patch('pathlib.Path.glob') as mock_glob:
                            # Setup mocks
                            mock_glob.return_value = [test_cache / "pycompgen" / "package1.sh"]
                            
                            # Create completion
                            completion = GeneratedCompletion(
                                package_name="test-package",
                                completion_type=CompletionType.CLICK,
                                content="test completion content",
                                commands=["test-command"]
                            )
                            
                            # Test cache directory resolution
                            cache_dir = get_cache_dir()
                            assert cache_dir == test_cache / "pycompgen"
                            
                            # Test saving completions
                            save_completions([completion], cache_dir)
                            
                            # Verify directory creation was attempted
                            mock_mkdir.assert_called()
        
        # Verify file writing was attempted
        mock_write.assert_called()
        
        # Test source script generation
        source_script_path = save_source_script(cache_dir)
        
        assert source_script_path == cache_dir / "completions.sh"