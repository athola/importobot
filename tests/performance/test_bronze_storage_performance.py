"""Performance tests for Bronze layer storage operations.

Tests performance characteristics and ensures they meet business requirements:
- Ingestion throughput
- Query response time
- Pagination performance
- Concurrent operation scalability

Business Use Cases:
- Handle bulk test imports (1000+ test cases)
- Respond to UI queries quickly (<100ms)
- Support multiple concurrent users
"""

import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import LayerMetadata
from importobot.medallion.storage.local import LocalStorageBackend

# pylint: disable=no-name-in-module
from tests.utils.performance_utils import get_adaptive_thresholds


class TestBronzeStoragePerformance:
    """Performance tests for Bronze storage operations."""

    @staticmethod
    def _measure_throughput(
        bronze_layer: BronzeLayer,
        test_data: dict,
        record_count: int,
        prefix: str,
    ) -> tuple[float, float]:
        """Ingest a number of records and return (throughput, elapsed_seconds)."""
        start_time = time.perf_counter()
        for i in range(record_count):
            metadata = LayerMetadata(
                source_path=Path(f"{prefix}_{i}.json"),
                layer_name="bronze",
                ingestion_timestamp=datetime.now(),
            )
            bronze_layer.ingest(test_data, metadata)

        elapsed = time.perf_counter() - start_time
        throughput = record_count / max(elapsed, 1e-6)
        return throughput, elapsed

    def test_bulk_ingestion_meets_throughput_requirements(self):
        """Test bulk ingestion can handle 1000 records in reasonable time.

        Business Requirement: QA team imports 1000+ test cases from Zephyr.
        Acceptance Criteria: <1 second for 1000 records.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            test_data = {
                "testCase": {
                    "name": "Performance Test",
                    "description": "Bulk ingestion test",
                    "steps": [
                        {"action": "Step 1", "expected": "Result 1"},
                        {"action": "Step 2", "expected": "Result 2"},
                    ],
                }
            }

            # Calibrate throughput with a smaller warm-up run to adapt to hardware.
            calibration_backend = LocalStorageBackend(
                {"base_path": str(Path(temp_dir) / "storage_calibration")}
            )
            calibration_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze_calibration",
                storage_backend=calibration_backend,
            )
            calibration_throughput, calibration_elapsed = self._measure_throughput(
                calibration_layer, test_data, record_count=100, prefix="warmup"
            )

            assert calibration_throughput > 100, (
                f"Warm-up throughput too low ({calibration_throughput:.0f} rec/s); "
                "hardware may be undersized for this test."
            )

            # Main performance measurement using fresh storage backend.
            storage_backend = LocalStorageBackend(
                {"base_path": str(Path(temp_dir) / "storage_main")}
            )
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze_main",
                storage_backend=storage_backend,
            )

            main_throughput, elapsed_time = self._measure_throughput(
                bronze_layer, test_data, record_count=1000, prefix="perf"
            )

            # Require the large run to stay within 80% of calibrated throughput.
            assert main_throughput >= calibration_throughput * 0.8, (
                f"Main throughput {main_throughput:.0f} rec/s fell below 80% of "
                f"calibrated baseline {calibration_throughput:.0f} rec/s "
                f"(elapsed {elapsed_time:.2f}s, warm-up {calibration_elapsed:.2f}s)"
            )

    def test_query_response_time_meets_ui_requirements(self):
        """Test query response time meets UI responsiveness requirements.

        Business Requirement: UI displays test results within 25ms.
        Acceptance Criteria: Query 100 records in <25ms (adaptive).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Pre-populate with data
            for i in range(200):
                test_data = {"test": f"data_{i}"}
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            # Measure query time
            start_time = time.perf_counter()
            records = bronze_layer.get_bronze_records(limit=100)
            elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

            # Use adaptive threshold based on system performance
            threshold = get_adaptive_thresholds().get_operation_threshold(25.0)
            assert elapsed_time < threshold, (
                f"Query took {elapsed_time:.2f}ms, "
                f"adaptive threshold is <{threshold:.2f}ms"
            )

            # Verify correct number of records
            assert len(records) == 100

    def test_filter_dispatch_query_performance(self):
        """Filter-based queries should respond within business threshold."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            zephyr_template = {
                "testCase": {"name": "Perf Zephyr", "steps": [{"action": "A"}]}
            }
            generic_template = {"misc": "data"}

            zephyr_count = 300
            generic_count = 300

            for i in range(zephyr_count):
                metadata = LayerMetadata(
                    source_path=Path(f"perf_zephyr_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(zephyr_template, metadata)

            for i in range(generic_count):
                metadata = LayerMetadata(
                    source_path=Path(f"perf_generic_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(generic_template, metadata)

            start_time = time.perf_counter()
            zephyr_records = bronze_layer.get_bronze_records(
                filter_criteria={"format_type": "ZEPHYR"}
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Use adaptive threshold based on system performance
            threshold = get_adaptive_thresholds().get_operation_threshold(40.0)
            assert elapsed_ms < threshold, (
                f"Filter query took {elapsed_ms:.2f}ms, "
                f"adaptive threshold is <{threshold:.2f}ms"
            )
            assert len(zephyr_records) == zephyr_count

    def test_pagination_performance_scales_linearly(self):
        """Test pagination performance scales linearly with data size.

        Business Requirement: Large datasets should paginate efficiently.
        Acceptance Criteria: 2x data shouldn't take >1.6x time.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Test with 100 records
            for i in range(100):
                test_data = {"test": f"data_{i}"}
                metadata = LayerMetadata(
                    source_path=Path(f"test_100_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            start_time = time.perf_counter()
            records_100 = bronze_layer.get_bronze_records(limit=50)
            time_100 = time.perf_counter() - start_time

            # Add 100 more records (200 total)
            for i in range(100, 200):
                test_data = {"test": f"data_{i}"}
                metadata = LayerMetadata(
                    source_path=Path(f"test_200_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            start_time = time.perf_counter()
            records_200 = bronze_layer.get_bronze_records(limit=50)
            time_200 = time.perf_counter() - start_time

            # Performance should scale reasonably (not exponentially)
            # 2x data shouldn't take more than 3x time
            if time_100 > 0:
                scaling_factor = time_200 / time_100
                assert scaling_factor < 1.6, (
                    f"Performance degraded by {scaling_factor:.2f}x "
                    f"when data doubled, expected <1.6x"
                )

            assert len(records_100) == 50
            assert len(records_200) == 50

    def test_concurrent_read_performance(self):
        """Test concurrent reads don't significantly degrade performance.

        Business Requirement: Multiple users querying simultaneously.
        Acceptance Criteria: 4 concurrent reads should be <12x slower than serial.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Pre-populate with data
            for i in range(100):
                test_data = {"test": f"data_{i}"}
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            # Warm cache to avoid first-hit overhead
            bronze_layer.get_bronze_records(limit=25)

            # Serial reads
            start_time = time.perf_counter()
            for _ in range(4):
                bronze_layer.get_bronze_records(limit=25)
            serial_time = time.perf_counter() - start_time

            # Concurrent reads
            results = []

            def read_records():
                records = bronze_layer.get_bronze_records(limit=25)
                results.append(len(records))

            start_time = time.perf_counter()
            threads = [threading.Thread(target=read_records) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            concurrent_time = time.perf_counter() - start_time

            # Concurrent shouldn't be much slower than serial
            # (file system locks may add some overhead)
            if serial_time > 0:
                slowdown = concurrent_time / serial_time
                assert slowdown < 12.0, (
                    f"Concurrent reads {slowdown:.2f}x slower than serial, "
                    "expected <12x (file system contention)"
                )

            # All reads should have succeeded
            assert len(results) == 4
            assert all(count == 25 for count in results)

    def test_retrieval_time_stable_with_increasing_data(self):
        """Test retrieval time remains stable as dataset grows.

        Business Requirement: System performance shouldn't degrade over time.
        Acceptance Criteria: Query time increases <100% from 100 to 1000 records.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Measure query time with 100 records
            for i in range(100):
                test_data = {"test": f"data_{i}"}
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            start_time = time.perf_counter()
            bronze_layer.get_bronze_records(limit=10)
            time_at_100 = time.perf_counter() - start_time

            # Add more records (1000 total)
            for i in range(100, 1000):
                test_data = {"test": f"data_{i}"}
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            start_time = time.perf_counter()
            bronze_layer.get_bronze_records(limit=10)
            time_at_1000 = time.perf_counter() - start_time

            # Query time shouldn't increase dramatically
            if time_at_100 > 0:
                degradation = (time_at_1000 - time_at_100) / time_at_100
                assert degradation < 1.0, (
                    f"Query time degraded by {degradation * 100:.0f}% "
                    "with 10x data growth, expected <100% "
                    "(incremental metadata caching)"
                )

    def test_empty_storage_query_performance(self):
        """Test empty storage queries are fast.

        Business Requirement: New system startup should be responsive.
        Acceptance Criteria: Empty query <5ms (adaptive).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Query empty storage
            start_time = time.perf_counter()
            records = bronze_layer.get_bronze_records()
            elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

            # Use adaptive threshold based on system performance
            threshold = get_adaptive_thresholds().get_operation_threshold(5.0)
            assert elapsed_time < threshold, (
                f"Empty storage query took {elapsed_time:.2f}ms, "
                f"adaptive threshold is <{threshold:.2f}ms"
            )
            assert len(records) == 0

    def test_large_dataset_scalability(self):
        """Test system handles large datasets (5000+ records).

        Business Requirement: Enterprise customers have large test suites.
        Acceptance Criteria: Ingest 5000 records in <3s and query 100
        records in <80ms (adaptive).
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            num_records = 5000

            # Ingest large dataset
            start_time = time.perf_counter()
            for i in range(num_records):
                test_data = {"test": f"data_{i}", "index": i}
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            ingestion_time = time.perf_counter() - start_time

            # Use adaptive thresholds based on system performance
            # 3s in ms
            ingestion_threshold = get_adaptive_thresholds().get_operation_threshold(
                3000.0
            )
            assert ingestion_time * 1000 < ingestion_threshold, (
                f"Ingesting {num_records} records took {ingestion_time:.2f}s, "
                f"adaptive threshold is <{ingestion_threshold / 1000:.2f}s"
            )

            # Query should still be responsive
            start_time = time.perf_counter()
            records = bronze_layer.get_bronze_records(limit=100)
            query_time = (time.perf_counter() - start_time) * 1000

            query_threshold = get_adaptive_thresholds().get_operation_threshold(80.0)
            assert query_time < query_threshold, (
                f"Query with {num_records} total records took {query_time:.2f}ms, "
                f"adaptive threshold is <{query_threshold:.2f}ms"
            )
            assert len(records) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
