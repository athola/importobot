"""pytest configuration and fixtures."""

import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

import pytest

from importobot import telemetry


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
    cleanup_files = []

    def register_file_for_cleanup(file_path):
        """Register a file to be cleaned up after the test."""
        cleanup_files.append(Path(file_path))

    yield register_file_for_cleanup

    for file_path in cleanup_files:
        if file_path.exists():
            try:
                if file_path.is_file():
                    file_path.unlink()
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
            except (OSError, IOError, PermissionError) as e:
                print(f"Warning: Could not clean up {file_path}: {e}")


@pytest.fixture
def telemetry_events(monkeypatch):
    """Capture telemetry events emitted during a test."""
    monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
    monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_SAMPLE_DELTA", "0")
    monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_INTERVAL_SECONDS", "0")
    telemetry.reset_telemetry_client()
    events = []

    def _exporter(event_name, payload):
        events.append((event_name, payload))

    telemetry.clear_telemetry_exporters()
    telemetry.register_telemetry_exporter(_exporter)

    yield events

    telemetry.reset_telemetry_client()


@pytest.fixture
def benchmark():
    """Provide simple benchmark fixture for performance tests."""

    def _benchmark(func: Callable[[], Any], *, iterations: int = 1) -> dict[str, Any]:
        """Run function and return timing/result information."""
        start = time.perf_counter()
        result = None
        for _ in range(iterations):
            result = func()
        elapsed = (time.perf_counter() - start) / max(iterations, 1)
        return {"elapsed": elapsed, "result": result}

    return _benchmark
