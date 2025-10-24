"""Test fixtures for developer tooling scripts.

This module provides test data samples for analysis scripts without requiring
them to import test modules, which avoids type checking issues.
"""

from typing import Any

try:
    from tests.unit.medallion.bronze import (  # type: ignore
        test_format_detection_integration,
    )

    TestFormatDetectionIntegration = (
        test_format_detection_integration.TestFormatDetectionIntegration
    )
except ImportError:  # pragma: no cover - developer tooling dependency
    # Default implementation if test utils aren't available
    def create_test_case_base(test_id: int, title: str, refs: str) -> dict[str, Any]:
        """Default test case base creator."""
        return {
            "id": test_id,
            "title": title,
            "refs": refs,
            "custom_preconds": "Test case prerequisites",
            "custom_steps": [
                {
                    "step": f"Step {i + 1}",
                    "expected": f"Expected result {i + 1}",
                }
                for i in range(2)
            ],
        }

    # Default test data if integration test isn't available
    TEST_DATA_SAMPLES: dict[str, dict[str, Any]] = {}
else:
    # Import test data from integration tests to avoid duplication
    test_instance = TestFormatDetectionIntegration()
    test_instance.setUp()
    TEST_DATA_SAMPLES = test_instance.test_data_samples
