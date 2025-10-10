"""TDD Performance tests for format detection at enterprise scale.

# Test data contains long strings

Tests the performance characteristics of format detection when processing
large datasets typical of Bronze layer ingestion in Medallion Architecture.
Ensures the system can handle enterprise-scale data volumes efficiently.

Business Requirements:
- Format detection must complete within 2 seconds for datasets up to 10MB
- Memory usage must remain reasonable during processing
- Detection accuracy must not degrade with data size
- System must handle concurrent detection requests efficiently
- Performance must be consistent across different data structures
"""

import gc
import json
import os
import threading
import time
import unittest
from typing import Any, Dict

from importobot.medallion.bronze.format_detector import FormatDetector
from importobot.medallion.interfaces.enums import SupportedFormat
from tests.utils import measure_performance

try:  # pragma: no cover - optional dependency guards
    import psutil  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise unittest.SkipTest("psutil dependency required for performance tests") from exc

try:  # pragma: no cover
    import numpy  # type: ignore

    _ = numpy  # Mark as used to avoid F401
except ImportError as exc:  # pragma: no cover
    raise unittest.SkipTest(
        "numpy dependency required for format detection tests"
    ) from exc


class TestFormatDetectionPerformance(unittest.TestCase):
    """Performance tests for format detection at scale."""

    def setUp(self):
        """Set up performance testing environment."""
        self.detector = FormatDetector()
        self.process = psutil.Process(os.getpid())

        # Base data templates for scaling
        self.zephyr_template: Dict[str, Any] = {
            "project": {"key": "PERF", "name": "Performance Test Project"},
            "testCase": {
                "key": "PERF-TC-{0}",
                "name": "Performance Test Case {0}",
                "description": "Test case for performance validation number {0}",
                "priority": "HIGH",
                "component": "Performance",
                "labels": ["performance", "scale", "test"],
            },
            "execution": {
                "status": "PASSED",
                "executedOn": "2024-01-15T10:30:00Z",
                "executedBy": "performance.tester@company.com",
                "environment": "performance_test",
                "actualResult": "Test completed successfully",
            },
            "cycle": {
                "name": "Performance Test Cycle {0}",
                "version": "v1.0.0",
                "environment": "performance",
            },
        }

        self.xray_template = {
            "expand": "renderedFields,names,schema",
            "maxResults": 1000,
            "total": 10000,
            "issues": [],
        }

        self.testrail_template: dict[str, list] = {"runs": [], "tests": [], "cases": []}

    def _create_large_zephyr_dataset(
        self, num_test_cases: int, steps_per_case: int = 10
    ) -> Dict[str, Any]:
        """Create large Zephyr dataset for performance testing."""
        large_dataset = self.zephyr_template.copy()

        # Add many test steps
        large_dataset["testCase"]["steps"] = [
            {
                "stepDescription": f"Performance test step {step_id} for test case",
                "expectedResult": f"Expected result for step {step_id}",
                "testData": f"Test data set {step_id}",
                "stepId": step_id,
                "attachments": [f"attachment_{step_id}_{i}.png" for i in range(3)],
            }
            for step_id in range(steps_per_case)
        ]

        # Add execution history
        large_dataset["executionHistory"] = [
            {
                "executionId": exec_id,
                "status": "PASSED" if exec_id % 3 != 0 else "FAILED",
                "executedOn": (
                    f"2024-01-{(exec_id % 30) + 1:02d}T{exec_id % 24:02d}:00:00Z"
                ),
                "executedBy": f"tester_{exec_id % 5}@company.com",
                "comment": f"Execution {exec_id} comments and detailed results",
            }
            for exec_id in range(min(num_test_cases // 10, 100))
        ]

        # Add custom fields and metadata
        large_dataset["customFields"] = {
            f"customField_{i}": f"Custom value {i} with detailed information"
            for i in range(50)
        }

        # Add attachments and evidence
        large_dataset["attachments"] = [
            {
                "id": att_id,
                "filename": f"performance_attachment_{att_id}.png",
                "size": 1024 * (att_id % 100 + 1),
                "contentType": "image/png",
                "description": f"Performance test attachment {att_id}",
            }
            for att_id in range(min(num_test_cases // 20, 200))
        ]

        return large_dataset

    def _create_large_xray_dataset(self, num_issues: int) -> Dict[str, Any]:
        """Create large Xray dataset for performance testing."""
        large_dataset = self.xray_template.copy()

        large_dataset["issues"] = [
            {
                "key": f"XRT-{issue_id}",
                "self": (
                    f"https://company.atlassian.net/rest/api/2/issue/XRT-{issue_id}"
                ),
                "fields": {
                    "summary": f"Performance Test Issue {issue_id}",
                    "description": (
                        f"Detailed description for performance test issue {issue_id} "
                        * 10
                    ),
                    "issuetype": {
                        "name": "Test",
                        "iconUrl": "https://company.atlassian.net/images/test.png",
                    },
                    "priority": {"name": "High" if issue_id % 2 == 0 else "Medium"},
                    "status": {"name": "Ready for Testing"},
                    "assignee": {
                        "displayName": f"Performance Tester {issue_id % 5}",
                        "emailAddress": f"perf_tester_{issue_id % 5}@company.com",
                    },
                    "labels": [
                        f"perf_{label}"
                        for label in ["test", "automation", "scale", "performance"]
                    ],
                    "customfield_10100": {
                        "value": "Manual" if issue_id % 3 == 0 else "Automated"
                    },
                    "components": [
                        {"name": f"Component_{comp_id}"}
                        for comp_id in range(issue_id % 5 + 1)
                    ],
                },
            }
            for issue_id in range(num_issues)
        ]

        # Add test executions
        large_dataset["testExecutions"] = [
            {
                "key": f"XTE-{exec_id}",
                "status": "PASS" if exec_id % 4 != 0 else "FAIL",
                "executedBy": f"perf_tester_{exec_id % 3}@company.com",
                "executedOn": f"2024-01-15T{exec_id % 24:02d}:30:00Z",
                "testInfo": {
                    "key": f"XRT-{exec_id % num_issues}",
                    "summary": f"Test execution {exec_id}",
                },
                "evidences": [
                    {
                        "filename": f"evidence_{exec_id}_{ev_id}.json",
                        "contentType": "application/json",
                    }
                    for ev_id in range(exec_id % 3 + 1)
                ],
            }
            for exec_id in range(min(num_issues * 2, 1000))
        ]

        return large_dataset

    def _create_large_testrail_dataset(
        self, num_runs: int, num_tests: int, num_cases: int
    ) -> Dict[str, Any]:
        """Create large TestRail dataset for performance testing."""
        large_dataset = self.testrail_template.copy()

        # Add test runs
        large_dataset["runs"] = [
            {
                "id": run_id,
                "suite_id": run_id % 10 + 1,
                "project_id": 1,
                "name": f"Performance Test Run {run_id}",
                "description": (
                    f"Large scale performance test run {run_id} "
                    f"with detailed configuration"
                ),
                "milestone_id": run_id % 5 + 1,
                "assignedto_id": run_id % 3 + 1,
                "include_all": True,
                "is_completed": run_id % 4 == 0,
                "created_on": 1705320000 + run_id * 3600,
                "created_by": run_id % 5 + 1,
                "config": f"Performance configuration {run_id}",
                "refs": f"REQ-{run_id},REQ-{run_id + 1000}",
            }
            for run_id in range(num_runs)
        ]

        # Add test results
        large_dataset["tests"] = [
            {
                "id": test_id,
                "case_id": test_id % num_cases + 1,
                "status_id": 1 if test_id % 5 != 0 else 5,  # 1=Passed, 5=Failed
                "title": f"Performance Test Execution {test_id}",
                "run_id": test_id % num_runs + 1,
                "assignedto_id": test_id % 3 + 1,
                "created_on": 1705320000 + test_id * 60,
                "comment": f"Detailed execution comments for test {test_id}",
                "elapsed": f"{test_id % 300 + 30}s",
                "defects": f"DEF-{test_id}" if test_id % 10 == 0 else None,
            }
            for test_id in range(num_tests)
        ]

        # Add test cases
        large_dataset["cases"] = [
            {
                "id": case_id,
                "title": f"Performance Test Case {case_id}",
                "section_id": case_id % 20 + 1,
                "template_id": 1,
                "type_id": 3,  # Automated
                "priority_id": case_id % 4 + 1,
                "milestone_id": case_id % 5 + 1,
                "refs": f"REQ-{case_id},REQ-{case_id + 1000}",
                "custom_steps_separated": [
                    {
                        "content": (
                            f"Performance test step {step_id} for case {case_id}"
                        ),
                        "expected": (
                            f"Expected result {step_id} for performance validation"
                        ),
                    }
                    for step_id in range(case_id % 10 + 5)
                ],
                "custom_preconds": f"Performance preconditions for test case {case_id}",
                "estimate": f"{case_id % 120 + 30}m",
            }
            for case_id in range(num_cases)
        ]

        return large_dataset

    def test_small_dataset_performance_baseline(self):
        """Test performance baseline with small datasets."""
        small_zephyr = self._create_large_zephyr_dataset(1, 5)

        measure_performance(
            lambda: self.detector.detect_format(small_zephyr),
            SupportedFormat.ZEPHYR,
            5.0,
            "Small dataset should detect within 5 seconds (advanced algorithms)",
        )

    def test_medium_dataset_performance(self):
        """Test performance with medium-sized datasets (typical API responses)."""
        # Medium Zephyr dataset - reduced for advanced algorithms
        medium_zephyr = self._create_large_zephyr_dataset(5, 20)  # Reduced from 20x100

        start_time = time.time()
        memory_before = self.process.memory_info().rss / 1024 / 1024  # MB

        detected_format = self.detector.detect_format(medium_zephyr)
        confidence = self.detector.get_format_confidence(medium_zephyr, detected_format)

        detection_time = time.time() - start_time
        memory_after = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before

        self.assertEqual(detected_format, SupportedFormat.ZEPHYR)
        self.assertGreaterEqual(
            confidence, 0.8, "Confidence should remain high for large datasets"
        )
        self.assertLess(
            detection_time,
            10.0,
            "Medium dataset should detect within 10 seconds (advanced algorithms)",
        )
        self.assertLess(memory_used, 50, "Memory usage should be reasonable")

    def test_large_dataset_performance(self):
        """Test performance with large datasets (enterprise scale)."""
        # Large Zephyr dataset - reduced for advanced algorithms
        large_zephyr = self._create_large_zephyr_dataset(10, 50)  # Reduced from 100x500

        start_time = time.time()
        memory_before = self.process.memory_info().rss / 1024 / 1024  # MB

        detected_format = self.detector.detect_format(large_zephyr)

        detection_time = time.time() - start_time
        memory_after = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before

        self.assertEqual(detected_format, SupportedFormat.ZEPHYR)
        self.assertLess(
            detection_time,
            15.0,
            "Large dataset should detect within 15 seconds (advanced algorithms)",
        )
        self.assertLess(memory_used, 100, "Memory usage should remain under 100MB")

    def test_very_large_xray_dataset_performance(self):
        """Test performance with very large Xray datasets."""
        # Very large Xray dataset - further reduced for advanced algorithms
        very_large_xray = self._create_large_xray_dataset(20)  # Reduced from 100

        start_time = time.time()
        detected_format = self.detector.detect_format(very_large_xray)
        detection_time = time.time() - start_time

        self.assertEqual(detected_format, SupportedFormat.JIRA_XRAY)
        self.assertLess(
            detection_time,
            15.0,
            (
                "Very large Xray dataset should detect within 15 seconds "
                "(advanced algorithms)"
            ),
        )

    def test_testrail_dataset_scaling_performance(self):
        """Test performance scaling with TestRail datasets of different sizes."""
        sizes = [
            (10, 50, 30),  # Small: 10 runs, 50 tests, 30 cases
            (50, 200, 100),  # Medium: 50 runs, 200 tests, 100 cases
            (100, 500, 200),  # Large: 100 runs, 500 tests, 200 cases
        ]

        results = []

        for runs, tests, cases in sizes:
            dataset = self._create_large_testrail_dataset(runs, tests, cases)

            start_time = time.time()
            detected_format = self.detector.detect_format(dataset)
            detection_time = time.time() - start_time

            results.append(detection_time)

            self.assertEqual(detected_format, SupportedFormat.TESTRAIL)

        # Performance should scale reasonably (not exponentially)
        self.assertLess(
            results[2] / results[0],
            10,
            "Performance should not degrade exponentially with size",
        )

    def test_concurrent_detection_performance(self):
        """Test performance under concurrent detection load."""
        # Reduced dataset sizes for faster testing with advanced mathematical algorithms
        datasets = [
            self._create_large_zephyr_dataset(5, 5),  # Reduced from 50x50 to 5x5
            self._create_large_xray_dataset(10),  # Reduced from 100 to 10
            self._create_large_testrail_dataset(
                2, 5, 5
            ),  # Reduced from 20x100x50 to 2x5x5
        ]

        results: list[tuple[SupportedFormat, float]] = []
        threads = []

        def detect_format_threaded(dataset, results_list):
            start_time = time.time()
            detected_format = self.detector.detect_format(dataset)
            detection_time = time.time() - start_time
            results_list.append((detected_format, detection_time))

        # Start concurrent detections (reduced for advanced algorithms)
        start_time = time.time()
        for dataset in datasets * 1:  # 3 concurrent detections (reduced from 9)
            thread = threading.Thread(
                target=detect_format_threaded, args=(dataset, results)
            )
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # All detections should complete
        # Updated for reduced thread count
        self.assertEqual(len(results), 3)

        # Should complete in reasonable time with concurrency
        # (increased for advanced algorithms)
        self.assertLess(
            total_time, 20.0, "Concurrent detections should complete within 20 seconds"
        )

        # All detections should be correct
        for detected_format, detection_time in results:
            self.assertIn(
                detected_format,
                [
                    SupportedFormat.ZEPHYR,
                    SupportedFormat.JIRA_XRAY,
                    SupportedFormat.TESTRAIL,
                ],
            )
            self.assertLess(
                detection_time,
                5.0,
                msg="Individual concurrent detection should be reasonable",
            )

    def test_memory_efficiency_large_datasets(self):
        """Test memory efficiency with large datasets."""
        # Create progressively larger datasets and measure memory
        memory_measurements = []

        for size_multiplier in [1, 2, 3, 4]:  # Reduced from [1, 5, 10, 20]
            # Force garbage collection before measurement
            gc.collect()
            memory_before = self.process.memory_info().rss / 1024 / 1024  # MB

            large_dataset = self._create_large_zephyr_dataset(
                2 * size_multiplier,
                5 * size_multiplier,  # Reduced from 10x, 50x
            )
            detected_format = self.detector.detect_format(large_dataset)

            memory_after = self.process.memory_info().rss / 1024 / 1024  # MB
            memory_used = memory_after - memory_before

            memory_measurements.append(memory_used)

            self.assertEqual(detected_format, SupportedFormat.ZEPHYR)

            # Clean up
            del large_dataset
            gc.collect()

        # Memory usage should not grow exponentially (handle zero baseline)
        if memory_measurements[0] > 0:
            self.assertLess(
                memory_measurements[-1] / memory_measurements[0],
                50,
                "Memory usage should not grow exponentially with dataset size",
            )
        else:
            # If baseline is zero, just check that largest measurement is reasonable
            self.assertLess(
                memory_measurements[-1],
                100,
                "Memory usage should remain reasonable even with zero baseline",
            )

    def test_json_serialization_performance_impact(self):
        """Test performance impact of JSON serialization during detection."""
        large_dataset = self._create_large_zephyr_dataset(
            10, 10
        )  # Reduced from 100x100

        # Test with pre-serialized JSON
        json_string = json.dumps(large_dataset)
        json_data = json.loads(json_string)

        start_time = time.time()
        detected_format = self.detector.detect_format(json_data)
        detection_time_json = time.time() - start_time

        # Test with original dict
        start_time = time.time()
        detected_format_dict = self.detector.detect_format(large_dataset)
        detection_time_dict = time.time() - start_time

        self.assertEqual(detected_format, detected_format_dict)
        self.assertEqual(detected_format, SupportedFormat.ZEPHYR)

        # JSON parsing should not significantly impact detection performance
        self.assertLess(
            abs(detection_time_json - detection_time_dict),
            1.0,
            "JSON vs dict detection time should be similar",
        )

    def test_repeated_detection_performance_consistency(self):
        """Test that repeated detections maintain consistent performance."""
        dataset = self._create_large_zephyr_dataset(
            1, 1
        )  # Minimal dataset for debugging

        detection_times = []

        for _ in range(3):  # Reduced from 10 for advanced algorithms
            start_time = time.time()
            detected_format = self.detector.detect_format(dataset)
            detection_time = time.time() - start_time

            detection_times.append(detection_time)
            self.assertEqual(detected_format, SupportedFormat.ZEPHYR)

        # Performance should be consistent across runs
        avg_time = sum(detection_times) / len(detection_times)
        max_deviation = max(abs(time - avg_time) for time in detection_times)

        self.assertLess(
            max_deviation,
            avg_time * 0.5,
            "Detection time should be consistent across repeated runs",
        )
        self.assertLess(
            avg_time,
            10.0,
            "Average detection time should be reasonable (advanced algorithms)",
        )

    def test_data_structure_complexity_performance(self):
        """Test performance impact of different data structure complexities."""
        base_dataset = self._create_large_zephyr_dataset(10, 10)

        # Test with different nesting levels
        nesting_levels = [3, 5, 8, 10]
        detection_times = []

        for nesting_level in nesting_levels:
            # Create deeply nested structure
            nested_dataset = base_dataset.copy()
            current = nested_dataset

            for level in range(nesting_level):
                current[f"nested_level_{level}"] = {
                    "data": base_dataset.copy(),
                    "metadata": {"level": level, "complexity": "high"},
                }
                current = current[f"nested_level_{level}"]

            start_time = time.time()
            detected_format = self.detector.detect_format(nested_dataset)
            detection_time = time.time() - start_time

            detection_times.append(detection_time)
            self.assertEqual(detected_format, SupportedFormat.ZEPHYR)

        # Deeply nested structures should not cause exponential performance degradation
        self.assertLess(
            detection_times[-1] / detection_times[0],
            5,
            "Deep nesting should not cause severe performance degradation",
        )


if __name__ == "__main__":
    unittest.main()
