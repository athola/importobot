"""Invariant tests for Bronze layer storage operations.

Tests fundamental properties that must always hold true:
- Storage operations are idempotent
- Retrieval never loses data
- Pagination is deterministic
- Error handling is consistent

Business Use Cases:
- Data integrity during concurrent operations
- Reliable data retrieval under all conditions
- Predictable behavior across edge cases
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

try:
    from hypothesis import given, settings
    from hypothesis import strategies as st
except ImportError as exc:  # pragma: no cover - optional dependency
    raise unittest.SkipTest("Hypothesis is required for invariant tests") from exc

from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import LayerMetadata
from importobot.medallion.interfaces.enums import ProcessingStatus, SupportedFormat
from importobot.medallion.storage.local import LocalStorageBackend


class TestBronzeStorageInvariants:
    """Invariant tests for Bronze storage operations."""

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=30),
            values=st.one_of(st.text(max_size=100), st.integers(), st.none()),
            min_size=1,
            max_size=15,
        )
    )
    @settings(max_examples=30, deadline=3000)
    def test_retrieval_count_never_exceeds_ingestion_count_invariant(
        self, test_data: dict[str, Any]
    ) -> None:
        """Invariant: Number of retrieved records never exceeds ingested records.

        Business Case: Data integrity - can't retrieve more than was stored.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Ingest a specific number of records
            ingestion_count = 5
            for i in range(ingestion_count):
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            # Retrieve with various limits
            for limit in [1, 5, 10, 100, 1000]:
                records = bronze_layer.get_bronze_records(limit=limit)

                # INVARIANT: Retrieved count <= ingested count
                assert len(records) <= ingestion_count, (
                    f"Retrieved {len(records)} records but only "
                    f"ingested {ingestion_count}"
                )

    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=20, deadline=None)
    def test_limit_zero_always_returns_empty_invariant(self, num_records: int) -> None:
        """Invariant: Querying with limit=0 always returns empty list.

        Business Case: SQL-like behavior - LIMIT 0 returns no rows.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Ingest arbitrary number of records
            for i in range(num_records):
                test_data = {"test": f"data_{i}"}
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            # Query with limit=0
            records = bronze_layer.get_bronze_records(limit=0)

            # INVARIANT: limit=0 always returns empty list
            assert len(records) == 0, (
                f"limit=0 should return 0 records, got {len(records)}"
            )

    @given(
        st.lists(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.text(max_size=50),
                min_size=1,
                max_size=5,
            ),
            min_size=1,
            max_size=30,
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_retrieval_after_ingestion_preserves_count_invariant(
        self, test_data_list: list[dict[str, Any]]
    ) -> None:
        """Invariant: Retrieved record count equals ingested count.

        Business Case: Data persistence - all ingested data must be retrievable.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Ingest all test data
            for i, test_data in enumerate(test_data_list):
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            # Retrieve with sufficiently large limit
            records = bronze_layer.get_bronze_records(limit=len(test_data_list) + 100)

            # INVARIANT: All ingested records are retrievable
            assert len(records) == len(test_data_list), (
                f"Ingested {len(test_data_list)} records but retrieved {len(records)}"
            )

    @given(
        st.integers(min_value=1, max_value=50), st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=20, deadline=3000)
    def test_limit_parameter_bounds_retrieval_invariant(
        self, num_records: int, limit: int
    ) -> None:
        """Invariant: Retrieved count <= min(limit, total_records).

        Business Case: Pagination must respect limit parameter.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Ingest records
            for i in range(num_records):
                test_data = {"test": f"data_{i}"}
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            # Retrieve with limit
            records = bronze_layer.get_bronze_records(limit=limit)

            # INVARIANT: Retrieved count respects both limit and total records
            expected_max = min(limit, num_records)
            assert len(records) <= expected_max, (
                f"Retrieved {len(records)} records, expected at most {expected_max}"
            )

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(max_size=50),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=25, deadline=2000)
    def test_retrieval_without_storage_backend_returns_empty_invariant(
        self, test_data: dict[str, Any]
    ) -> None:
        """Invariant: Retrieval without backend uses in-memory storage.

        Business Case: Graceful degradation when storage unavailable -
        in-memory storage provides temporary resilience.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create BronzeLayer WITHOUT storage backend
            bronze_layer = BronzeLayer(storage_path=Path(temp_dir) / "bronze")

            # Ingest data
            metadata = LayerMetadata(
                source_path=Path("test.json"),
                layer_name="bronze",
                ingestion_timestamp=datetime.now(),
            )
            result = bronze_layer.ingest(test_data, metadata)

            # Attempt retrieval - should work due to in-memory storage defaults
            records = bronze_layer.get_bronze_records()

            # INVARIANT: In-memory storage provides graceful degradation
            # If ingestion succeeded, data should be retrievable from memory
            if result.status == ProcessingStatus.COMPLETED:
                assert len(records) > 0, (
                    "Successful ingestion should make data retrievable "
                    "from in-memory storage"
                )
            else:
                # If ingestion failed, retrieval should be empty
                assert len(records) == 0, (
                    "Failed ingestion should result in empty retrieval"
                )

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(max_size=50),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=20, deadline=3000)
    def test_ingestion_success_implies_retrievability_invariant(
        self, test_data: dict[str, Any]
    ) -> None:
        """Invariant: Successful ingestion implies data is retrievable.

        Business Case: Data persistence guarantee.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            metadata = LayerMetadata(
                source_path=Path("test.json"),
                layer_name="bronze",
                ingestion_timestamp=datetime.now(),
            )

            result = bronze_layer.ingest(test_data, metadata)

            if result.status == ProcessingStatus.COMPLETED:
                # INVARIANT: Completed ingestion means data is retrievable
                records = bronze_layer.get_bronze_records()
                assert len(records) > 0, (
                    "Successful ingestion should make data retrievable"
                )

    @given(st.lists(st.integers(min_value=1, max_value=100), min_size=2, max_size=10))
    @settings(max_examples=15, deadline=3000)
    def test_multiple_retrievals_same_data_invariant(self, limits: list[int]) -> None:
        """Invariant: Multiple retrievals return same data (idempotent).

        Business Case: Query results should be stable/repeatable.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Ingest 20 records
            for i in range(20):
                test_data = {"test": f"data_{i}", "index": i}
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            # Retrieve multiple times with same limit
            limit = limits[0]
            first_retrieval = bronze_layer.get_bronze_records(limit=limit)
            second_retrieval = bronze_layer.get_bronze_records(limit=limit)

            # INVARIANT: Multiple retrievals return same count
            assert len(first_retrieval) == len(second_retrieval), (
                "Multiple retrievals should return same number of records"
            )

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(max_size=50),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=20, deadline=2000)
    def test_retrieved_records_have_required_structure_invariant(
        self, test_data: dict[str, Any]
    ) -> None:
        """Invariant: All retrieved records have BronzeRecord structure.

        Business Case: Type safety - consumers can rely on record structure.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            metadata = LayerMetadata(
                source_path=Path("test.json"),
                layer_name="bronze",
                ingestion_timestamp=datetime.now(),
            )
            bronze_layer.ingest(test_data, metadata)

            records = bronze_layer.get_bronze_records()

            # INVARIANT: All records have required BronzeRecord structure
            for record in records:
                assert hasattr(record, "data"), "Record missing 'data' attribute"
                assert hasattr(record, "metadata"), (
                    "Record missing 'metadata' attribute"
                )
                assert hasattr(record, "format_detection"), (
                    "Record missing 'format_detection' attribute"
                )
                assert hasattr(record, "lineage"), "Record missing 'lineage' attribute"
                assert isinstance(record.data, dict), "Record data must be dict"

    @given(st.integers(min_value=1, max_value=20))
    @settings(max_examples=15, deadline=3000)
    def test_storage_persistence_across_instances_invariant(
        self, num_records: int
    ) -> None:
        """Invariant: Data persists across BronzeLayer instance recreation.

        Business Case: System restarts shouldn't lose data.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}

            # First instance: ingest data
            storage_backend_1 = LocalStorageBackend(storage_config)
            bronze_layer_1 = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend_1,
            )

            for i in range(num_records):
                test_data = {"test": f"data_{i}"}
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer_1.ingest(test_data, metadata)

            # Second instance: retrieve data
            storage_backend_2 = LocalStorageBackend(storage_config)
            bronze_layer_2 = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze2",
                storage_backend=storage_backend_2,
            )

            records = bronze_layer_2.get_bronze_records(limit=num_records + 10)

            # INVARIANT: Data persists across instances
            assert len(records) == num_records, (
                f"Expected {num_records} persisted records, got {len(records)}"
            )

    @given(
        st.lists(
            st.sampled_from(["zephyr", "testlink", "unknown"]),
            min_size=1,
            max_size=6,
        ),
        st.sampled_from(
            ["zephyr", "ZEPHYR", "ZePhYr", "testlink", "TESTLINK", "unknown"]
        ),
    )
    @settings(max_examples=25, deadline=2500)
    def test_format_type_filter_case_insensitive_invariant(
        self, format_sequence: list[str], filter_value: str
    ) -> None:
        """Invariant: Format-type filters are case-insensitive for known handlers."""

        def _sample_data(fmt: str) -> dict[str, Any]:
            if fmt.lower() == "zephyr":
                return {
                    "testCase": {"name": "Zephyr Case", "steps": [{"action": "A"}]},
                    "execution": {"status": "PASS"},
                    "cycle": {"name": "Cycle"},
                }
            if fmt.lower() == "testlink":
                return {
                    "testsuites": {
                        "testsuite": [
                            {"name": "TL Suite", "testcase": [{"name": "Case"}]}
                        ]
                    }
                }
            return {"misc": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            for idx, fmt in enumerate(format_sequence):
                metadata = LayerMetadata(
                    source_path=Path(f"case_{fmt}_{idx}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(_sample_data(fmt), metadata)

            records = bronze_layer.get_bronze_records(
                filter_criteria={"format_type": filter_value}
            )

            expected_count = sum(
                1 for fmt in format_sequence if fmt.lower() == filter_value.lower()
            )
            assert len(records) == expected_count

            for record in records:
                detected = record.format_detection.detected_format
                assert isinstance(detected, SupportedFormat)
                if expected_count:
                    assert detected.value.lower() == filter_value.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
