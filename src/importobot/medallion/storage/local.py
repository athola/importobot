"""Local filesystem storage backend for Medallion architecture."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager, suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:  # pragma: no cover - platform specific imports
    import fcntl
except ImportError:  # pragma: no cover - Windows default handling
    fcntl = None  # type: ignore[assignment]

try:  # pragma: no cover - platform specific imports
    import msvcrt
except ImportError:  # pragma: no cover - non-Windows platforms
    msvcrt = None  # type: ignore[assignment]

from importobot.medallion.interfaces.data_models import (
    LayerData,
    LayerMetadata,
    LayerQuery,
)
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.medallion.storage.base import StorageBackend
from importobot.medallion.utils.query_filters import matches_query_filters
from importobot.utils.logging import get_logger

logger = get_logger()


@contextmanager
def _exclusive_file_lock(lock_path: Path) -> Iterator[None]:
    """Cross-platform exclusive file lock using advisory locking primitives."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        try:
            if fcntl is not None:  # Unix-like systems
                fcntl.flock(lock_file, fcntl.LOCK_EX)
            elif msvcrt is not None:  # Windows default handling
                lock_file.seek(0)
                lock_file.write("0")
                lock_file.flush()
                locking = getattr(msvcrt, "locking", None)
                lk_lock = getattr(msvcrt, "LK_LOCK", None)
                if locking is not None and lk_lock is not None:
                    locking(lock_file.fileno(), lk_lock, 1)
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            elif msvcrt is not None:
                lock_file.seek(0)
                locking = getattr(msvcrt, "locking", None)
                lk_unlock = getattr(msvcrt, "LK_UNLCK", None)
                if locking is not None and lk_unlock is not None:
                    locking(lock_file.fileno(), lk_unlock, 1)
    with suppress(OSError):
        lock_path.unlink()


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend implementation."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the local storage backend.

        Args:
            config: Configuration with 'base_path' and optional settings
        """
        super().__init__(config)
        self.base_path = Path(config.get("base_path", "./medallion_data"))
        self.create_compression = config.get("compression", False)
        self.auto_backup = config.get("auto_backup", False)
        self._metadata_cache: dict[
            str, tuple[float, tuple[tuple[Path, float], ...]]
        ] = {}

        # Create directory structure
        self.base_path.mkdir(parents=True, exist_ok=True)
        for layer in ["bronze", "silver", "gold"]:
            (self.base_path / layer).mkdir(exist_ok=True)
            (self.base_path / layer / "data").mkdir(exist_ok=True)
            (self.base_path / layer / "metadata").mkdir(exist_ok=True)
            (self.base_path / layer / "locks").mkdir(exist_ok=True)

        logger.info("Initialized LocalStorageBackend at %s", self.base_path)

    def store_data(
        self,
        layer_name: str,
        data_id: str,
        data: dict[str, Any],
        metadata: LayerMetadata,
    ) -> bool:
        """Store data in the local filesystem.

        Args:
            layer_name: Name of the layer
            data_id: Unique identifier for the data
            data: The data to store
            metadata: Associated metadata

        Returns:
            True if storage was successful, False otherwise
        """
        try:
            layer_path = self.base_path / layer_name
            data_file = layer_path / "data" / f"{data_id}.json"
            metadata_file = layer_path / "metadata" / f"{data_id}.json"

            lock_manager = self._acquire_write_lock(layer_path, data_id)
            with lock_manager:
                # Store data
                with open(data_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str, ensure_ascii=False)

                # Store metadata
                metadata_dict = {
                    "source_path": str(metadata.source_path),
                    "layer_name": metadata.layer_name,
                    "ingestion_timestamp": metadata.ingestion_timestamp.isoformat(),
                    "processing_timestamp": (
                        metadata.processing_timestamp.isoformat()
                        if metadata.processing_timestamp
                        else None
                    ),
                    "data_hash": metadata.data_hash,
                    "version": metadata.version,
                    "format_type": metadata.format_type.value,
                    "record_count": metadata.record_count,
                    "file_size_bytes": metadata.file_size_bytes,
                    "processing_duration_ms": metadata.processing_duration_ms,
                    "user_id": metadata.user_id,
                    "session_id": metadata.session_id,
                    "custom_metadata": metadata.custom_metadata,
                }

                with open(metadata_file, "w", encoding="utf-8") as f:
                    json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

            logger.debug("Stored data %s in layer %s", data_id, layer_name)
            self._update_metadata_cache_on_write(layer_name, metadata_file)
            return True

        except Exception as e:
            logger.error(
                "Failed to store data %s in layer %s: %s", data_id, layer_name, str(e)
            )
            return False

    def retrieve_data(
        self, layer_name: str, data_id: str
    ) -> tuple[dict[str, Any], LayerMetadata] | None:
        """Retrieve specific data from the layer.

        Args:
            layer_name: Name of the layer
            data_id: Unique identifier for the data

        Returns:
            Tuple of (data, metadata) if found, None otherwise
        """
        try:
            layer_path = self.base_path / layer_name
            data_file = layer_path / "data" / f"{data_id}.json"
            metadata_file = layer_path / "metadata" / f"{data_id}.json"

            if not data_file.exists() or not metadata_file.exists():
                return None

            # Load data
            with open(data_file, encoding="utf-8") as f:
                data = json.load(f)

            # Load metadata
            with open(metadata_file, encoding="utf-8") as f:
                metadata_dict = json.load(f)

            metadata = LayerMetadata(
                source_path=Path(metadata_dict["source_path"]),
                layer_name=metadata_dict["layer_name"],
                ingestion_timestamp=datetime.fromisoformat(
                    metadata_dict["ingestion_timestamp"]
                ),
                processing_timestamp=(
                    datetime.fromisoformat(metadata_dict["processing_timestamp"])
                    if metadata_dict.get("processing_timestamp")
                    else None
                ),
                data_hash=metadata_dict.get("data_hash", ""),
                version=metadata_dict.get("version", "1.0"),
                format_type=SupportedFormat(
                    metadata_dict.get("format_type", "unknown")
                ),
                record_count=metadata_dict.get("record_count", 0),
                file_size_bytes=metadata_dict.get("file_size_bytes", 0),
                processing_duration_ms=metadata_dict.get("processing_duration_ms", 0.0),
                user_id=metadata_dict.get("user_id", "system"),
                session_id=metadata_dict.get("session_id", ""),
                custom_metadata=metadata_dict.get("custom_metadata", {}),
            )

            return data, metadata

        except Exception as e:
            logger.error(
                "Failed to retrieve data %s from layer %s: %s",
                data_id,
                layer_name,
                str(e),
            )
            return None

    def query_data(self, layer_name: str, query: LayerQuery) -> LayerData:
        """Query data from the layer based on criteria.

        Args:
            layer_name: Name of the layer
            query: Query specification

        Returns:
            LayerData with matching records
        """
        try:
            layer_path = self.base_path / layer_name
            metadata_path = layer_path / "metadata"

            if not metadata_path.exists():
                return self._empty_layer_data(query)

            # Use os.scandir for faster directory scanning (2-3x faster than glob)
            metadata_files = self._get_metadata_listing(layer_name, metadata_path)
            matching_items, match_count = self._process_metadata_files(
                metadata_files, layer_path, query
            )

            return self._build_layer_data(matching_items, query, match_count)

        except Exception as e:
            logger.error("Failed to query data from layer %s: %s", layer_name, str(e))
            return self._empty_layer_data(query)

    def _fast_scan_metadata_dir(self, metadata_path: Path) -> list[tuple[Path, float]]:
        """Fast directory scanning using os.scandir (faster than glob).

        Business justification: 2-3x faster than glob() for large directories.
        Returns list of (path, mtime) tuples to avoid re-stating files.
        """
        metadata_files = []
        try:
            with os.scandir(metadata_path) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.endswith(".json"):
                        # Get mtime from DirEntry to avoid extra stat() call
                        mtime = entry.stat().st_mtime
                        metadata_files.append((Path(entry.path), mtime))
        except OSError:
            # Fall back to empty list if scandir fails
            pass
        return metadata_files

    def _get_metadata_listing(
        self, layer_name: str, metadata_path: Path
    ) -> list[tuple[Path, float]]:
        """Return cached metadata listing when directory has not changed."""
        if not metadata_path.exists():
            self._metadata_cache.pop(layer_name, None)
            return []

        try:
            dir_mtime = metadata_path.stat().st_mtime
        except OSError:
            dir_mtime = -1.0

        cached = self._metadata_cache.get(layer_name)
        if cached and cached[0] == dir_mtime:
            return list(cached[1])

        metadata_files = self._fast_scan_metadata_dir(metadata_path)
        metadata_files.sort(key=lambda x: x[1], reverse=True)
        self._metadata_cache[layer_name] = (dir_mtime, tuple(metadata_files))
        return metadata_files

    def _update_metadata_cache_on_write(
        self, layer_name: str, metadata_file: Path
    ) -> None:
        """Incrementally update cached metadata listing after a write."""
        cached = self._metadata_cache.get(layer_name)
        if not cached:
            return
        try:
            dir_mtime = metadata_file.parent.stat().st_mtime
            file_mtime = metadata_file.stat().st_mtime
        except OSError:
            self._metadata_cache.pop(layer_name, None)
            return

        entries = [item for item in cached[1] if item[0] != metadata_file]
        entries.append((metadata_file, file_mtime))
        entries.sort(key=lambda x: x[1], reverse=True)
        self._metadata_cache[layer_name] = (dir_mtime, tuple(entries))

    def _remove_metadata_cache_entry(
        self, layer_name: str, metadata_file: Path
    ) -> None:
        """Remove a metadata entry from cache after deletion."""
        cached = self._metadata_cache.get(layer_name)
        if not cached:
            return

        entries = [item for item in cached[1] if item[0] != metadata_file]
        if not entries:
            self._metadata_cache.pop(layer_name, None)
            return

        try:
            dir_mtime = metadata_file.parent.stat().st_mtime
        except OSError:
            dir_mtime = cached[0]

        self._metadata_cache[layer_name] = (dir_mtime, tuple(entries))

    def _acquire_write_lock(
        self, layer_path: Path, data_id: str
    ) -> AbstractContextManager[None]:
        """Acquire an exclusive lock for a specific data record."""
        lock_dir = layer_path / "locks"
        lock_dir.mkdir(exist_ok=True)
        lock_path = lock_dir / f"{data_id}.lock"
        return _exclusive_file_lock(lock_path)

    def _empty_layer_data(self, query: LayerQuery) -> LayerData:
        """Create an empty LayerData response."""
        return LayerData(
            records=[],
            metadata=[],
            total_count=0,
            retrieved_count=0,
            query=query,
        )

    def _process_metadata_files(
        self,
        metadata_files: list[tuple[Path, float]],
        layer_path: Path,
        query: LayerQuery,
    ) -> tuple[list[tuple[dict[str, Any], LayerMetadata]], int]:
        """Process metadata files and return matching items with match count.

        Optimized to:
        - Sort files by modification time (most recent first) using cached mtime
        - Load at most offset + limit records from disk while still counting all matches
        """
        matching_items: list[tuple[dict[str, Any], LayerMetadata]] = []
        match_count = 0

        # Calculate how many records we need to materialize for pagination
        if query.limit is None:
            max_needed = len(metadata_files)
        else:
            max_needed = query.offset + query.limit

        for metadata_path, _mtime in metadata_files:
            should_materialize = len(matching_items) < max_needed
            match_delta, item = self._process_metadata_entry(
                metadata_path, layer_path, query, should_materialize
            )
            match_count += match_delta
            if item is not None:
                matching_items.append(item)

        return matching_items, match_count

    def _process_metadata_entry(
        self,
        metadata_path: Path,
        layer_path: Path,
        query: LayerQuery,
        should_materialize: bool,
    ) -> tuple[int, tuple[dict[str, Any], LayerMetadata] | None]:
        """Process a single metadata file safely for lint performance rules."""
        try:
            metadata = self._load_metadata_from_file(metadata_path)
        except Exception as error:
            logger.warning(
                "Failed to process metadata file %s: %s", metadata_path, error
            )
            return 0, None

        data_id = metadata_path.stem

        if not self._matches_query(data_id, metadata, query):
            return 0, None

        if not should_materialize:
            return 1, None

        data = self._load_data_file(layer_path, data_id)
        if data is None:
            return 1, None

        return 1, (data, metadata)

    def _load_metadata_from_file(self, metadata_file: Path) -> LayerMetadata:
        """Load and parse metadata from a JSON file."""
        with open(metadata_file, encoding="utf-8") as f:
            metadata_dict = json.load(f)

        return LayerMetadata(
            source_path=Path(metadata_dict["source_path"]),
            layer_name=metadata_dict["layer_name"],
            ingestion_timestamp=datetime.fromisoformat(
                metadata_dict["ingestion_timestamp"]
            ),
            processing_timestamp=(
                datetime.fromisoformat(metadata_dict["processing_timestamp"])
                if metadata_dict.get("processing_timestamp")
                else None
            ),
            data_hash=metadata_dict.get("data_hash", ""),
            version=metadata_dict.get("version", "1.0"),
            format_type=SupportedFormat(metadata_dict.get("format_type", "unknown")),
            record_count=metadata_dict.get("record_count", 0),
            file_size_bytes=metadata_dict.get("file_size_bytes", 0),
            processing_duration_ms=metadata_dict.get("processing_duration_ms", 0.0),
            user_id=metadata_dict.get("user_id", "system"),
            session_id=metadata_dict.get("session_id", ""),
            custom_metadata=metadata_dict.get("custom_metadata", {}),
        )

    def _load_data_file(self, layer_path: Path, data_id: str) -> dict[str, Any] | None:
        """Load data from a JSON file."""
        data_file = layer_path / "data" / f"{data_id}.json"
        if data_file.exists():
            with open(data_file, encoding="utf-8") as f:
                return json.load(f)  # type: ignore[no-any-return]
        return None

    def _build_layer_data(
        self,
        matching_items: list[tuple[dict[str, Any], LayerMetadata]],
        query: LayerQuery,
        match_count: int,
    ) -> LayerData:
        """Build the final LayerData response from matching items.

        Note: Items are already sorted by mtime in _process_metadata_files,
        which correlates strongly with ingestion_timestamp. We skip re-sorting
        for performance unless there's a specific need.
        """
        # Items already sorted by modification time in _process_metadata_files
        # This avoids O(n log n) re-sort on large datasets
        total_count = match_count

        start_idx = query.offset
        end_idx = (
            start_idx + query.limit if query.limit is not None else len(matching_items)
        )
        final_items = matching_items[start_idx:end_idx]

        records = [item[0] for item in final_items]
        metadata_list = [item[1] for item in final_items]

        return LayerData(
            records=records,
            metadata=metadata_list,
            total_count=total_count,
            retrieved_count=len(final_items),
            query=query,
        )

    def delete_data(self, layer_name: str, data_id: str) -> bool:
        """Delete data from the layer.

        Args:
            layer_name: Name of the layer
            data_id: Unique identifier for the data

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            layer_path = self.base_path / layer_name
            data_file = layer_path / "data" / f"{data_id}.json"
            metadata_file = layer_path / "metadata" / f"{data_id}.json"

            deleted_any = False
            if data_file.exists():
                data_file.unlink()
                deleted_any = True

            if metadata_file.exists():
                metadata_file.unlink()
                deleted_any = True

            if deleted_any:
                logger.debug("Deleted data %s from layer %s", data_id, layer_name)
                self._remove_metadata_cache_entry(layer_name, metadata_file)

            return deleted_any

        except Exception as e:
            logger.error(
                "Failed to delete data %s from layer %s: %s",
                data_id,
                layer_name,
                str(e),
            )
            return False

    def list_data_ids(self, layer_name: str) -> list[str]:
        """List all data IDs in the specified layer.

        Args:
            layer_name: Name of the layer

        Returns:
            List of data IDs
        """
        try:
            layer_path = self.base_path / layer_name / "data"
            if not layer_path.exists():
                return []

            data_files = list(layer_path.glob("*.json"))
            return [f.stem for f in data_files]

        except Exception as e:
            logger.error(
                "Failed to list data IDs from layer %s: %s", layer_name, str(e)
            )
            return []

    def get_storage_info(self) -> dict[str, Any]:
        """Get information about the storage backend.

        Returns:
            Dictionary with storage backend information
        """
        info = {
            "backend_type": "local_filesystem",
            "base_path": str(self.base_path),
            "compression": self.create_compression,
            "auto_backup": self.auto_backup,
        }

        # Add layer statistics
        for layer in ["bronze", "silver", "gold"]:
            layer_path = self.base_path / layer
            if layer_path.exists():
                data_count = len(list((layer_path / "data").glob("*.json")))
                info[f"{layer}_data_count"] = data_count

        return info

    def cleanup_old_data(self, layer_name: str, retention_days: int) -> int:
        """Clean up old data based on retention policy.

        Args:
            layer_name: Name of the layer
            retention_days: Number of days to retain data

        Returns:
            Number of items cleaned up
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            layer_path = self.base_path / layer_name
            metadata_path = layer_path / "metadata"

            if not metadata_path.exists():
                return 0

            cleaned_count = 0
            metadata_files = list(metadata_path.glob("*.json"))

            for metadata_file in metadata_files:
                cleaned_count += self._cleanup_metadata_file(
                    metadata_file, layer_name, cutoff_date
                )

            logger.info(
                "Cleaned up %s old items from layer %s", cleaned_count, layer_name
            )
            return cleaned_count

        except Exception as e:
            logger.error(
                "Failed to cleanup old data from layer %s: %s", layer_name, str(e)
            )
            return 0

    def _cleanup_metadata_file(
        self, metadata_file: Path, layer_name: str, cutoff_date: datetime
    ) -> int:
        """Cleanup a single metadata file during retention processing."""
        try:
            with open(metadata_file, encoding="utf-8") as file_handle:
                metadata_dict = json.load(file_handle)

            ingestion_time = datetime.fromisoformat(
                metadata_dict["ingestion_timestamp"]
            )
        except Exception as error:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to process metadata file %s during cleanup: %s",
                metadata_file,
                error,
            )
            return 0

        if ingestion_time >= cutoff_date:
            return 0

        data_id = metadata_file.stem
        return 1 if self.delete_data(layer_name, data_id) else 0

    def backup_layer(self, layer_name: str, backup_path: Path) -> bool:
        """Create a backup of the entire layer.

        Args:
            layer_name: Name of the layer to backup
            backup_path: Path where backup should be stored

        Returns:
            True if backup was successful, False otherwise
        """
        try:
            layer_path = self.base_path / layer_name
            if not layer_path.exists():
                logger.warning("Layer %s does not exist, cannot backup", layer_name)
                return False

            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(layer_path, backup_path, dirs_exist_ok=True)

            logger.info(
                "Successfully backed up layer %s to %s", layer_name, backup_path
            )
            return True

        except Exception as e:
            logger.error("Failed to backup layer %s: %s", layer_name, str(e))
            return False

    def restore_layer(self, layer_name: str, backup_path: Path) -> bool:
        """Restore a layer from backup.

        Args:
            layer_name: Name of the layer to restore
            backup_path: Path where backup is stored

        Returns:
            True if restore was successful, False otherwise
        """
        try:
            if not backup_path.exists():
                logger.error("Backup path %s does not exist", backup_path)
                return False

            layer_path = self.base_path / layer_name
            temp_path = layer_path.with_suffix(".restore_temp")

            if layer_path.exists():
                if temp_path.exists():
                    shutil.rmtree(temp_path)
                shutil.move(layer_path, temp_path)

            try:
                shutil.copytree(backup_path, layer_path)
            except Exception:
                if temp_path.exists():
                    shutil.move(temp_path, layer_path)
                raise

            if temp_path.exists():
                shutil.rmtree(temp_path)

            logger.info(
                "Successfully restored layer %s from %s", layer_name, backup_path
            )
            return True

        except Exception as e:
            logger.error("Failed to restore layer %s: %s", layer_name, str(e))
            return False

    def _matches_query(
        self, data_id: str, metadata: LayerMetadata, query: LayerQuery
    ) -> bool:
        """Check if a data item matches the query criteria."""
        # Use shared query filter logic
        return matches_query_filters(data_id, metadata, query)
