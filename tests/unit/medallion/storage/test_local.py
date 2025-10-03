"""Tests for local filesystem storage backend."""

import json
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from importobot.medallion.interfaces.data_models import (
    LayerData,
    LayerMetadata,
    LayerQuery,
)
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.medallion.storage.local import LocalStorageBackend


# Shared fixtures for all test classes
@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def storage_backend(temp_dir):
    """Create a LocalStorageBackend instance for testing."""
    config = {"base_path": str(temp_dir)}
    return LocalStorageBackend(config)


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    return LayerMetadata(
        source_path=Path("/test/source.json"),
        layer_name="bronze",
        ingestion_timestamp=datetime.now(),
        processing_timestamp=datetime.now(),
        data_hash="test_hash_123",
        version="1.0",
        format_type=SupportedFormat.UNKNOWN,
        record_count=10,
        file_size_bytes=1024,
        processing_duration_ms=100.5,
        user_id="test_user",
        session_id="test_session",
        custom_metadata={"test_key": "test_value"},
    )


@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    return {
        "test_cases": [
            {"id": "TC001", "name": "Test Case 1", "status": "passed"},
            {"id": "TC002", "name": "Test Case 2", "status": "failed"},
        ],
        "summary": {"total": 2, "passed": 1, "failed": 1},
    }


# Tests internal implementation details - protected-access needed
# pylint: disable=protected-access
class TestLocalStorageInit:
    """Test LocalStorageBackend initialization."""

    def test_init_default_config(self, temp_dir):
        """Test initialization with default configuration."""
        config = {"base_path": str(temp_dir)}
        backend = LocalStorageBackend(config)

        assert backend.base_path == temp_dir
        assert backend.create_compression is False
        assert backend.auto_backup is False

        # Check directory structure was created
        for layer in ["bronze", "silver", "gold"]:
            assert (temp_dir / layer).exists()
            assert (temp_dir / layer / "data").exists()
            assert (temp_dir / layer / "metadata").exists()

    def test_init_custom_config(self, temp_dir):
        """Test initialization with custom configuration."""
        config = {
            "base_path": str(temp_dir),
            "compression": True,
            "auto_backup": True,
        }
        backend = LocalStorageBackend(config)

        assert backend.create_compression is True
        assert backend.auto_backup is True


# pylint: disable=protected-access
class TestLocalStorageDataOps:
    """Test basic data operations (store, retrieve, delete)."""

    def test_store_data_success(self, storage_backend, sample_data, sample_metadata):
        """Test successful data storage."""
        result = storage_backend.store_data(
            layer_name="bronze",
            data_id="test_001",
            data=sample_data,
            metadata=sample_metadata,
        )

        assert result is True

        # Verify files were created
        data_file = storage_backend.base_path / "bronze" / "data" / "test_001.json"
        metadata_file = (
            storage_backend.base_path / "bronze" / "metadata" / "test_001.json"
        )

        assert data_file.exists()
        assert metadata_file.exists()

        # Verify data content
        with open(data_file, "r", encoding="utf-8") as f:
            stored_data = json.load(f)
        assert stored_data == sample_data

        # Verify metadata content
        with open(metadata_file, "r", encoding="utf-8") as f:
            stored_metadata = json.load(f)
        assert stored_metadata["layer_name"] == "bronze"
        assert stored_metadata["data_hash"] == "test_hash_123"

    def test_store_data_failure(self, storage_backend, sample_data, sample_metadata):
        """Test data storage failure handling."""
        # Mock json.dump to raise an exception
        with patch("json.dump", side_effect=OSError("Disk full")):
            result = storage_backend.store_data(
                layer_name="bronze",
                data_id="test_001",
                data=sample_data,
                metadata=sample_metadata,
            )

            assert result is False

    def test_retrieve_data_success(self, storage_backend, sample_data, sample_metadata):
        """Test successful data retrieval."""
        # First store the data
        storage_backend.store_data(
            layer_name="bronze",
            data_id="test_001",
            data=sample_data,
            metadata=sample_metadata,
        )

        # Then retrieve it
        result = storage_backend.retrieve_data("bronze", "test_001")

        assert result is not None
        data, metadata = result

        assert data == sample_data
        assert metadata.layer_name == "bronze"
        assert metadata.data_hash == "test_hash_123"
        assert metadata.version == "1.0"
        assert metadata.format_type == SupportedFormat.UNKNOWN

    def test_retrieve_data_not_found(self, storage_backend):
        """Test data retrieval when data doesn't exist."""
        result = storage_backend.retrieve_data("bronze", "nonexistent")
        assert result is None

    def test_retrieve_data_missing_files(
        self, storage_backend, sample_data, sample_metadata
    ):
        """Test data retrieval when files are missing."""
        # Store data first
        storage_backend.store_data(
            layer_name="bronze",
            data_id="test_001",
            data=sample_data,
            metadata=sample_metadata,
        )

        # Remove data file
        data_file = storage_backend.base_path / "bronze" / "data" / "test_001.json"
        data_file.unlink()

        result = storage_backend.retrieve_data("bronze", "test_001")
        assert result is None

    def test_retrieve_data_corrupted_metadata(
        self, storage_backend, sample_data, sample_metadata
    ):
        """Test data retrieval with corrupted metadata."""
        # Store data first
        storage_backend.store_data(
            layer_name="bronze",
            data_id="test_001",
            data=sample_data,
            metadata=sample_metadata,
        )

        # Corrupt metadata file
        metadata_file = (
            storage_backend.base_path / "bronze" / "metadata" / "test_001.json"
        )
        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        result = storage_backend.retrieve_data("bronze", "test_001")
        assert result is None

    def test_delete_data_success(self, storage_backend, sample_data, sample_metadata):
        """Test successful data deletion."""
        # Store data first
        storage_backend.store_data(
            layer_name="bronze",
            data_id="test_001",
            data=sample_data,
            metadata=sample_metadata,
        )

        # Delete it
        result = storage_backend.delete_data("bronze", "test_001")
        assert result is True

        # Verify files are gone
        data_file = storage_backend.base_path / "bronze" / "data" / "test_001.json"
        metadata_file = (
            storage_backend.base_path / "bronze" / "metadata" / "test_001.json"
        )

        assert not data_file.exists()
        assert not metadata_file.exists()

    def test_delete_data_not_found(self, storage_backend):
        """Test deleting non-existent data."""
        result = storage_backend.delete_data("bronze", "nonexistent")
        assert result is False

    def test_delete_data_partial(self, storage_backend, sample_data, sample_metadata):
        """Test deleting data when only one file exists."""
        # Store data first
        storage_backend.store_data(
            layer_name="bronze",
            data_id="test_001",
            data=sample_data,
            metadata=sample_metadata,
        )

        # Remove metadata file manually
        metadata_file = (
            storage_backend.base_path / "bronze" / "metadata" / "test_001.json"
        )
        metadata_file.unlink()

        # Delete should still work (removes data file)
        result = storage_backend.delete_data("bronze", "test_001")
        assert result is True

    def test_delete_data_failure(self, storage_backend):
        """Test delete data failure handling."""
        # Create invalid backend to trigger failure
        with patch.object(Path, "unlink", side_effect=PermissionError("Access denied")):
            # Store some data first
            storage_backend.store_data(
                layer_name="bronze",
                data_id="test_001",
                data={"test": "data"},
                metadata=LayerMetadata(
                    source_path=Path("/test"),
                    layer_name="bronze",
                    ingestion_timestamp=datetime.now(),
                    format_type=SupportedFormat.UNKNOWN,
                ),
            )

            result = storage_backend.delete_data("bronze", "test_001")
            assert result is False


# pylint: disable=protected-access
class TestLocalStorageQuery:
    """Test query and list operations."""

    def test_query_data_empty_layer(self, storage_backend):
        """Test querying data from empty layer."""
        query = LayerQuery(layer_name="bronze", filters={})
        result = storage_backend.query_data("bronze", query)

        assert isinstance(result, LayerData)
        assert result.total_count == 0
        assert result.retrieved_count == 0
        assert len(result.records) == 0
        assert len(result.metadata) == 0

    def test_query_data_with_results(
        self, storage_backend, sample_data, sample_metadata
    ):
        """Test querying data with results."""
        # Store multiple data items
        for i in range(3):
            storage_backend.store_data(
                layer_name="bronze",
                data_id=f"test_{i:03d}",
                data={**sample_data, "id": i},
                metadata=sample_metadata,
            )

        query = LayerQuery(layer_name="bronze", filters={})
        result = storage_backend.query_data("bronze", query)

        assert result.total_count == 3
        assert result.retrieved_count == 3
        assert len(result.records) == 3
        assert len(result.metadata) == 3

    def test_query_data_with_limit_offset(
        self, storage_backend, sample_data, sample_metadata
    ):
        """Test querying data with limit and offset."""
        # Store multiple data items
        for i in range(5):
            storage_backend.store_data(
                layer_name="bronze",
                data_id=f"test_{i:03d}",
                data={**sample_data, "id": i},
                metadata=sample_metadata,
            )

        query = LayerQuery(layer_name="bronze", filters={}, limit=2, offset=1)
        result = storage_backend.query_data("bronze", query)

        assert result.total_count == 5
        assert result.retrieved_count == 2
        assert len(result.records) == 2

    def test_query_data_failure(self, storage_backend):
        """Test query data failure handling."""
        # Remove the layer directory to trigger failure
        layer_path = storage_backend.base_path / "bronze"
        shutil.rmtree(layer_path)

        query = LayerQuery(layer_name="bronze", filters={})
        result = storage_backend.query_data("bronze", query)

        assert result.total_count == 0
        assert result.retrieved_count == 0

    def test_list_data_ids_success(self, storage_backend, sample_data, sample_metadata):
        """Test successful data ID listing."""
        # Store multiple data items
        expected_ids = ["test_001", "test_002", "test_003"]
        for data_id in expected_ids:
            storage_backend.store_data(
                layer_name="bronze",
                data_id=data_id,
                data=sample_data,
                metadata=sample_metadata,
            )

        result = storage_backend.list_data_ids("bronze")
        assert sorted(result) == sorted(expected_ids)

    def test_list_data_ids_empty_layer(self, storage_backend):
        """Test listing data IDs from empty layer."""
        result = storage_backend.list_data_ids("bronze")
        assert result == []

    def test_list_data_ids_nonexistent_layer(self, storage_backend):
        """Test listing data IDs from nonexistent layer."""
        result = storage_backend.list_data_ids("nonexistent")
        assert result == []

    def test_list_data_ids_failure(self, storage_backend):
        """Test list data IDs failure handling."""
        # Remove the layer directory to trigger failure
        layer_path = storage_backend.base_path / "bronze"
        shutil.rmtree(layer_path)

        result = storage_backend.list_data_ids("bronze")
        assert result == []

    def test_get_storage_info(self, storage_backend, sample_data, sample_metadata):
        """Test getting storage information."""
        # Store some data first
        storage_backend.store_data(
            layer_name="bronze",
            data_id="test_001",
            data=sample_data,
            metadata=sample_metadata,
        )

        info = storage_backend.get_storage_info()

        assert info["backend_type"] == "local_filesystem"
        assert info["base_path"] == str(storage_backend.base_path)
        assert info["compression"] is False
        assert info["auto_backup"] is False
        assert info["bronze_data_count"] == 1
        assert info["silver_data_count"] == 0
        assert info["gold_data_count"] == 0


# pylint: disable=protected-access
class TestLocalStorageMaintenance:
    """Test maintenance operations (cleanup, backup, restore)."""

    def test_cleanup_old_data(self, storage_backend, sample_data):
        """Test cleaning up old data."""
        # Create metadata with different timestamps
        old_metadata = LayerMetadata(
            source_path=Path("/test/old.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now() - timedelta(days=10),
            format_type=SupportedFormat.UNKNOWN,
        )

        new_metadata = LayerMetadata(
            source_path=Path("/test/new.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
            format_type=SupportedFormat.UNKNOWN,
        )

        # Store old and new data
        storage_backend.store_data("bronze", "old_data", sample_data, old_metadata)
        storage_backend.store_data("bronze", "new_data", sample_data, new_metadata)

        # Cleanup data older than 5 days
        cleaned_count = storage_backend.cleanup_old_data("bronze", retention_days=5)

        assert cleaned_count == 1

        # Verify old data is gone, new data remains
        assert storage_backend.retrieve_data("bronze", "old_data") is None
        assert storage_backend.retrieve_data("bronze", "new_data") is not None

    def test_cleanup_old_data_empty_layer(self, storage_backend):
        """Test cleanup on empty layer."""
        cleaned_count = storage_backend.cleanup_old_data("bronze", retention_days=5)
        assert cleaned_count == 0

    def test_cleanup_old_data_nonexistent_layer(self, storage_backend):
        """Test cleanup on nonexistent layer."""
        cleaned_count = storage_backend.cleanup_old_data(
            "nonexistent", retention_days=5
        )
        assert cleaned_count == 0

    def test_cleanup_old_data_corrupted_metadata(
        self, storage_backend, sample_data, sample_metadata
    ):
        """Test cleanup with corrupted metadata file."""
        # Store valid data
        storage_backend.store_data("bronze", "valid_data", sample_data, sample_metadata)

        # Create corrupted metadata file
        corrupted_metadata_file = (
            storage_backend.base_path / "bronze" / "metadata" / "corrupted.json"
        )
        with open(corrupted_metadata_file, "w", encoding="utf-8") as f:
            f.write("invalid json")

        # Cleanup should handle corruption gracefully
        cleaned_count = storage_backend.cleanup_old_data("bronze", retention_days=5)
        assert cleaned_count >= 0  # Should not crash

    def test_backup_layer_success(
        self, storage_backend, sample_data, sample_metadata, temp_dir
    ):
        """Test successful layer backup."""
        # Store some data
        storage_backend.store_data("bronze", "test_001", sample_data, sample_metadata)

        backup_path = temp_dir / "backup" / "bronze"
        result = storage_backend.backup_layer("bronze", backup_path)

        assert result is True
        assert backup_path.exists()
        assert (backup_path / "data" / "test_001.json").exists()
        assert (backup_path / "metadata" / "test_001.json").exists()

    def test_backup_layer_nonexistent(self, storage_backend, temp_dir):
        """Test backing up nonexistent layer."""
        backup_path = temp_dir / "backup" / "nonexistent"
        result = storage_backend.backup_layer("nonexistent", backup_path)

        assert result is False

    def test_backup_layer_failure(self, storage_backend, sample_data, sample_metadata):
        """Test backup failure handling."""
        # Store some data
        storage_backend.store_data("bronze", "test_001", sample_data, sample_metadata)

        # Try to backup to invalid path
        invalid_backup_path = Path("/invalid/path/backup")
        result = storage_backend.backup_layer("bronze", invalid_backup_path)

        assert result is False

    def test_restore_layer_success(
        self, storage_backend, sample_data, sample_metadata, temp_dir
    ):
        """Test successful layer restore."""
        # Create backup first
        storage_backend.store_data("bronze", "test_001", sample_data, sample_metadata)
        backup_path = temp_dir / "backup" / "bronze"
        storage_backend.backup_layer("bronze", backup_path)

        # Clear the layer
        layer_path = storage_backend.base_path / "bronze"
        shutil.rmtree(layer_path)

        # Restore from backup
        result = storage_backend.restore_layer("bronze", backup_path)

        assert result is True
        assert storage_backend.retrieve_data("bronze", "test_001") is not None

    def test_restore_layer_nonexistent_backup(self, storage_backend, temp_dir):
        """Test restoring from nonexistent backup."""
        backup_path = temp_dir / "nonexistent_backup"
        result = storage_backend.restore_layer("bronze", backup_path)

        assert result is False

    def test_restore_layer_failure(self, storage_backend):
        """Test restore failure handling."""
        # Create a valid backup path but mock shutil.copytree to fail
        backup_path = storage_backend.base_path / "existing_bronze"
        backup_path.mkdir(parents=True, exist_ok=True)

        with patch("shutil.copytree", side_effect=PermissionError("Access denied")):
            result = storage_backend.restore_layer("bronze", backup_path)
            assert result is False


# pylint: disable=protected-access
class TestLocalStorageInternals:
    """Test internal helper methods."""

    def test_matches_query_with_filters(self, storage_backend):
        """Test query matching with filters."""
        metadata = LayerMetadata(
            source_path=Path("/test/source.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
            format_type=SupportedFormat.UNKNOWN,
            user_id="test_user",
        )

        query = LayerQuery(layer_name="bronze", filters={"user_id": "test_user"})

        # Use the private method for testing
        result = storage_backend._matches_query("data_001", metadata, query)
        # This will depend on the implementation of matches_query_filters
        # which should be tested separately
        assert isinstance(result, bool)

    def test_load_metadata_from_file(self, storage_backend, temp_dir):
        """Test loading metadata from file."""
        # Create a metadata file
        metadata_dict = {
            "source_path": "/test/source.json",
            "layer_name": "bronze",
            "ingestion_timestamp": datetime.now().isoformat(),
            "processing_timestamp": None,
            "data_hash": "test_hash",
            "version": "1.0",
            "format_type": "unknown",
            "record_count": 10,
            "file_size_bytes": 1024,
            "processing_duration_ms": 100.0,
            "user_id": "test_user",
            "session_id": "test_session",
            "custom_metadata": {"key": "value"},
        }

        metadata_file = temp_dir / "test_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata_dict, f)

        # Load metadata
        metadata = storage_backend._load_metadata_from_file(metadata_file)

        assert metadata.layer_name == "bronze"
        assert metadata.data_hash == "test_hash"
        assert metadata.format_type == SupportedFormat.UNKNOWN

    def test_load_data_file_success(self, storage_backend, temp_dir):
        """Test loading data file successfully."""
        data = {"test": "data", "items": [1, 2, 3]}
        data_file = temp_dir / "data" / "test.json"
        data_file.parent.mkdir(parents=True, exist_ok=True)

        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        result = storage_backend._load_data_file(temp_dir, "test")
        assert result == data

    def test_load_data_file_not_found(self, storage_backend, temp_dir):
        """Test loading nonexistent data file."""
        result = storage_backend._load_data_file(temp_dir, "nonexistent")
        assert result is None

    def test_build_layer_data(self, storage_backend, sample_metadata):
        """Test building LayerData from matching items."""
        matching_items = [
            ({"id": 1}, sample_metadata),
            ({"id": 2}, sample_metadata),
            ({"id": 3}, sample_metadata),
        ]

        query = LayerQuery(layer_name="bronze", filters={}, limit=2, offset=1)
        result = storage_backend._build_layer_data(matching_items, query)

        assert result.total_count == 3
        assert result.retrieved_count == 2
        assert len(result.records) == 2
        assert result.records[0]["id"] == 2  # After offset=1
        assert result.records[1]["id"] == 3

    def test_process_metadata_files(self, storage_backend, temp_dir, sample_data):
        """Test processing metadata files."""
        # Create metadata files
        metadata_files = []
        for i in range(3):
            metadata_file = temp_dir / f"metadata_{i}.json"
            metadata_dict = {
                "source_path": f"/test/source_{i}.json",
                "layer_name": "bronze",
                "ingestion_timestamp": datetime.now().isoformat(),
                "format_type": "unknown",
                "data_hash": f"hash_{i}",
                "version": "1.0",
                "record_count": 10,
                "file_size_bytes": 1024,
                "processing_duration_ms": 100.0,
                "user_id": "test_user",
                "session_id": "test_session",
                "custom_metadata": {},
            }

            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata_dict, f)

            # Create corresponding data file
            data_file = temp_dir / "data" / f"metadata_{i}.json"
            data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump({**sample_data, "id": i}, f)

            metadata_files.append(metadata_file)

        query = LayerQuery(layer_name="bronze", filters={})

        # Mock the _matches_query method to return True
        with patch.object(storage_backend, "_matches_query", return_value=True):
            result = storage_backend._process_metadata_files(
                metadata_files, temp_dir, query
            )

        assert len(result) == 3
        for i, (data, metadata) in enumerate(result):
            assert data["id"] == i
            assert metadata.data_hash == f"hash_{i}"

    def test_empty_layer_data(self, storage_backend):
        """Test creating empty LayerData response."""
        query = LayerQuery(layer_name="bronze", filters={"test": "filter"})
        result = storage_backend._empty_layer_data(query)

        assert isinstance(result, LayerData)
        assert result.total_count == 0
        assert result.retrieved_count == 0
        assert len(result.records) == 0
        assert len(result.metadata) == 0
        assert result.query == query
