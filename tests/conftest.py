"""Pytest configuration and shared fixtures for Importobot test suite.

This module provides common configuration and makes shared fixtures available
across all test modules in the Importobot project. It follows pytest best
practices for organizing test utilities and fixtures.
"""

import shutil
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from importobot import telemetry
from tests.business_requirements import BusinessRequirements

# Import shared fixtures to make them available globally
try:
    # Import helper functions
    from tests.fixtures.format_detection_fixtures import (
        ConfidenceTestScenarios,
        FormatTestDataGenerator,
        FormatTestScenarios,
        all_supported_formats,
        ambiguous_examples,
        complex_format_examples,
        confidence_test_scenarios,
        confidence_thresholds,
        format_complexity_levels,
        format_test_generator,
        format_test_scenarios,
        malformed_examples,
        minimal_format_examples,
        perfect_evidence_scenarios,
        performance_dataset_sizes,
        standard_format_examples,
        validate_confidence_bounds,
        validate_format_detection_result,
        validate_performance_metrics,
        weak_evidence_scenarios,
        zero_evidence_scenarios,
    )

    # Make helper functions available at package level
    __all__ = [
        "ConfidenceTestScenarios",
        # Helper classes
        "FormatTestDataGenerator",
        "FormatTestScenarios",
        "all_supported_formats",
        "ambiguous_examples",
        "benchmark",
        "cleanup_test_files",
        "complex_format_examples",
        "confidence_test_scenarios",
        "confidence_thresholds",
        "format_complexity_levels",
        # New fixtures
        "format_test_generator",
        "format_test_scenarios",
        "malformed_examples",
        "minimal_format_examples",
        "perfect_evidence_scenarios",
        "performance_dataset_sizes",
        "sample_zephyr_json",
        "standard_format_examples",
        "telemetry_events",
        # Original fixtures
        "temp_dir",
        "validate_confidence_bounds",
        # Helper functions
        "validate_format_detection_result",
        "validate_performance_metrics",
        "weak_evidence_scenarios",
        "zero_evidence_scenarios",
    ]
except ImportError:
    # Fixtures module not available, skip imports
    pass


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

    This fixture uses isolated temporary directories and proper cleanup tracking
    to prevent tests from leaving behind artifacts.
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
            except (OSError, PermissionError) as e:
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


# Additional fixtures and configuration for testing
@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration values."""
    return {
        "timeout": 30,  # Default timeout for tests in seconds
        "retry_count": 3,  # Number of retries for flaky tests
        "performance_multiplier": 1.0,  # Multiplier for performance thresholds
    }


@pytest.fixture(autouse=True)
def configure_timeout(request, test_config):
    """Automatically apply timeout to all tests."""
    # Set timeout based on test configuration
    timeout = test_config["timeout"]

    # Mark test with timeout if it doesn't already have one
    if "timeout" not in request.node.keywords:
        request.node.add_marker(pytest.mark.timeout(timeout))


@pytest.fixture(scope="session")
def business_requirements():
    """Load business requirements for testing."""
    br = BusinessRequirements()
    return {
        "format_confidence": {
            "standard": br.MIN_FORMAT_CONFIDENCE_STANDARD,
            "high_quality": br.MIN_FORMAT_CONFIDENCE_HIGH_QUALITY,
            "perfect_match": br.MIN_FORMAT_CONFIDENCE_PERFECT_MATCH,
            "generic": br.MIN_GENERIC_FORMAT_CONFIDENCE,
        },
        "bayesian_confidence": {
            "strong_evidence_min": br.STRONG_EVIDENCE_MIN_CONFIDENCE,
            "zero_evidence_max": br.ZERO_EVIDENCE_MAX_CONFIDENCE,
            "zero_evidence_tolerance": br.ZERO_EVIDENCE_TOLERANCE,
        },
        "performance": {
            "max_format_detection_time": br.MAX_FORMAT_DETECTION_TIME,
            "max_confidence_calculation_time": br.MAX_CONFIDENCE_CALCULATION_TIME,
            "min_bulk_processing_speedup": br.MIN_BULK_PROCESSING_SPEEDUP,
            "max_memory_usage_large_dataset": br.MAX_MEMORY_USAGE_LARGE_DATASET,
        },
    }
