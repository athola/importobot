"""pytest configuration and fixtures."""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_zephyr_json():
    """Sample Zephyr JSON data for testing."""
    return {
        "tests": [
            {
                "name": "Sample Test Case",
                "description": "A sample test case description",
                "steps": [
                    {
                        "action": "Do something",
                        "expectedResult": "Something happens",
                    }
                ],
            }
        ]
    }


@pytest.fixture(autouse=True)
def cleanup_test_files(tmp_path):
    """Automatically clean up any test-generated files after each test.

    This fixture ensures that tests don't leave behind artifacts by using
    isolated temporary directories and proper cleanup tracking.
    """
    _ = tmp_path  # Mark as used to avoid linting warning
    # Track files that should be cleaned up
    cleanup_files = []

    # Store the cleanup list in the fixture for tests to access
    def register_file_for_cleanup(file_path):
        """Register a file to be cleaned up after the test."""
        cleanup_files.append(Path(file_path))

    # Make cleanup function available to tests through the request context
    yield register_file_for_cleanup

    # Clean up tracked files
    for file_path in cleanup_files:
        if file_path.exists():
            try:
                if file_path.is_file():
                    file_path.unlink()
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
            except (OSError, IOError, PermissionError) as e:
                # Log cleanup errors but don't fail the test
                print(f"Warning: Could not clean up {file_path}: {e}")
