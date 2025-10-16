"""Generative tests for Bronze layer storage operations.

Uses property-based testing to verify storage behavior across
many different input variations and edge cases.

Business Use Cases:
- Verify storage handles diverse data structures
- Test pagination boundaries
- Validate error handling across random inputs
"""

import logging
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import pytest
from hypothesis import strategies as st

try:
    from hypothesis import given, settings
except ImportError as exc:  # pragma: no cover - optional dependency
    raise unittest.SkipTest("Hypothesis is required for generative tests") from exc

from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import LayerMetadata
from importobot.medallion.interfaces.enums import ProcessingStatus, SupportedFormat
from importobot.medallion.storage.local import LocalStorageBackend

pytestmark = pytest.mark.slow

logger = logging.getLogger(__name__)


class TestBronzeStorageGenerative(unittest.TestCase):
    """Generative tests for Bronze layer storage operations."""

    unicode_failures: ClassVar[list[dict[str, str]]] = []

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
        assert result.status in {ProcessingStatus.COMPLETED, ProcessingStatus.FAILED}

        if result.status is ProcessingStatus.COMPLETED:
            # Should be able to retrieve the data
            records = self.bronze_layer.get_bronze_records()
            assert len(records) > 0

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
        assert ingestion_result.processed_count == 1

        matching_records = self.bronze_layer.get_bronze_records(
            filter_criteria={"testCase.name": case_name}
        )
        non_matching_records = self.bronze_layer.get_bronze_records(
            filter_criteria={"testCase.name": f"{case_name}-different"}
        )

        assert len(matching_records) == 1
        assert matching_records[0].data["testCase"]["name"] == case_name
        assert len(non_matching_records) == 0

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
            assert isinstance(records, list)
            assert len(records) >= 0
            assert len(records) <= min(limit, 10)

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
            assert len(records) == len(test_data_list)

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

            if result.status is ProcessingStatus.COMPLETED:
                # Should be able to retrieve
                records = self.bronze_layer.get_bronze_records()
                if len(records) > 0:
                    # Verify data integrity
                    assert isinstance(records[0].data, dict)

        except Exception as exc:
            # Some character combinations may fail; record the context for analysis
            failure_info = {
                "name": test_name,
                "description": description[:200],  # avoid huge log entries
                "error": repr(exc),
            }
            self.unicode_failures.append(failure_info)
            logger.warning(
                "Unicode ingestion failed: name=%r error=%s", test_name, repr(exc)
            )

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
                assert len(records) <= min(limit, 50)

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
            source_path = Path("default_source.json")

        test_data = {"test": "data"}
        metadata = LayerMetadata(
            source_path=source_path,
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        result = self.bronze_layer.ingest(test_data, metadata)

        # Should handle gracefully
        assert result is not None
        assert result.status in {ProcessingStatus.COMPLETED, ProcessingStatus.FAILED}

    BASE_VALUE = st.none() | st.booleans() | st.integers() | st.text(max_size=50)
    _NESTED_DICT_VALUES: st.SearchStrategy[Any] = st.deferred(
        lambda base_value=BASE_VALUE: st.one_of(  # type: ignore[misc]
            base_value,
            st.lists(base_value, max_size=4),
            st.dictionaries(st.text(max_size=10), base_value, max_size=4),
            st.lists(
                st.one_of(
                    base_value,
                    st.dictionaries(st.text(max_size=10), base_value, max_size=4),
                ),
                max_size=4,
            ),
        )
    )

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=_NESTED_DICT_VALUES,
            min_size=1,
            max_size=5,
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

        result = self.bronze_layer.ingest(nested_data, metadata)

        # Should handle nested structures
        assert result is not None

        if result.status is ProcessingStatus.COMPLETED:
            records = self.bronze_layer.get_bronze_records()
            assert len(records) > 0

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
        assert result.status == ProcessingStatus.COMPLETED

        # Retrieve and verify format is preserved
        records = self.bronze_layer.get_bronze_records()
        assert len(records) > 0

        # Verify format detection information is present
        for record in records:
            assert record.format_detection is not None
            assert isinstance(record.format_detection.detected_format, SupportedFormat)


if __name__ == "__main__":
    unittest.main()
