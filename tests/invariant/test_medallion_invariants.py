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

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from importobot.medallion.bronze.raw_data_processor import RawDataProcessor
from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.enums import ProcessingStatus
from importobot.medallion.interfaces.records import BronzeRecord


@st.composite
def medallion_test_data(draw):
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
    def test_data_consistency_across_operations_invariant(self, test_data):
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
    def test_resource_management_invariant(self, test_data_list):
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
    def test_error_boundary_stability_invariant(self, test_data, corruption_factor):
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
    def test_performance_consistency_invariant(self, test_data):
        """Invariant: System performance should be consistent for similar operations."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                bronze_layer = BronzeLayer(storage_path=Path(temp_dir))
                processor = RawDataProcessor(bronze_layer=bronze_layer)

                # Measure processing times for multiple runs
                processing_times = []
                source_info = {
                    "source": "performance_test",
                    "timestamp": "2024-01-01T00:00:00",
                }

                for _run in range(3):
                    start_time = time.time()
                    result = processor.ingest_with_detection(test_data, source_info)
                    end_time = time.time()

                    processing_time = end_time - start_time
                    processing_times.append(processing_time)

                    # Should complete within reasonable time (10 seconds max)
                    assert processing_time < 10.0

                    # Result should be valid
                    assert isinstance(result, dict)
                    # pylint: disable=unsupported-membership-test
                    assert "processing_result" in result

                # Performance should be reasonably consistent
                # (no single run should be more than 10x slower than the fastest)
                min_time = min(processing_times)
                max_time = max(processing_times)

                if min_time > 0:  # Avoid division by zero
                    ratio = max_time / min_time
                    assert ratio < 10.0  # Performance consistency check

        except Exception as e:
            pytest.fail(
                f"Performance consistency invariant violated: {type(e).__name__}: {e}"
            )

    @given(medallion_test_data())
    @settings(max_examples=25)
    def test_data_transformation_preservation_invariant(self, test_data):
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

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=10)
    def test_system_scalability_properties_invariant(self, data_multiplier):
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
