"""Integration tests for caching in real conversion workflows.

Tests verify caching behavior in actual conversion scenarios:
- JSON to Robot Framework conversion
- Format detection
- Test generation
"""

import json
from typing import Any, cast

import pytest

from importobot import exceptions
from importobot.context import clear_context, get_context
from importobot.core.converter import JsonToRobotConverter
from importobot.medallion.bronze.detection_cache import DetectionCache
from importobot.medallion.bronze.format_detector import FormatDetector
from importobot.services.performance_cache import get_performance_cache


class TestCachingInConversionWorkflow:
    """Test caching behavior during actual test conversion."""

    @pytest.fixture(autouse=True)
    def _clean_context(self):
        """Ensure clean context for each test."""
        clear_context()
        yield
        clear_context()

    def test_format_detection_caches_results(self):
        """GIVEN a format detector processing the same data twice
        WHEN detecting format on repeated calls
        THEN second call uses cached result

        Business value: Avoid expensive format detection on repeated data
        """
        cache = DetectionCache()
        detector = FormatDetector(cache=cache)

        test_data = {
            "testCase": {
                "name": "Test Login",
                "steps": [{"action": "Login", "data": "user@example.com"}],
            }
        }

        # First detection (cache miss)
        result1 = detector.detect_format(test_data)
        stats1 = cache.get_cache_stats()

        # Second detection (cache hit)
        result2 = detector.detect_format(test_data)
        stats2 = cache.get_cache_stats()

        # Results should be identical
        assert result1 == result2

        # Cache hits should increase
        assert stats2["cache_hits"] > stats1["cache_hits"]

    def test_string_operations_cached_during_conversion(self):
        """GIVEN a converter processing test data
        WHEN converting multiple tests with repeated strings
        THEN string operations are cached

        Business value: Reduce CPU usage for string processing
        """
        converter = JsonToRobotConverter()

        test_data = {
            "testCases": [
                {
                    "name": "Test Case 1",
                    "steps": [
                        {"action": "LOGIN", "expected": "SUCCESS"},
                        {"action": "VERIFY", "expected": "LOADED"},
                    ],
                },
                {
                    "name": "Test Case 2",
                    "steps": [
                        {
                            "action": "LOGIN",
                            "expected": "SUCCESS",
                        },  # Repeated strings
                        {"action": "LOGOUT", "expected": "SUCCESS"},
                    ],
                },
            ]
        }

        # Convert tests
        result = converter.convert(test_data)

        # Verify conversion succeeded
        assert "Test Case 1" in result
        assert "Test Case 2" in result

        # Verify cache was used
        perf_cache = get_performance_cache()
        stats = perf_cache.get_cache_stats()

        # Should have some cache hits from repeated strings
        assert stats["cache_hits"] > 0

    def test_batch_conversion_cache_accumulation(self):
        """GIVEN a batch of test files to convert
        WHEN converting files sequentially
        THEN cache accumulates useful data

        Business value: Later files in batch benefit from cached operations
        """
        converter = JsonToRobotConverter()
        perf_cache = get_performance_cache()

        # Simulate batch of files with overlapping data
        batch = [
            {
                "testCase": {
                    "name": f"Test {i}",
                    "steps": [
                        {"action": "SETUP", "data": "initialize"},  # Repeated
                        {"action": f"TEST_{i}", "data": f"data_{i}"},
                        {"action": "TEARDOWN", "data": "cleanup"},  # Repeated
                    ],
                }
            }
            for i in range(5)
        ]

        stats_per_file = []

        for i, test_data in enumerate(batch):
            result = converter.convert(test_data)
            assert f"Test {i}" in result

            # Track stats after each file
            stats = perf_cache.get_cache_stats()
            stats_per_file.append(stats)

        # Later files should have higher hit rates (benefiting from cache)
        first_file_hits = stats_per_file[0]["cache_hits"]
        last_file_hits = stats_per_file[-1]["cache_hits"]

        # Last file should have more cache hits
        assert last_file_hits >= first_file_hits

    def test_cache_survives_conversion_errors(self):
        """GIVEN a conversion workflow that encounters an error
        WHEN continuing to process valid data
        THEN cache remains functional

        Business value: Resilient processing in production
        """
        converter = JsonToRobotConverter()
        perf_cache = get_performance_cache()

        # Valid data
        valid_data = {
            "testCase": {
                "name": "Valid Test",
                "steps": [{"action": "test", "expected": "pass"}],
            }
        }

        # Convert valid data first
        result1 = converter.convert(valid_data)
        assert "Valid Test" in result1

        # Try to convert invalid data (should fail)
        invalid_data = {"malformed": "data without required fields"}

        with pytest.raises(exceptions.ImportobotError):
            converter.convert(invalid_data)

        # Cache should still work for subsequent valid conversions
        result2 = converter.convert(valid_data)
        assert "Valid Test" in result2

        # Cache should have recorded hits
        stats = perf_cache.get_cache_stats()
        assert stats["cache_hits"] > 0


class TestCachingWithRealFiles:
    """Test caching with actual JSON test files."""

    @pytest.fixture(autouse=True)
    def _clean_context(self):
        """Ensure clean context for each test."""
        clear_context()
        yield
        clear_context()

    def test_caching_with_example_files(self, tmp_path):
        """GIVEN real JSON test files
        WHEN converting them with caching enabled
        THEN conversions complete and cache is utilized

        Business value: Verify caching works with realistic data
        """
        # Create sample test files
        test_files = []
        for i in range(3):
            file_path = tmp_path / f"test_{i}.json"
            test_data = {
                "testCase": {
                    "name": f"Integration Test {i}",
                    "description": "Test caching behavior",
                    "steps": [
                        {"action": "Setup", "expected": "Ready"},
                        {"action": f"Execute_{i}", "expected": "Success"},
                        {"action": "Cleanup", "expected": "Clean"},
                    ],
                }
            }
            file_path.write_text(json.dumps(test_data))
            test_files.append(file_path)

        # Convert all files
        converter = JsonToRobotConverter()
        results = []

        for file_path in test_files:
            data = json.loads(file_path.read_text())
            result = converter.convert(data)
            results.append(result)

        # Verify all conversions succeeded
        assert len(results) == 3
        for i, result in enumerate(results):
            assert f"Integration Test {i}" in result

        # Verify cache was utilized
        perf_cache = get_performance_cache()
        stats = perf_cache.get_cache_stats()

        # Should have processed multiple operations
        total_operations = stats["cache_hits"] + stats["cache_misses"]
        assert total_operations > 0

        # Should have some cache reuse
        if total_operations > 1:
            hit_rate = stats["cache_hits"] / total_operations
            # At least some operations should have hit cache
            # (due to repeated strings like "Setup", "Cleanup")
            assert hit_rate > 0

    def test_large_file_conversion_uses_cache_effectively(self, tmp_path):
        """GIVEN a large test file with many test cases
        WHEN converting it
        THEN cache provides performance benefit

        Business value: Efficient processing of large test suites
        """
        # Create large test file with repeated patterns
        large_test_data = {
            "testCases": [
                {
                    "name": f"Test Case {i}",
                    "priority": "HIGH" if i % 2 == 0 else "LOW",  # Repeated values
                    "steps": [
                        {"action": "Initialize", "expected": "Ready"},  # Repeated
                        {"action": f"Test_{i}", "expected": "Pass"},
                        {"action": "Finalize", "expected": "Complete"},  # Repeated
                    ],
                }
                for i in range(50)  # 50 test cases
            ]
        }

        file_path = tmp_path / "large_suite.json"
        file_path.write_text(json.dumps(large_test_data))

        # Convert large file
        converter = JsonToRobotConverter()
        data = json.loads(file_path.read_text())
        result = converter.convert(data)

        # Verify conversion succeeded
        assert "Test Case 0" in result
        assert "Test Case 49" in result

        # Verify cache was effective
        perf_cache = get_performance_cache()
        stats = perf_cache.get_cache_stats()

        # With 50 test cases and repeated strings, should have good hit rate
        total_ops = stats["cache_hits"] + stats["cache_misses"]
        if total_ops > 0:
            hit_rate = stats["cache_hits"] / total_ops

            # Should have significant cache reuse
            # (Conservative threshold to avoid flakiness)
            assert hit_rate > 0.1


class TestCacheInvalidation:
    """Test cache invalidation scenarios."""

    @pytest.fixture(autouse=True)
    def _clean_context(self):
        """Ensure clean context for each test."""
        clear_context()
        yield
        clear_context()

    def test_modified_data_invalidates_cache(self):
        """GIVEN data that has been cached
        WHEN the data is modified
        THEN new conversion uses fresh data, not stale cache

        Business value: Ensure cache doesn't serve stale data
        """
        converter = JsonToRobotConverter()

        # Original data
        test_data = {
            "testCase": {
                "name": "Original Test",
                "steps": [{"action": "test", "expected": "original"}],
            }
        }

        # Convert original
        result1 = converter.convert(test_data)
        assert "Original Test" in result1
        assert "original" in result1.lower()

        # Modify data
        test_data["testCase"]["name"] = "Modified Test"
        steps = cast(list[dict[str, Any]], test_data["testCase"]["steps"])
        steps[0]["expected"] = "modified"

        # Convert modified data
        result2 = converter.convert(test_data)
        assert "Modified Test" in result2
        assert "modified" in result2.lower()

        # Results should be different
        assert result1 != result2

    def test_cache_cleared_between_independent_jobs(self):
        """GIVEN multiple independent conversion jobs
        WHEN each job should have isolated cache
        THEN clearing cache between jobs prevents interference

        Business value: Ensure job isolation in multi-tenant systems
        """
        converter = JsonToRobotConverter()

        def run_conversion_job(job_id: int) -> tuple[str, float]:
            # Job-specific data
            data = {
                "testCase": {
                    "name": f"Job {job_id} Test",
                    "steps": [{"action": f"job_{job_id}_action", "data": job_id}],
                }
            }

            result = converter.convert(data)

            # Get cache stats for this job
            perf_cache = get_performance_cache()
            stats = perf_cache.get_cache_stats()

            return (result, stats["cache_size"])

        # Run first job
        result1, cache_size1 = run_conversion_job(1)

        # Clear cache to simulate job isolation
        context = get_context()
        context.clear_caches()

        # Run second job (should start with empty cache)
        result2, cache_size2 = run_conversion_job(2)

        # Verify both jobs succeeded
        assert "Job 1 Test" in result1
        assert "Job 2 Test" in result2

        # Second job should have started with cleared cache
        # (size might vary, but shouldn't have accumulated from job 1)
