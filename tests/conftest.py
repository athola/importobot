"""pytest configuration and fixtures."""

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
def cleanup_test_files():
    """Automatically clean up any test-generated files after each test.

    This fixture ensures that tests don't leave behind artifacts by
    tracking files before and
    after each test execution.
    """
    # Store initial state of common test file types
    initial_files = set(Path(".").glob("*.robot")) | set(Path(".").glob("*.json"))

    yield

    # Clean up after test
    final_files = set(Path(".").glob("*.robot")) | set(Path(".").glob("*.json"))
    generated_files = final_files - initial_files

    for file in generated_files:
        if file.exists():
            try:
                file.unlink()
            except (OSError, IOError):
                pass  # Ignore errors during cleanup
