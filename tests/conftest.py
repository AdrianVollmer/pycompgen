import pytest
from pathlib import Path
from unittest.mock import patch
import tempfile
import os

from pycompgen.models import (
    InstalledPackage,
    CompletionPackage,
    PackageManager,
    CompletionType,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_uv_package():
    """Mock uv tool package."""
    return InstalledPackage(
        name="test-package",
        path=Path("/fake/path/to/venv"),
        manager=PackageManager.UV_TOOL,
        version="1.0.0",
    )


@pytest.fixture
def mock_pipx_package():
    """Mock pipx package."""
    return InstalledPackage(
        name="pipx-package",
        path=Path("/fake/pipx/venv"),
        manager=PackageManager.PIPX,
        version="2.0.0",
    )


@pytest.fixture
def mock_click_completion_package(mock_uv_package):
    """Mock completion package with click support."""
    return CompletionPackage(
        package=mock_uv_package,
        completion_type=CompletionType.CLICK,
        commands=["test-command"],
    )


@pytest.fixture
def mock_argcomplete_completion_package(mock_pipx_package):
    """Mock completion package with argcomplete support."""
    return CompletionPackage(
        package=mock_pipx_package,
        completion_type=CompletionType.ARGCOMPLETE,
        commands=["argcomplete-command"],
    )


@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    with patch.dict(
        os.environ,
        {
            "XDG_CACHE_HOME": "/tmp/test-cache",
            "XDG_STATE_HOME": "/tmp/test-state",
            "HOME": "/tmp/test-home",
        },
    ):
        yield
