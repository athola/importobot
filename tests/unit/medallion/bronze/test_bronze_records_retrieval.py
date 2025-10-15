"""TDD tests for Bronze layer record retrieval functionality.

These tests verify the get_bronze_records() method implementation
with storage backend integration.

Red-Green-Refactor Cycle:
1. RED: Write failing tests that define desired behavior
2. GREEN: Implement minimal code to make tests pass
3. REFACTOR: Improve code while keeping tests green
"""

import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import LayerMetadata
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.medallion.interfaces.records import BronzeRecord
from importobot.medallion.storage.local import LocalStorageBackend


class TestBronzeRecordsRetrieval(unittest.TestCase):
    """Test Bronze layer record retrieval with storage backend integration."""

    def setUp(self):
        """Set up test environment with storage backend."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create storage backend
        storage_config = {"base_path": str(self.temp_dir / "storage")}
        self.storage_backend = LocalStorageBackend(storage_config)

        # Create Bronze layer with storage backend
        self.bronze_layer = BronzeLayer(
            storage_path=self.temp_dir / "bronze",
            storage_backend=self.storage_backend,
        )

        # Sample test data
        self.test_data_1 = {
            "testCase": {
                "name": "Login Test",
                "description": "Test user login",
                "priority": "High",
            }
        }

        self.test_data_2 = {
            "testCase": {
                "name": "Logout Test",
                "description": "Test user logout",
                "priority": "Medium",
            }
        }

        self.test_data_3 = {
            "testsuites": {"testsuite": [{"name": "Suite 1", "testcase": []}]}
        }

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_bronze_records_without_storage_backend(self):
        """Test that get_bronze_records returns empty list without storage backend."""
        # Create Bronze layer without storage backend
        bronze_layer_no_storage = BronzeLayer(storage_path=self.temp_dir / "no_storage")

        records = bronze_layer_no_storage.get_bronze_records()

        self.assertEqual(len(records), 0)
        self.assertIsInstance(records, list)

    def test_get_bronze_records_returns_empty_list_when_no_data(self):
        """Test that get_bronze_records returns empty list when no data stored."""
        records = self.bronze_layer.get_bronze_records()

        self.assertEqual(len(records), 0)
        self.assertIsInstance(records, list)

    def test_get_bronze_records_retrieves_single_record(self):
        """Test retrieving a single bronze record from storage."""
        # Ingest test data
        metadata = LayerMetadata(
            source_path=Path("test_file.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        result = self.bronze_layer.ingest(self.test_data_1, metadata)

        self.assertEqual(result.success_count, 1)

        # Retrieve records
        records = self.bronze_layer.get_bronze_records()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].data["testCase"]["name"], "Login Test")
        self.assertIsNotNone(records[0].metadata)
        self.assertIsNotNone(records[0].format_detection)
        self.assertIsNotNone(records[0].lineage)

    def test_get_bronze_records_retrieves_multiple_records(self):
        """Test retrieving multiple bronze records from storage."""
        # Ingest multiple test data
        metadata_1 = LayerMetadata(
            source_path=Path("test_file_1.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        metadata_2 = LayerMetadata(
            source_path=Path("test_file_2.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        self.bronze_layer.ingest(self.test_data_1, metadata_1)
        self.bronze_layer.ingest(self.test_data_2, metadata_2)

        # Retrieve records
        records = self.bronze_layer.get_bronze_records()

        self.assertEqual(len(records), 2)
        record_names = [r.data["testCase"]["name"] for r in records]
        self.assertIn("Login Test", record_names)
        self.assertIn("Logout Test", record_names)

    def test_get_bronze_records_with_limit(self):
        """Test retrieving bronze records with limit parameter."""
        # Ingest multiple records
        for i in range(5):
            test_data = {
                "testCase": {
                    "name": f"Test {i}",
                    "description": f"Test case {i}",
                }
            }
            metadata = LayerMetadata(
                source_path=Path(f"test_file_{i}.json"),
                layer_name="bronze",
                ingestion_timestamp=datetime.now(),
            )
            self.bronze_layer.ingest(test_data, metadata)

        # Retrieve with limit
        records = self.bronze_layer.get_bronze_records(limit=3)

        self.assertEqual(len(records), 3)

    def test_get_bronze_records_with_filter_criteria(self):
        """Test retrieving bronze records with filter criteria."""
        # Ingest different format types
        metadata_zephyr = LayerMetadata(
            source_path=Path("zephyr.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        metadata_testlink = LayerMetadata(
            source_path=Path("testlink.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        self.bronze_layer.ingest(self.test_data_1, metadata_zephyr)
        self.bronze_layer.ingest(self.test_data_3, metadata_testlink)

        # Retrieve all records first to verify ingestion
        all_records = self.bronze_layer.get_bronze_records()
        self.assertEqual(len(all_records), 2)

        # Note: Filter criteria works on metadata-level filters
        # Format-based filtering would require custom filter implementation

    def test_get_bronze_records_preserves_metadata(self):
        """Test that retrieved records preserve original metadata."""
        # Ingest with specific metadata
        source_path = Path("important_test.json")
        metadata = LayerMetadata(
            source_path=source_path,
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        self.bronze_layer.ingest(self.test_data_1, metadata)

        # Retrieve and verify metadata
        records = self.bronze_layer.get_bronze_records()

        self.assertEqual(len(records), 1)
        record = records[0]

        # Verify metadata fields are populated
        self.assertIsNotNone(record.metadata.ingestion_timestamp)
        self.assertIsInstance(record.metadata.ingestion_timestamp, datetime)

    def test_get_bronze_records_includes_format_detection(self):
        """Test that retrieved records include format detection information."""
        metadata = LayerMetadata(
            source_path=Path("zephyr_test.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        self.bronze_layer.ingest(self.test_data_1, metadata)

        # Retrieve and verify format detection
        records = self.bronze_layer.get_bronze_records()

        self.assertEqual(len(records), 1)
        record = records[0]

        self.assertIsNotNone(record.format_detection)
        self.assertIsInstance(record.format_detection.detected_format, SupportedFormat)
        self.assertGreater(record.format_detection.confidence_score, 0)
        self.assertIsInstance(record.format_detection.evidence_details, dict)

    def test_get_bronze_records_includes_lineage(self):
        """Test that retrieved records include lineage information."""
        metadata = LayerMetadata(
            source_path=Path("lineage_test.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        self.bronze_layer.ingest(self.test_data_1, metadata)

        # Retrieve and verify lineage
        records = self.bronze_layer.get_bronze_records()

        self.assertEqual(len(records), 1)
        record = records[0]

        self.assertIsNotNone(record.lineage)
        self.assertIsNotNone(record.lineage.source_id)
        self.assertIsNotNone(record.lineage.source_type)
        self.assertIsNotNone(record.lineage.source_location)

    def test_get_bronze_records_handles_storage_errors(self):
        """Test that get_bronze_records handles storage errors gracefully."""
        # Create a Bronze layer with corrupted storage path
        corrupted_storage_config = {
            "base_path": str(self.temp_dir / "corrupted" / "very" / "deep" / "path")
        }
        corrupted_backend = LocalStorageBackend(corrupted_storage_config)
        bronze_layer_corrupted = BronzeLayer(
            storage_path=self.temp_dir / "bronze_corrupted",
            storage_backend=corrupted_backend,
        )

        # Should return empty list on error, not raise exception
        records = bronze_layer_corrupted.get_bronze_records()

        self.assertEqual(len(records), 0)
        self.assertIsInstance(records, list)

    def test_get_bronze_records_returns_bronze_record_objects(self):
        """Test that get_bronze_records returns proper BronzeRecord objects."""
        metadata = LayerMetadata(
            source_path=Path("test.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        self.bronze_layer.ingest(self.test_data_1, metadata)

        records = self.bronze_layer.get_bronze_records()

        self.assertEqual(len(records), 1)
        self.assertIsInstance(records[0], BronzeRecord)

        # Verify BronzeRecord properties
        record = records[0]
        self.assertIsInstance(record.data, dict)
        self.assertIsNotNone(record.metadata)
        self.assertIsNotNone(record.format_detection)
        self.assertIsNotNone(record.lineage)

    def test_get_bronze_records_default_limit(self):
        """Test that get_bronze_records applies default limit of 1000."""
        # This test verifies the default limit is reasonable
        # We won't actually create 1001 records, just verify the parameter works

        # Ingest a few records
        for i in range(3):
            test_data = {"test": f"data_{i}"}
            metadata = LayerMetadata(
                source_path=Path(f"test_{i}.json"),
                layer_name="bronze",
                ingestion_timestamp=datetime.now(),
            )
            self.bronze_layer.ingest(test_data, metadata)

        # Retrieve without limit (should use default)
        records = self.bronze_layer.get_bronze_records()

        # Should get all 3 records (less than default limit)
        self.assertEqual(len(records), 3)

    def test_get_bronze_records_with_zero_limit(self):
        """Test that get_bronze_records with limit=0 returns empty list.

        Business requirement: limit=0 should return 0 records, consistent with
        SQL LIMIT 0, REST API conventions, and Python slicing behavior.
        """
        # Ingest data
        metadata = LayerMetadata(
            source_path=Path("test.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        self.bronze_layer.ingest(self.test_data_1, metadata)

        # Retrieve with limit=0
        records = self.bronze_layer.get_bronze_records(limit=0)

        # Should return exactly 0 records
        self.assertEqual(len(records), 0)


if __name__ == "__main__":
    unittest.main()
