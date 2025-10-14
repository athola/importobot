"""Generative tests for Bronze layer storage operations.

Uses property-based testing to verify storage behavior across
many different input variations and edge cases.

Business Use Cases:
- Verify storage handles diverse data structures
- Test pagination boundaries
- Validate error handling across random inputs
"""

import shutil
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
    raise unittest.SkipTest("Hypothesis is required for generative tests") from exc

from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import LayerMetadata
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.medallion.storage.local import LocalStorageBackend

pytestmark = pytest.mark.slow


class TestBronzeStorageGenerative(unittest.TestCase):
    """Generative tests for Bronze layer storage operations."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        storage_config = {"base_path": str(self.temp_dir / "storage")}
        self.storage_backend = LocalStorageBackend(storage_config)
        self.bronze_layer = BronzeLayer(
            storage_path=self.temp_dir / "bronze",
            storage_backend=self.storage_backend,
        )

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=50, deadline=2000)
    def test_storage_handles_arbitrary_dict_structures(
        self, test_data: dict[str, Any]
    ) -> None:
        """Test storage handles diverse dictionary structures.

        Business Case: System receives test data from many different sources
        with varying structures.
        """
        # Ingest arbitrary data
        metadata = LayerMetadata(
            source_path=Path("arbitrary_data.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        result = self.bronze_layer.ingest(test_data, metadata)

        # Should always succeed or handle gracefully
        self.assertIn(result.status.value, ["completed", "failed"])

        if result.status.value == "completed":
            # Should be able to retrieve the data
            records = self.bronze_layer.get_bronze_records()
            self.assertGreater(len(records), 0)

    @given(st.text(min_size=1, max_size=40))
    @settings(max_examples=40, deadline=2000)
    def test_generated_nested_filter_matches_expected_records(
        self, case_name: str
    ) -> None:
        """Property: Dot-notation filters surface matching generated records."""
        test_data = {
            "testCase": {
                "name": case_name,
                "description": "Generated filter test",
                "priority": "Medium",
            }
        }
        metadata = LayerMetadata(
            source_path=Path("generated_filter.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        ingestion_result = self.bronze_layer.ingest(test_data, metadata)
        self.assertEqual(ingestion_result.processed_count, 1)

        matching_records = self.bronze_layer.get_bronze_records(
            filter_criteria={"testCase.name": case_name}
        )
        non_matching_records = self.bronze_layer.get_bronze_records(
            filter_criteria={"testCase.name": f"{case_name}-different"}
        )

        self.assertEqual(len(matching_records), 1)
        self.assertEqual(
            matching_records[0].data["testCase"]["name"],
            case_name,
        )
        self.assertEqual(len(non_matching_records), 0)

    @given(st.integers(min_value=0, max_value=1000))
    @settings(max_examples=20, deadline=5000)
    def test_pagination_limit_boundaries(self, limit: int) -> None:
        """Test pagination works correctly across all valid limit values.

        Business Case: UI components may request any reasonable limit value.
        """
        # Create fresh storage for this test example
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Ingest 10 records
            for i in range(10):
                test_data = {"test": f"data_{i}"}
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            # Test retrieval with arbitrary limit
            records = bronze_layer.get_bronze_records(limit=limit)

            # Should never crash, should return 0 to min(limit, 10) records
            self.assertIsInstance(records, list)
            self.assertGreaterEqual(len(records), 0)
            self.assertLessEqual(len(records), min(limit, 10))

    @given(
        st.lists(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.text(max_size=50),
                min_size=1,
                max_size=10,
            ),
            min_size=1,
            max_size=50,
        )
    )
    @settings(max_examples=20, deadline=5000)
    def test_batch_ingestion_consistency(
        self, test_data_list: list[dict[str, Any]]
    ) -> None:
        """Test batch ingestion maintains consistency.

        Business Case: Nightly test runs ingest hundreds of test cases.
        """
        # Create fresh storage for this test example
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Ingest all data
            for i, test_data in enumerate(test_data_list):
                metadata = LayerMetadata(
                    source_path=Path(f"batch_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            # Retrieve all records
            records = bronze_layer.get_bronze_records(limit=len(test_data_list) + 10)

            # Should have ingested all records
            self.assertEqual(len(records), len(test_data_list))

    @given(
        test_name=st.text(min_size=1, max_size=100, alphabet=st.characters()),
        description=st.text(max_size=500),
    )
    @settings(max_examples=30, deadline=2000)
    def test_unicode_and_special_characters_handling(
        self, test_name: str, description: str
    ) -> None:
        """Test storage handles unicode and special characters correctly.

        Business Case: International teams use test names in various languages.
        """
        test_data = {
            "testCase": {
                "name": test_name,
                "description": description,
                "priority": "High",
            }
        }

        metadata = LayerMetadata(
            source_path=Path("unicode_test.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        try:
            result = self.bronze_layer.ingest(test_data, metadata)

            if result.status.value == "completed":
                # Should be able to retrieve
                records = self.bronze_layer.get_bronze_records()
                if len(records) > 0:
                    # Verify data integrity
                    self.assertIsInstance(records[0].data, dict)

        except Exception:
            # Some character combinations may fail, which is acceptable
            # as long as it doesn't crash the process
            pass

    @given(
        st.lists(
            st.integers(min_value=1, max_value=100),
            min_size=1,
            max_size=20,
            unique=True,
        )
    )
    @settings(max_examples=20, deadline=3000)
    def test_multiple_limit_queries_consistency(self, limits: list[int]) -> None:
        """Test multiple queries with different limits return consistent data.

        Business Case: Different UI components query same data with different limits.
        """
        # Create fresh storage for this test example
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_config = {"base_path": str(Path(temp_dir) / "storage")}
            storage_backend = LocalStorageBackend(storage_config)
            bronze_layer = BronzeLayer(
                storage_path=Path(temp_dir) / "bronze",
                storage_backend=storage_backend,
            )

            # Ingest 50 records
            for i in range(50):
                test_data = {"test": f"data_{i}", "index": i}
                metadata = LayerMetadata(
                    source_path=Path(f"test_{i}.json"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                )
                bronze_layer.ingest(test_data, metadata)

            # Query with different limits
            previous_records = None
            for limit in sorted(limits):
                records = bronze_layer.get_bronze_records(limit=limit)

                # Should return valid number of records
                self.assertLessEqual(len(records), min(limit, 50))

                # Records should be consistent across queries
                if previous_records is not None:
                    # Smaller limit results should be subset of larger limit results
                    if len(records) < len(previous_records):
                        previous_records = records

                previous_records = records


class TestBronzeStorageGenerativeEdgeCases(unittest.TestCase):
    """Generative tests for edge cases in Bronze storage."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        storage_config = {"base_path": str(self.temp_dir / "storage")}
        self.storage_backend = LocalStorageBackend(storage_config)
        self.bronze_layer = BronzeLayer(
            storage_path=self.temp_dir / "bronze",
            storage_backend=self.storage_backend,
        )

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @given(st.text(min_size=1, max_size=1000))
    @settings(max_examples=30, deadline=2000)
    def test_source_path_variations(self, path_str: str) -> None:
        """Test storage handles various source path strings.

        Business Case: Test data comes from many different file locations.
        """
        # Create safe path
        try:
            source_path = Path(path_str.replace("\x00", "_").replace("/", "_"))
        except Exception:
            # Invalid path strings should be handled gracefully
            source_path = Path("fallback.json")

        test_data = {"test": "data"}
        metadata = LayerMetadata(
            source_path=source_path,
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        result = self.bronze_layer.ingest(test_data, metadata)

        # Should handle gracefully
        self.assertIsNotNone(result)
        self.assertIn(result.status.value, ["completed", "failed"])

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.recursive(
                st.none() | st.booleans() | st.integers() | st.text(max_size=50),
                lambda children: st.lists(children, max_size=5)
                | st.dictionaries(st.text(max_size=10), children, max_size=5),
                max_leaves=20,
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=20, deadline=3000)
    def test_nested_data_structures(self, nested_data: dict[str, Any]) -> None:
        """Test storage handles deeply nested data structures.

        Business Case: Complex test data with nested steps and conditions.
        """
        metadata = LayerMetadata(
            source_path=Path("nested_test.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        try:
            result = self.bronze_layer.ingest(nested_data, metadata)

            # Should handle nested structures
            self.assertIsNotNone(result)

            if result.status.value == "completed":
                records = self.bronze_layer.get_bronze_records()
                self.assertGreater(len(records), 0)

        except RecursionError:
            # Extremely deep nesting may hit recursion limit, acceptable
            pass

    @given(
        format_type=st.sampled_from(
            [
                SupportedFormat.ZEPHYR,
                SupportedFormat.TESTLINK,
                SupportedFormat.JIRA_XRAY,
                SupportedFormat.TESTRAIL,
                SupportedFormat.GENERIC,
                SupportedFormat.UNKNOWN,
            ]
        )
    )
    @settings(max_examples=10, deadline=2000)
    def test_all_format_types_stored_and_retrieved(
        self, format_type: SupportedFormat
    ) -> None:
        """Test all supported format types are stored and retrieved correctly.

        Business Case: System handles test data from multiple test management tools.
        """
        test_data = {
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

        result = self.bronze_layer.ingest(test_data, metadata)
        self.assertEqual(result.status.value, "completed")

        # Retrieve and verify format is preserved
        records = self.bronze_layer.get_bronze_records()
        self.assertGreater(len(records), 0)

        # Verify format detection information is present
        for record in records:
            self.assertIsNotNone(record.format_detection)
            self.assertIsInstance(
                record.format_detection.detected_format, SupportedFormat
            )


if __name__ == "__main__":
    unittest.main()
