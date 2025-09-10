from unittest.mock import Mock, patch
import os

from pycompgen.cache import (
    get_cache_dir,
    save_completions,
)
from pycompgen.models import GeneratedCompletion, CompletionType, Shell


class TestGetCacheDir:
    """Test cache directory resolution."""

    def test_get_cache_dir_xdg_cache_home(self, tmp_path):
        """Test cache directory with XDG_CACHE_HOME set."""
        custom_cache = tmp_path / "custom" / "cache"
        custom_cache.mkdir(parents=True)

        with patch.dict(os.environ, {"XDG_CACHE_HOME": str(custom_cache)}):
            result = get_cache_dir()
            assert result == custom_cache

    def test_get_cache_dir_fallback(self, tmp_path):
        """Test cache directory fallback to ~/.cache."""
        mock_home = tmp_path / "home" / "user"
        mock_home.mkdir(parents=True)

        with patch.dict(os.environ, {}, clear=True):
            with patch("pathlib.Path.home", return_value=mock_home):
                result = get_cache_dir()
                assert result == mock_home / ".cache"

    def test_get_cache_dir_empty_xdg(self, tmp_path):
        """Test cache directory with empty XDG_CACHE_HOME."""
        mock_home = tmp_path / "home" / "user"
        mock_home.mkdir(parents=True)

        with patch.dict(os.environ, {"XDG_CACHE_HOME": ""}):
            with patch("pathlib.Path.home", return_value=mock_home):
                result = get_cache_dir()
                assert result == mock_home / ".cache"


class TestSaveCompletions:
    """Test saving completions to cache."""

    def test_save_completions_success(self, temp_dir):
        """Test successful completion saving."""
        completions = [
            GeneratedCompletion(
                package_name="test-package",
                completion_type=CompletionType.CLICK,
                content="test completion content",
                command="test-command",
                shell=Shell.BASH,
            ),
            GeneratedCompletion(
                package_name="another-package",
                completion_type=CompletionType.ARGCOMPLETE,
                content="another completion content",
                command="another-command",
                shell=Shell.ZSH,
            ),
        ]

        # Mock the cache directory to use temp_dir
        with patch("pycompgen.cache.get_cache_dir", return_value=temp_dir):
            save_completions(completions, temp_dir)

            # Check that files were created in shell-specific directories
            assert (temp_dir / "pycompgen" / "bash" / "test-command.sh").exists()
            assert (temp_dir / "pycompgen" / "zsh" / "another-command.zsh").exists()

            # Check content
            content1 = (temp_dir / "pycompgen" / "bash" / "test-command.sh").read_text()
            assert "test completion content" in content1

            content2 = (
                temp_dir / "pycompgen" / "zsh" / "another-command.zsh"
            ).read_text()
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
                command="test-command",
                shell=Shell.BASH,
            )
        ]

        # Mock the cache directory to use cache_dir
        with patch("pycompgen.cache.get_cache_dir", return_value=cache_dir):
            save_completions(completions, cache_dir)

            assert cache_dir.exists()
            assert (cache_dir / "pycompgen" / "bash" / "test-command.sh").exists()

    def test_save_completions_no_overwrite_without_force(self, temp_dir):
        """Test that existing files are not overwritten without force."""
        # Create the shell-specific directory and file structure
        bash_dir = temp_dir / "pycompgen" / "bash"
        bash_dir.mkdir(parents=True)
        completion_file = bash_dir / "test-command.sh"
        completion_file.write_text("original content")
        original_mtime = completion_file.stat().st_mtime

        completions = [
            GeneratedCompletion(
                package_name="test-package",
                completion_type=CompletionType.CLICK,
                content="new content",
                command="test-command",
                shell=Shell.BASH,
            )
        ]

        # Mock the cache directory to use temp_dir
        with patch("pycompgen.cache.get_cache_dir", return_value=temp_dir):
            save_completions(completions, temp_dir, force=False)

            # File should not be overwritten
            assert completion_file.read_text() == "original content"
            assert completion_file.stat().st_mtime == original_mtime

    def test_save_completions_overwrite_with_force(self, temp_dir):
        """Test that existing files are overwritten with force."""
        # Create the shell-specific directory and file structure
        bash_dir = temp_dir / "pycompgen" / "bash"
        bash_dir.mkdir(parents=True)
        completion_file = bash_dir / "test-command.sh"
        completion_file.write_text("original content")

        completions = [
            GeneratedCompletion(
                package_name="test-package",
                completion_type=CompletionType.CLICK,
                content="new content",
                command="test-command",
                shell=Shell.BASH,
            )
        ]

        # Mock the cache directory to use temp_dir
        with patch("pycompgen.cache.get_cache_dir", return_value=temp_dir):
            save_completions(completions, temp_dir, force=True)

            # File should be overwritten
            assert "new content" in completion_file.read_text()

    def test_save_completions_empty_list(self, temp_dir):
        """Test saving empty completion list."""
        # Mock the cache directory to use temp_dir
        with patch("pycompgen.cache.get_cache_dir", return_value=temp_dir):
            save_completions([], temp_dir)

            # Should not fail, directory should exist
            assert temp_dir.exists()

    @patch("pycompgen.cache.get_logger")
    def test_save_completions_logging(self, mock_get_logger, temp_dir):
        """Test that completion saving is logged."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        completions = [
            GeneratedCompletion(
                package_name="test-package",
                completion_type=CompletionType.CLICK,
                content="test content",
                command="test-command",
                shell=Shell.BASH,
            )
        ]

        # Mock the cache directory to use temp_dir
        with patch("pycompgen.cache.get_cache_dir", return_value=temp_dir):
            save_completions(completions, temp_dir)

            # Should log the saving operation
            mock_logger.info.assert_called()


class TestIntegrationWithMockEnv:
    """Integration tests with mocked environment."""

    def test_full_cache_workflow(self, tmp_path):
        """Test complete cache workflow with mocked file operations."""
        test_cache = tmp_path / "test" / "cache"
        test_cache.mkdir(parents=True)

        with patch.dict(os.environ, {"XDG_CACHE_HOME": str(test_cache)}):
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                with patch("pathlib.Path.exists", return_value=False):
                    with patch("pathlib.Path.write_text") as mock_write:
                        with patch("pathlib.Path.glob") as mock_glob:
                            # Setup mocks
                            mock_glob.return_value = [
                                test_cache / "pycompgen" / "bash" / "package1.sh"
                            ]

                            # Create completion
                            completion = GeneratedCompletion(
                                package_name="test-package",
                                completion_type=CompletionType.CLICK,
                                content="test completion content",
                                command="test-command",
                                shell=Shell.BASH,
                            )

                            # Test cache directory resolution
                            cache_dir = get_cache_dir()
                            assert cache_dir == test_cache

                            # Test saving completions
                            save_completions([completion], cache_dir)

                            # Verify directory creation was attempted
                            mock_mkdir.assert_called()

        # Verify file writing was attempted
        mock_write.assert_called()
