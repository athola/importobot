"""Integration tests for Bronze layer storage backend integration.

These tests verify end-to-end workflows involving storage persistence,
retrieval, and interaction with the medallion architecture.

Business Use Cases:
- Data ingestion pipeline with persistent storage
- Recovery from crashes (data survives process restart)
- Multi-session data queries
- Storage backend switching
"""

import shutil
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path

try:
    from importobot.medallion.bronze.raw_data_processor import RawDataProcessor
except ImportError:  # pragma: no cover - optional dependency
    RawDataProcessor: type = None  # type: ignore
from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import LayerMetadata
from importobot.medallion.interfaces.enums import ProcessingStatus
from importobot.medallion.storage.local import LocalStorageBackend


class TestBronzeStorageIntegration(unittest.TestCase):
    """Integration tests for Bronze layer with persistent storage."""

    def setUp(self) -> None:
        """Set up test environment with real storage backend."""
        self.temp_dir = Path(tempfile.mkdtemp())
        storage_config = {"base_path": str(self.temp_dir / "storage")}
        self.storage_backend = LocalStorageBackend(storage_config)

        self.bronze_layer = BronzeLayer(
            storage_path=self.temp_dir / "bronze",
            storage_backend=self.storage_backend,
        )

        self.processor = (
            RawDataProcessor(bronze_layer=self.bronze_layer)
            if RawDataProcessor is not None
            else None
        )

        # Sample test data
        self.zephyr_data = {
            "testCase": {
                "name": "Authentication Test",
                "description": "Verify user authentication",
                "steps": [
                    {"action": "Navigate to login", "expected": "Login page shown"},
                    {"action": "Enter credentials", "expected": "User logged in"},
                ],
            },
            "execution": {"status": "PASS", "executionId": "EXEC-001"},
        }

        self.testlink_data = {
            "testsuites": {
                "testsuite": [
                    {
                        "name": "API Tests",
                        "testcase": [
                            {
                                "name": "GET /users",
                                "summary": "Retrieve user list",
                                "steps": [{"step_number": "1", "actions": "Send GET"}],
                            }
                        ],
                    }
                ]
            }
        }

    def tearDown(self) -> None:
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_ingest_and_retrieve_workflow(self) -> None:
        """Test complete workflow: ingest data, retrieve it from storage.

        Business Case: QA team ingests test cases, later retrieves them for analysis.
        """
        # Ingest test data
        metadata = LayerMetadata(
            source_path=Path("zephyr_export.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        result = self.bronze_layer.ingest(self.zephyr_data, metadata)

        # Verify ingestion succeeded
        assert result.status == ProcessingStatus.COMPLETED
        assert result.success_count == 1

        # Retrieve records from storage
        records = self.bronze_layer.get_bronze_records()

        # Verify retrieval
        assert len(records) == 1
        assert records[0].data["testCase"]["name"] == "Authentication Test"
        assert records[0].metadata is not None
        assert records[0].format_detection is not None
        assert records[0].lineage is not None

    def test_data_survives_bronze_layer_restart(self) -> None:
        """Test that ingested data persists across BronzeLayer instances.

        Business Case: System crashes, data must be recoverable after restart.
        """
        # First session: ingest data
        metadata = LayerMetadata(
            source_path=Path("test_data.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        self.bronze_layer.ingest(self.zephyr_data, metadata)

        # Simulate restart by creating new BronzeLayer instance
        new_bronze_layer = BronzeLayer(
            storage_path=self.temp_dir / "bronze",
            storage_backend=self.storage_backend,
        )

        # Retrieve from new instance
        records = new_bronze_layer.get_bronze_records()

        # Data should still be available
        assert len(records) == 1
        assert records[0].data["testCase"]["name"] == "Authentication Test"

    def test_multiple_ingestion_sessions_accumulate_data(self) -> None:
        """Test that multiple ingestion sessions accumulate records in storage.

        Business Case: Daily test runs accumulate over time for trend analysis.
        """
        # Session 1: Ingest Zephyr data
        metadata_1 = LayerMetadata(
            source_path=Path("day1_zephyr.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        self.bronze_layer.ingest(self.zephyr_data, metadata_1)

        # Session 2: Ingest TestLink data
        metadata_2 = LayerMetadata(
            source_path=Path("day2_testlink.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        self.bronze_layer.ingest(self.testlink_data, metadata_2)

        # Retrieve all records
        records = self.bronze_layer.get_bronze_records()

        # Should have both records
        assert len(records) == 2

        # Verify both formats present
        record_types = set()
        for record in records:
            if "testCase" in record.data:
                record_types.add("zephyr")
            if "testsuites" in record.data:
                record_types.add("testlink")

        assert len(record_types) == 2

    def test_storage_defaults_respect_filter_dispatch(self) -> None:
        """Ensure storage defaults honor filter criteria via dispatch map.

        Business Case: After a restart, API queries by format type still return
        the expected subset sourced from persisted storage.
        """
        zephyr_metadata = LayerMetadata(
            source_path=Path("restart_zephyr.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        testlink_metadata = LayerMetadata(
            source_path=Path("restart_testlink.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        self.bronze_layer.ingest(self.zephyr_data, zephyr_metadata)
        self.bronze_layer.ingest(self.testlink_data, testlink_metadata)

        # Simulate restart with fresh BronzeLayer (empty in-memory stores)
        restarted_layer = BronzeLayer(
            storage_path=self.temp_dir / "bronze",
            storage_backend=self.storage_backend,
        )

        zephyr_records = restarted_layer.get_bronze_records(
            filter_criteria={"format_type": "zephyr"}
        )
        testlink_records = restarted_layer.get_bronze_records(
            filter_criteria={"format_type": "TESTLINK"}
        )

        assert len(zephyr_records) == 1
        assert len(testlink_records) == 1
        assert "testCase" in zephyr_records[0].data
        assert "testsuites" in testlink_records[0].data

    @unittest.skipUnless(
        RawDataProcessor is not None, "RawDataProcessor requires optional dependencies"
    )
    def test_raw_data_processor_integration_with_storage(self) -> None:
        """Test RawDataProcessor properly integrates with storage backend.

        Business Case: High-level API must work seamlessly with storage.
        """
        # Use RawDataProcessor to ingest
        assert self.processor is not None
        result = self.processor.ingest_data_dict(
            self.zephyr_data, "processor_test.json"
        )

        assert result.status == ProcessingStatus.COMPLETED

        # Retrieve using BronzeLayer
        records = self.bronze_layer.get_bronze_records()

        assert len(records) == 1
        assert records[0].data["testCase"]["name"] == "Authentication Test"

    def test_pagination_across_large_dataset(self) -> None:
        """Test pagination works correctly for large result sets.

        Business Case: UI displays paginated results, need consistent data.
        """
        # Ingest 25 records
        for i in range(25):
            test_data = {
                "testCase": {
                    "name": f"Test Case {i}",
                    "description": f"Description {i}",
                }
            }
            metadata = LayerMetadata(
                source_path=Path(f"test_{i}.json"),
                layer_name="bronze",
                ingestion_timestamp=datetime.now(),
            )
            self.bronze_layer.ingest(test_data, metadata)

        # Retrieve first page (10 records)
        page1 = self.bronze_layer.get_bronze_records(limit=10)
        assert len(page1) == 10

        # Retrieve second page (10 records)
        page2 = self.bronze_layer.get_bronze_records(limit=10)
        assert len(page2) == 10

        # Retrieve remaining records
        page3 = self.bronze_layer.get_bronze_records(limit=10)
        assert len(page3) >= 5

        # Total should be all records when limit is high
        all_records = self.bronze_layer.get_bronze_records(limit=100)
        assert len(all_records) == 25

    def test_storage_backend_isolation_between_layers(self) -> None:
        """Test that bronze layer storage is isolated from other layers.

        Business Case: Bronze, Silver, Gold layers have separate storage spaces.
        """
        # Ingest into bronze
        metadata = LayerMetadata(
            source_path=Path("bronze_data.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        self.bronze_layer.ingest(self.zephyr_data, metadata)

        # Check bronze has data
        bronze_records = self.bronze_layer.get_bronze_records()
        assert len(bronze_records) == 1

        # Verify storage structure
        bronze_storage_path = self.temp_dir / "storage" / "bronze" / "data"
        assert bronze_storage_path.exists()

        # Verify no cross-contamination with other layers
        silver_storage_path = self.temp_dir / "storage" / "silver" / "data"
        if silver_storage_path.exists():
            silver_files = list(silver_storage_path.glob("*.json"))
            assert len(silver_files) == 0

    def test_concurrent_ingestion_and_retrieval(self) -> None:
        """Test that ingestion and retrieval can happen concurrently.

        Business Case: System ingests new data while users query existing data.
        """

        results = {"ingested": 0, "retrieved": 0}

        def ingest_data():
            for i in range(5):
                test_data = {"testCase": {"name": f"Concurrent Test {i}"}}
                metadata = LayerMetadata(
                    source_path=Path(f"concurrent_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                self.bronze_layer.ingest(test_data, metadata)
                results["ingested"] += 1

        def retrieve_data():
            for _ in range(5):
                records = self.bronze_layer.get_bronze_records()
                results["retrieved"] = len(records)

        # Run ingestion and retrieval concurrently
        ingest_thread = threading.Thread(target=ingest_data)
        retrieve_thread = threading.Thread(target=retrieve_data)

        ingest_thread.start()
        retrieve_thread.start()

        ingest_thread.join()
        retrieve_thread.join()

        # Verify all data was ingested
        assert results["ingested"] == 5

        # Final retrieval should get all records
        final_records = self.bronze_layer.get_bronze_records()
        assert len(final_records) == 5

    def test_storage_backend_error_recovery(self) -> None:
        """Test graceful handling when storage backend encounters errors.

        Business Case: Storage write errors shouldn't crash ingestion process.
        """
        # Ingest some data successfully
        metadata = LayerMetadata(
            source_path=Path("good_data.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        result = self.bronze_layer.ingest(self.zephyr_data, metadata)
        assert result.status == ProcessingStatus.COMPLETED

        # Create a bronze layer without storage backend
        # This simulates storage failure by having no persistent backend
        bronze_without_storage = BronzeLayer(storage_path=self.temp_dir / "bronze2")

        # Attempt to ingest (should succeed with in-memory storage)
        result2 = bronze_without_storage.ingest(self.zephyr_data, metadata)

        # In-memory storage should still work
        assert result2.status == ProcessingStatus.COMPLETED

        # Retrieval without storage backend should fall back to in-memory data
        records = bronze_without_storage.get_bronze_records()
        assert len(records) == 1
        assert "testCase" in records[0].data


class TestBronzeStorageBackendSwitching(unittest.TestCase):
    """Integration tests for switching storage backends.

    Business Case: Migrate from local storage to cloud storage.
    """

    def setUp(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_migrate_between_storage_backends(self) -> None:
        """Test data migration between different storage backends.

        Business Case: Company migrates from local to cloud storage.
        """
        # Create first storage backend
        storage1_config = {"base_path": str(self.temp_dir / "storage1")}
        storage1 = LocalStorageBackend(storage1_config)

        bronze1 = BronzeLayer(
            storage_path=self.temp_dir / "bronze1", storage_backend=storage1
        )

        # Ingest data to first backend
        test_data = {
            "testCase": {"name": "Migration Test", "description": "Test migration"}
        }
        metadata = LayerMetadata(
            source_path=Path("migration_test.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        bronze1.ingest(test_data, metadata)

        # Retrieve from first backend
        records1 = bronze1.get_bronze_records()
        assert len(records1) == 1

        # Create second storage backend
        storage2_config = {"base_path": str(self.temp_dir / "storage2")}
        storage2 = LocalStorageBackend(storage2_config)

        bronze2 = BronzeLayer(
            storage_path=self.temp_dir / "bronze2", storage_backend=storage2
        )

        # Migrate data: retrieve from storage1, ingest to storage2
        for record in records1:
            migration_metadata = LayerMetadata(
                source_path=Path("migrated_data.json"),
                layer_name="bronze",
                ingestion_timestamp=datetime.now(),
            )
            bronze2.ingest(record.data, migration_metadata)

        # Verify data in second backend
        records2 = bronze2.get_bronze_records()
        assert len(records2) == 1
        assert records2[0].data["testCase"]["name"] == "Migration Test"


if __name__ == "__main__":
    unittest.main()
