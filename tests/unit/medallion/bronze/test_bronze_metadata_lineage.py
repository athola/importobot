"""Unit tests for BronzeLayer metadata and lineage retrieval."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from pathlib import Path

from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import LayerMetadata
from importobot.medallion.interfaces.records import BronzeRecord, RecordMetadata


class TestBronzeMetadataAndLineage(unittest.TestCase):
    """Verify BronzeLayer exposes stored metadata, lineage, and records."""

    def setUp(self) -> None:
        self.bronze_layer = BronzeLayer()
        self.sample_data = {
            "testCase": {
                "name": "Sanity Check",
                "description": "Smoke test for metadata retrieval",
            }
        }
        self.metadata = LayerMetadata(
            source_path=Path("tests/data/sample.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
            record_count=5,
            file_size_bytes=1024,
            custom_metadata={"team": "qa"},
        )

        # Ingest once for all tests to reuse the stored identifiers.
        self.processing_result = self.bronze_layer.ingest(
            self.sample_data, self.metadata
        )
        self.record_id = next(iter(self.bronze_layer._data_store))

    def test_get_record_metadata_returns_enhanced_metadata(self) -> None:
        """BronzeLayer should convert LayerMetadata into RecordMetadata."""
        retrieved = self.bronze_layer.get_record_metadata(self.record_id)

        self.assertIsNotNone(retrieved)
        assert retrieved is not None  # mypy type narrowing
        self.assertIsInstance(retrieved, RecordMetadata)
        self.assertEqual(retrieved.record_id, self.record_id)
        self.assertEqual(retrieved.source_system, str(self.metadata.source_path))
        self.assertEqual(retrieved.source_file_size, self.metadata.file_size_bytes)
        self.assertIn("record_count", retrieved.quality_checks)
        self.assertEqual(
            retrieved.custom_attributes["team"],
            self.metadata.custom_metadata["team"],
        )

    def test_get_record_metadata_returns_none_for_unknown_id(self) -> None:
        """BronzeLayer should return None when metadata is missing."""
        self.assertIsNone(self.bronze_layer.get_record_metadata("missing-id"))

    def test_get_record_lineage_maps_to_data_lineage(self) -> None:
        """Stored lineage info should map to DataLineage structure."""
        lineage = self.bronze_layer.get_record_lineage(self.record_id)

        self.assertIsNotNone(lineage)
        assert lineage is not None  # mypy type narrowing
        self.assertEqual(lineage.source_id, self.record_id)
        self.assertEqual(lineage.source_location, str(self.metadata.source_path))
        self.assertEqual(lineage.parent_records, [])
        self.assertGreaterEqual(len(lineage.transformation_history), 1)

    def test_get_bronze_records_filters_by_record_id(self) -> None:
        """Record retrieval should support filter criteria."""
        records = self.bronze_layer.get_bronze_records(
            filter_criteria={"record_id": self.record_id}
        )

        self.assertEqual(len(records), 1)
        self.assertIsInstance(records[0], BronzeRecord)
        self.assertEqual(records[0].metadata.record_id, self.record_id)

    def test_get_bronze_records_filters_by_nested_key(self) -> None:
        """Dot-notation filtering should work for nested data keys."""
        records = self.bronze_layer.get_bronze_records(
            filter_criteria={"testCase.name": "Sanity Check"}
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].data["testCase"]["name"], "Sanity Check")

    def test_get_bronze_records_respects_limit_zero(self) -> None:
        """Limit set to zero should short-circuit with no records."""
        records = self.bronze_layer.get_bronze_records(limit=0)
        self.assertEqual(records, [])

    def test_get_bronze_records_filters_by_ingestion_timestamp_range(self) -> None:
        """Temporal filters should be applied to metadata timestamps."""
        earlier = self.metadata.ingestion_timestamp - timedelta(days=1)
        later = self.metadata.ingestion_timestamp + timedelta(days=1)

        within_range = self.bronze_layer.get_bronze_records(
            filter_criteria={
                "ingestion_timestamp_after": earlier.isoformat(),
                "ingestion_timestamp_before": later.isoformat(),
            }
        )

        outside_range = self.bronze_layer.get_bronze_records(
            filter_criteria={"ingestion_timestamp_before": earlier.isoformat()}
        )

        self.assertEqual(len(within_range), 1)
        self.assertEqual(within_range[0].metadata.record_id, self.record_id)
        self.assertEqual(outside_range, [])

    def test_get_bronze_records_filters_by_format_type_case_insensitive(self) -> None:
        """Filtering by format type should ignore case via dispatch handlers."""
        records_lower = self.bronze_layer.get_bronze_records(
            filter_criteria={"format_type": "zephyr"}
        )
        records_upper = self.bronze_layer.get_bronze_records(
            filter_criteria={"format_type": "ZEPHYR"}
        )

        self.assertEqual(len(records_lower), 1)
        self.assertEqual(len(records_upper), 1)
        self.assertEqual(records_lower[0].metadata.record_id, self.record_id)
        self.assertEqual(records_upper[0].metadata.record_id, self.record_id)

    def test_get_bronze_records_filters_by_custom_metadata(self) -> None:
        """Custom metadata filters should surface through dispatch fallback."""
        matching = self.bronze_layer.get_bronze_records(
            filter_criteria={"custom_metadata.team": "qa"}
        )
        non_matching = self.bronze_layer.get_bronze_records(
            filter_criteria={"custom_metadata.team": "devops"}
        )

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].metadata.record_id, self.record_id)
        self.assertEqual(non_matching, [])


if __name__ == "__main__":
    unittest.main()
