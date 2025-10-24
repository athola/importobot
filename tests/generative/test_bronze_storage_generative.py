"""Targeted tests for Bronze layer storage operations.

These tests exercise the core behaviours that previously relied on
property-based generation while keeping execution time predictable.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import LayerMetadata
from importobot.medallion.interfaces.enums import ProcessingStatus, SupportedFormat
from importobot.medallion.storage.local import LocalStorageBackend

logger = logging.getLogger(__name__)


class TestBronzeStorageGenerative(unittest.TestCase):
    """Focused regression tests for Bronze layer storage behaviour."""

    unicode_failures: ClassVar[list[dict[str, str]]] = []

    def setUp(self) -> None:
        """Create an isolated storage environment for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        storage_config = {"base_path": str(self.temp_dir / "storage")}
        self.storage_backend = LocalStorageBackend(storage_config)
        self.bronze_layer = BronzeLayer(
            storage_path=self.temp_dir / "bronze",
            storage_backend=self.storage_backend,
        )

    def tearDown(self) -> None:
        """Clean up temporary storage."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @classmethod
    def tearDownClass(cls) -> None:
        """Log any unicode ingestion failures observed during the test run."""
        super().tearDownClass()
        if cls.unicode_failures:
            logger.warning(
                "Captured %d unicode ingestion failures: %s",
                len(cls.unicode_failures),
                cls.unicode_failures,
            )

    def _ingest_payload(self, payload: dict[str, Any], name: str) -> None:
        metadata = LayerMetadata(
            source_path=Path(f"{name}.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )
        result = self.bronze_layer.ingest(payload, metadata)
        assert result.status in {
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
        }

    def test_storage_handles_diverse_payloads(self) -> None:
        """Ensure the Bronze layer accepts a variety of record shapes."""
        payloads: list[dict[str, Any]] = [
            {"name": "alpha", "description": "Sample test"},
            {"value": 42, "flags": {"enabled": True, "retries": 3}},
            {"id": "abc-123", "score": 9.7, "tags": ["one", "two"]},
            {
                "metadata": {"owner": "QA", "priority": "High"},
                "steps": [{"description": "Do something"}],
            },
            {"items": [1, 2, 3], "optional": None},
        ]

        for index, payload in enumerate(payloads):
            self._ingest_payload(payload, f"payload_{index}")

        records = self.bronze_layer.get_bronze_records()
        assert len(records) >= 1

    def test_generated_nested_filter_matches_expected_records(self) -> None:
        """Dot-notation filters should surface matching generated records."""
        sample_names = ["smoke", "Regression-42", "Unicode Δ"]

        for name in sample_names:
            payload = {
                "testCase": {
                    "name": name,
                    "description": "Generated filter test",
                    "priority": "Medium",
                }
            }
            self._ingest_payload(payload, f"filter_{name}")

            matching = self.bronze_layer.get_bronze_records(
                filter_criteria={"testCase.name": name}
            )
            assert len(matching) == 1
            assert matching[0].data["testCase"]["name"] == name

            non_matching = self.bronze_layer.get_bronze_records(
                filter_criteria={"testCase.name": f"{name}-different"}
            )
            assert not non_matching

    def test_pagination_limit_boundaries(self) -> None:
        """Pagination should respect requested limits without errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            for i in range(10):
                bronze_layer.ingest(
                    {"test": f"data_{i}"},
                    LayerMetadata(
                        source_path=Path(f"test_{i}.json"),
                        layer_name="bronze",
                        ingestion_timestamp=datetime.now(),
                    ),
                )

            for limit in [0, 1, 5, 10, 20, 1000]:
                records = bronze_layer.get_bronze_records(limit=limit)
                assert isinstance(records, list)
                assert len(records) <= min(limit, 10)

    def test_batch_ingestion_consistency(self) -> None:
        """Sequential ingestion should handle multiple records reliably."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            batch_payload = [
                {"case": f"nightly_{i}", "value": str(i)} for i in range(5)
            ]

            for index, payload in enumerate(batch_payload):
                result = bronze_layer.ingest(
                    payload,
                    LayerMetadata(
                        source_path=Path(f"batch_{index}.json"),
                        layer_name="bronze",
                        ingestion_timestamp=datetime.now(),
                    ),
                )
                assert result.status is ProcessingStatus.COMPLETED

            records = bronze_layer.get_bronze_records()
            assert len(records) >= len(batch_payload)

    def test_source_path_variations(self) -> None:
        """Source paths with unusual characters should be handled safely."""
        paths = ["normal.json", "../escape.json", "unicode_Δ.json", "null\x00byte.json"]
        payload = {"test": "data"}

        for candidate in paths:
            safe_name = candidate.replace("\x00", "_").replace("/", "_")
            metadata = LayerMetadata(
                source_path=Path(safe_name),
                layer_name="bronze",
                ingestion_timestamp=datetime.now(),
            )

            result = self.bronze_layer.ingest(payload, metadata)
            assert result.status in {
                ProcessingStatus.COMPLETED,
                ProcessingStatus.FAILED,
            }

    def test_nested_data_structures(self) -> None:
        """Ensure deeply nested structures are accepted."""
        nested_payload = {
            "suite": {
                "name": "Complex Suite",
                "cases": [
                    {
                        "name": "Scenario A",
                        "steps": [
                            {"description": "First", "data": {"key": "value"}},
                            {"description": "Second", "data": [1, 2, 3]},
                        ],
                    }
                ],
            }
        }

        self._ingest_payload(nested_payload, "nested")
        records = self.bronze_layer.get_bronze_records()
        assert records

    def test_all_format_types_stored_and_retrieved(self) -> None:
        """Every SupportedFormat should be persisted with detection metadata."""
        for format_type in [
            SupportedFormat.ZEPHYR,
            SupportedFormat.TESTLINK,
            SupportedFormat.JIRA_XRAY,
            SupportedFormat.TESTRAIL,
            SupportedFormat.GENERIC,
            SupportedFormat.UNKNOWN,
        ]:
            payload = {
                "testCase": {
                    "name": f"Test for {format_type.value}",
                    "format": format_type.value,
                }
            }
            metadata = LayerMetadata(
                source_path=Path(f"{format_type.value}_test.json"),
                layer_name="bronze",
                ingestion_timestamp=datetime.now(),
                format_type=format_type,
            )

            result = self.bronze_layer.ingest(payload, metadata)
            assert result.status == ProcessingStatus.COMPLETED

            records = self.bronze_layer.get_bronze_records()
            assert records
            for record in records:
                assert record.format_detection is not None
                assert isinstance(
                    record.format_detection.detected_format, SupportedFormat
                )


if __name__ == "__main__":  # pragma: no cover - manual execution
    unittest.main()
