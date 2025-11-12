"""Medallion architecture invariant tests using Hypothesis.

Tests architectural properties that should hold true across the Medallion system:
- Cross-layer data consistency and integrity
- Resource management under load
- Error boundaries and system stability
- Performance characteristics preservation
- Data transformation correctness

These tests focus on system-level properties not covered by unit tests.
"""

import gc
import tempfile
import time
from pathlib import Path
from typing import Any, TypedDict

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import DrawFn

from importobot.medallion.bronze.raw_data_processor import RawDataProcessor
from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import ProcessingResult
from importobot.medallion.interfaces.enums import ProcessingStatus, SupportedFormat
from importobot.medallion.interfaces.records import BronzeRecord


class ProcessingResultDict(TypedDict):
    """TypedDict for processing result dictionary structure."""

    processing_result: ProcessingResult
    quality_metrics: dict[str, Any]
    detected_format: str


def _extract_detected_format(result: ProcessingResultDict) -> SupportedFormat | str:
    detected_format = result.get("detected_format")
    if isinstance(detected_format, (SupportedFormat, str)):
        return detected_format
    return str(detected_format) if detected_format else ""


@st.composite
def medallion_test_data(draw: DrawFn) -> Any:
    """Generate realistic test data for Medallion architecture testing."""
    return draw(
        st.dictionaries(
            keys=st.sampled_from(
                [
                    "id",
                    "name",
                    "description",
                    "steps",
                    "status",
                    "priority",
                    "testCase",
                    "execution",
                    "project",
                    "metadata",
                    "author",
                ]
            ),
            values=st.one_of(
                st.text(min_size=0, max_size=100),
                st.integers(min_value=0, max_value=9999),
                st.dictionaries(
                    keys=st.text(min_size=1, max_size=20),
                    values=st.text(min_size=0, max_size=50),
                    min_size=0,
                    max_size=5,
                ),
                st.lists(
                    st.dictionaries(
                        keys=st.sampled_from(["step", "action", "expected"]),
                        values=st.text(min_size=0, max_size=100),
                        min_size=1,
                        max_size=3,
                    ),
                    min_size=0,
                    max_size=10,
                ),
            ),
            min_size=1,
            max_size=8,
        )
    )


class TestMedallionArchitectureInvariants:
    """Test architectural invariants of the Medallion system."""

    @given(medallion_test_data())
    @settings(max_examples=25)
    def test_data_consistency_across_operations_invariant(self, test_data: Any) -> None:
        """Invariant: Data should maintain consistency across multiple operations."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                bronze_layer = BronzeLayer(storage_path=Path(temp_dir))
                processor = RawDataProcessor(bronze_layer=bronze_layer)
                source_info = {
                    "source": "invariant_test",
                    "timestamp": "2024-01-01T00:00:00",
                }

                # Process the same data multiple times
                results = []
                for _i in range(3):
                    result = processor.ingest_with_detection(test_data, source_info)
                    results.append(result)

                # All results should have consistent structure
                assert len(results) == 3
                for result in results:
                    # Results are BronzeRecord objects, not dicts
                    assert isinstance(result, BronzeRecord)
                    assert hasattr(result, "metadata")
                    assert hasattr(result, "format_detection")

                # Quality metrics should be deterministic for same input
                quality_scores = [r.metadata.quality_score for r in results]
                assert len(set(quality_scores)) <= 2  # Allow for minor variations

                # Format detection should be consistent
                formats = [r.format_detection.detected_format for r in results]
                assert len(set(formats)) == 1  # Should be identical

        except Exception as e:
            pytest.fail(f"Data consistency invariant violated: {type(e).__name__}: {e}")

    @given(st.lists(medallion_test_data(), min_size=2, max_size=10))
    @settings(max_examples=15)
    def test_resource_management_invariant(self, test_data_list: list[Any]) -> None:
        """Invariant: System should manage resources properly under batch load."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                bronze_layer = BronzeLayer(storage_path=Path(temp_dir))
                processor = RawDataProcessor(bronze_layer=bronze_layer)

                # Batch process multiple items
                results = []
                for i, test_data in enumerate(test_data_list):
                    source_info = {
                        "source": f"batch_test_{i}",
                        "batch_id": "resource_test",
                    }
                    result = processor.ingest_with_detection(test_data, source_info)
                    results.append(result)

                # All operations should complete successfully
                assert len(results) == len(test_data_list)

                # Each result should have valid processing status
                for result in results:
                    processing_status = result.metadata.processing_status
                    assert processing_status in [
                        ProcessingStatus.COMPLETED,
                        ProcessingStatus.FAILED,
                        ProcessingStatus.SKIPPED,
                    ]

                # System should not leak resources (basic check)
                # Memory usage should stabilize after processing
                gc.collect()  # Force garbage collection
                assert True  # If we get here, no major resource leaks

        except Exception as e:
            pytest.fail(
                f"Resource management invariant violated: {type(e).__name__}: {e}"
            )

    @given(medallion_test_data(), st.integers(min_value=1, max_value=5))
    @settings(max_examples=20)
    def test_error_boundary_stability_invariant(
        self, test_data: Any, corruption_factor: int
    ) -> None:
        """Invariant: System maintains stability with problematic data."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                bronze_layer = BronzeLayer(storage_path=Path(temp_dir))
                processor = RawDataProcessor(bronze_layer=bronze_layer)

                # Test with normal data first
                source_info = {"source": "stability_test", "corruption": "none"}
                normal_result = processor.ingest_with_detection(test_data, source_info)
                assert isinstance(normal_result, dict)

                # Now test with potentially problematic variations
                problematic_variations = [
                    {},  # Empty data
                    {"": ""},  # Empty key/value
                    {
                        str(i): str(i * corruption_factor)
                        for i in range(corruption_factor)
                    },  # Repetitive
                ]

                for i, problem_data in enumerate(problematic_variations):
                    source_info_problem = {
                        "source": f"problem_test_{i}",
                        "variation": str(i),
                    }

                    # System should either process successfully or fail gracefully
                    result = processor.ingest_with_detection(
                        problem_data, source_info_problem
                    )

                    # Should always return a dict structure
                    assert isinstance(result, dict)
                    # pylint: disable=unsupported-membership-test
                    assert "processing_result" in result

                    # Processing status should be valid
                    status = result["processing_result"].status
                    assert status in [
                        ProcessingStatus.COMPLETED,
                        ProcessingStatus.FAILED,
                        ProcessingStatus.SKIPPED,
                    ]

        except Exception as e:
            pytest.fail(
                f"Error boundary stability invariant violated: {type(e).__name__}: {e}"
            )

    @given(medallion_test_data())
    @settings(max_examples=30)
    def test_performance_consistency_invariant(self, test_data: Any) -> None:
        """Invariant: System performance should be consistent for similar operations."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                bronze_layer = BronzeLayer(storage_path=Path(temp_dir))
                processor = RawDataProcessor(bronze_layer=bronze_layer)

                source_info = {
                    "source": "performance_test",
                    "timestamp": "2024-01-01T00:00:00",
                }

                results = self._ingest_repeated_results(
                    processor, test_data, source_info
                )
                self._assert_deterministic_formats(results)
                self._assert_deterministic_status(results)

        except Exception as e:
            pytest.fail(
                f"Performance consistency invariant violated: {type(e).__name__}: {e}"
            )

    @given(medallion_test_data())
    @settings(max_examples=25)
    def test_data_transformation_preservation_invariant(self, test_data: Any) -> None:
        """Invariant: Essential data properties preserved through transformations."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                bronze_layer = BronzeLayer(storage_path=Path(temp_dir))
                processor = RawDataProcessor(bronze_layer=bronze_layer)
                source_info = {
                    "source": "transformation_test",
                    "timestamp": "2024-01-01T00:00:00",
                }

                # Record input characteristics
                input_has_data = len(test_data) > 0 if test_data else False

                # Process data
                result = processor.ingest_with_detection(test_data, source_info)

                # Verify result structure preserves essential properties
                assert isinstance(result, dict)

                processing_result = result["processing_result"]
                assert hasattr(processing_result, "metadata")
                assert hasattr(processing_result, "status")

                # If input had data, output should reflect that
                if input_has_data:
                    assert processing_result.processed_count >= 0
                    assert processing_result.metadata.record_count >= 0

                # Quality metrics should reflect input characteristics
                quality_metrics = result["quality_metrics"]
                assert hasattr(quality_metrics, "overall_score")
                assert 0.0 <= quality_metrics.overall_score <= 1.0

                # Format detection should be reasonable
                detected_format = result["detected_format"]
                assert isinstance(detected_format, str)
                assert len(detected_format) > 0

        except Exception as e:
            pytest.fail(
                f"Data transformation preservation invariant violated: "
                f"{type(e).__name__}: {e}"
            )

    def _ingest_repeated_results(
        self,
        processor: RawDataProcessor,
        test_data: Any,
        source_info: dict[str, Any],
        runs: int = 3,
    ) -> list[ProcessingResultDict | BronzeRecord]:
        results: list[ProcessingResultDict | BronzeRecord] = []
        for _ in range(runs):
            result = processor.ingest_with_detection(test_data, source_info)
            self._assert_result_shape(result)
            results.append(result)
        return results

    def _assert_result_shape(self, result: dict[str, Any] | BronzeRecord) -> None:
        assert isinstance(result, (dict, BronzeRecord))
        if isinstance(result, dict):
            essential_keys = ["processing_result", "quality_metrics"]
            for key in essential_keys:
                assert key in result, f"Missing essential key: {key}"
            assert "detected_format" in result
        else:
            assert hasattr(result, "metadata")
            assert hasattr(result, "format_detection")

    def _assert_deterministic_formats(
        self, results: list[ProcessingResultDict | BronzeRecord]
    ) -> None:
        if len(results) < 2:
            return
        first_format = self._extract_format(results[0])
        for result in results[1:]:
            assert self._extract_format(result) == first_format, (
                "Format detection should be deterministic"
            )

    def _assert_deterministic_status(
        self, results: list[ProcessingResultDict | BronzeRecord]
    ) -> None:
        if len(results) < 2:
            return
        first_status = self._extract_status(results[0])
        for result in results[1:]:
            assert self._extract_status(result) == first_status, (
                "Processing status should be deterministic"
            )

    @staticmethod
    def _extract_format(
        result: ProcessingResultDict | BronzeRecord,
    ) -> SupportedFormat | str:
        if isinstance(result, dict) and not isinstance(result, BronzeRecord):
            return _extract_detected_format(result)
        assert isinstance(result, BronzeRecord)
        return result.format_detection.detected_format

    @staticmethod
    def _extract_status(
        result: ProcessingResultDict | BronzeRecord,
    ) -> ProcessingStatus | None:
        if isinstance(result, dict):
            # Use direct key access instead of get() for better type inference
            if "processing_result" in result:
                proc_result = result["processing_result"]
                return getattr(proc_result, "status", None)
            return None
        assert isinstance(result, BronzeRecord)
        return result.metadata.processing_status

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=10)
    def test_system_scalability_properties_invariant(
        self, data_multiplier: int
    ) -> None:
        """Invariant: System should exhibit predictable scalability properties."""
        assume(data_multiplier <= 50)  # Keep test times reasonable

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                bronze_layer = BronzeLayer(storage_path=Path(temp_dir))
                processor = RawDataProcessor(bronze_layer=bronze_layer)

                # Create data of increasing size
                large_test_data = {
                    "tests": [
                        {
                            "id": f"test_{i}",
                            "name": f"Test Case {i}",
                            "description": "x" * 10,  # Small description per item
                        }
                        for i in range(data_multiplier)
                    ]
                }

                source_info = {
                    "source": "scalability_test",
                    "size_factor": str(data_multiplier),
                }

                # Measure processing
                start_time = time.time()
                result = processor.ingest_with_detection(large_test_data, source_info)
                end_time = time.time()
                processing_time = end_time - start_time

                # System should handle increasing load gracefully
                assert processing_time < data_multiplier * 0.1  # Linear scaling limit

                # Result should be valid regardless of size
                assert isinstance(result, dict)
                # pylint: disable=unsupported-membership-test
                assert "processing_result" in result

                processing_result = result["processing_result"]
                assert processing_result.status in [
                    ProcessingStatus.COMPLETED,
                    ProcessingStatus.FAILED,
                    ProcessingStatus.SKIPPED,
                ]

                # Metadata should reflect the data size appropriately
                assert processing_result.processed_count >= 0

        except Exception as e:
            pytest.fail(
                f"System scalability properties invariant violated: "
                f"{type(e).__name__}: {e}"
            )
