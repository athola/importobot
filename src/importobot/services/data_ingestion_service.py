# pydocstyle: ignore=D107

"""Unified data ingestion service with optional security hardening.

Handles core data ingestion responsibilities with configurable security validation.
Consolidates both basic and secure ingestion capabilities into a single service.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, List, Mapping, Optional, Union, cast
from uuid import uuid4

from importobot.config import (
    FILE_CONTENT_CACHE_MAX_MB,
    FILE_CONTENT_CACHE_TTL_SECONDS,
)
from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import (
    DataQualityMetrics,
    LayerMetadata,
    ProcessingResult,
)
from importobot.medallion.interfaces.enums import ProcessingStatus, SupportedFormat
from importobot.services.security_gateway import SecurityGateway
from importobot.services.security_types import SecurityLevel
from importobot.telemetry import TelemetryClient, get_telemetry_client
from importobot.utils.logging import setup_logger
from importobot.utils.validation import (
    validate_file_path,
    validate_json_dict,
    validate_json_size,
)

logger = setup_logger(__name__)


class FileContentCache:
    """Simple LRU cache for file contents keyed by path + mtime."""

    def __init__(
        self,
        max_size_mb: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
        *,
        telemetry_client: Optional[TelemetryClient] = None,
    ) -> None:
        """Initialize cache with an LRU budget expressed in megabytes."""
        resolved_mb = (
            max_size_mb if max_size_mb is not None else FILE_CONTENT_CACHE_MAX_MB
        )
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._max_size_bytes = resolved_mb * 1024 * 1024
        self._current_size_bytes = 0
        resolved_ttl = (
            ttl_seconds if ttl_seconds is not None else FILE_CONTENT_CACHE_TTL_SECONDS
        )
        self._ttl_seconds: Optional[int] = resolved_ttl if resolved_ttl > 0 else None
        self._cache_hits = 0
        self._cache_misses = 0
        self._telemetry = telemetry_client or get_telemetry_client()

    def get_cached_content(self, file_path: Path) -> Optional[str]:
        """Return cached content if file unchanged, else evict entry."""
        cache_key = str(file_path.resolve())
        entry = self._cache.get(cache_key)
        if not entry:
            self._cache_misses += 1
            self._emit_cache_metrics()
            return None

        if (
            self._ttl_seconds is not None
            and (time.time() - entry["accessed"]) > self._ttl_seconds
        ):
            self._evict_key(cache_key)
            self._cache_misses += 1
            self._emit_cache_metrics()
            return None

        try:
            current_mtime = file_path.stat().st_mtime
        except OSError:
            # File no longer accessible; remove cache entry
            self._evict_key(cache_key)
            self._cache_misses += 1
            self._emit_cache_metrics()
            return None

        if entry["mtime"] != current_mtime:
            self._evict_key(cache_key)
            return None

        entry["accessed"] = time.time()
        self._cache.move_to_end(cache_key)
        self._cache_hits += 1
        self._emit_cache_metrics()
        return cast(str, entry["content"])

    def cache_content(self, file_path: Path, content: str) -> None:
        """Cache file content, evicting least-recently used as needed."""
        cache_key = str(file_path.resolve())
        content_bytes = content.encode("utf-8")
        content_size = len(content_bytes)

        if content_size > self._max_size_bytes:
            # Too large to cache; skip silently
            return

        try:
            mtime = file_path.stat().st_mtime
        except OSError:
            return

        if cache_key in self._cache:
            self._current_size_bytes -= self._cache[cache_key]["size"]

        while self._current_size_bytes + content_size > self._max_size_bytes:
            self._evict_oldest()

        self._cache[cache_key] = {
            "content": content,
            "mtime": mtime,
            "size": content_size,
            "accessed": time.time(),
        }
        self._cache.move_to_end(cache_key)
        self._current_size_bytes += content_size
        self._emit_cache_metrics()

    def _evict_oldest(self) -> None:
        if not self._cache:
            return
        _, entry = self._cache.popitem(last=False)
        self._current_size_bytes -= entry["size"]
        self._emit_cache_metrics()

    def _evict_key(self, cache_key: str) -> None:
        entry = self._cache.pop(cache_key, None)
        if entry:
            self._current_size_bytes -= entry["size"]
        self._emit_cache_metrics()

    def get_cache_stats(self) -> dict[str, int | float]:
        """Return hit/miss statistics for the file content cache."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            self._cache_hits / total_requests * 100 if total_requests > 0 else 0.0
        )
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "entries": len(self._cache),
            "current_bytes": self._current_size_bytes,
            "max_bytes": self._max_size_bytes,
            "ttl_seconds": self._ttl_seconds or 0,
        }

    def _emit_cache_metrics(self) -> None:
        self._telemetry.record_cache_metrics(
            "file_content_cache",
            hits=self._cache_hits,
            misses=self._cache_misses,
            extras={
                "entries": len(self._cache),
                "current_bytes": self._current_size_bytes,
                "max_bytes": self._max_size_bytes,
                "ttl_seconds": self._ttl_seconds or 0,
            },
        )


class DataIngestionService:
    """Unified data ingestion service with configurable security hardening."""

    def __init__(
        self,
        bronze_layer: BronzeLayer,
        *,
        security_level: Union[SecurityLevel, str] = SecurityLevel.STANDARD,
        enable_security_gateway: bool = False,
        format_service: Optional[Any] = None,
        content_cache: Optional[FileContentCache] = None,
    ):
        """Initialize ingestion service."""  # noqa: D107
        self.bronze_layer = bronze_layer

        if isinstance(security_level, str):
            self.security_level = SecurityLevel.from_string(security_level)
        else:
            self.security_level = security_level

        self.enable_security_gateway = enable_security_gateway
        self.format_service = format_service
        self._content_cache = content_cache or FileContentCache()

        # Lazy-load security gateway to avoid circular imports
        self._security_gateway: Optional[SecurityGateway] = None

        logger.info(
            "Initialized DataIngestionService with security_level=%s, gateway=%s",
            self.security_level.value,
            enable_security_gateway,
        )

    @property
    def security_gateway(self) -> Optional[SecurityGateway]:
        """Lazy-load security gateway when needed."""
        if self._security_gateway is None and self.enable_security_gateway:
            self._security_gateway = SecurityGateway(security_level=self.security_level)
        return self._security_gateway

    def ingest_file(self, file_path: Union[str, Path]) -> ProcessingResult:
        """Ingest a JSON file with optional security validation.

        Args:
            file_path: Path to the JSON file to ingest

        Returns:
            ProcessingResult with ingestion status and security validation results
        """
        file_path = Path(file_path)
        start_time = datetime.now()
        correlation_id = str(uuid4())

        try:
            # Optional security validation for file path
            if self.enable_security_gateway and self.security_gateway is not None:
                file_validation = self.security_gateway.validate_file_operation(
                    file_path, "read", correlation_id=correlation_id
                )
                if not file_validation["is_safe"]:
                    error_msg = (
                        f"File path security validation failed: "
                        f"{file_validation['security_issues']}"
                    )
                    logger.warning(error_msg)
                    return self._create_error_result(
                        start_time,
                        error_msg,
                        file_path,
                        security_info=file_validation,
                        correlation_id=correlation_id,
                    )

            # Standard file validation
            validate_file_path(str(file_path))

            # Read file content (with caching)
            content = self._read_file_content(file_path)

            # Process content (with optional security validation)
            if self.enable_security_gateway and self.security_gateway is not None:
                json_validation = self.security_gateway.sanitize_api_input(
                    content,
                    input_type="json",
                    context={
                        "source": str(file_path),
                        "correlation_id": correlation_id,
                    },
                )
                if not json_validation["is_safe"]:
                    error_msg = (
                        f"JSON content security validation failed: "
                        f"{json_validation['security_issues']}"
                    )
                    logger.warning(error_msg)
                    return self._create_error_result(
                        start_time,
                        error_msg,
                        file_path,
                        security_info=json_validation,
                        correlation_id=correlation_id,
                    )
                data = json_validation["sanitized_data"]
            else:
                # Standard JSON validation with size check
                validate_json_size(content, max_size_mb=10)
                data = json.loads(content)
                validate_json_dict(data)

            # Create metadata
            metadata = self._create_metadata(file_path, data)

            # Add security information if available
            if self.enable_security_gateway:
                metadata.custom_metadata["security_validation"] = json_validation
                metadata.custom_metadata["security_level"] = self.security_level.value
                metadata.custom_metadata["correlation_id"] = correlation_id

            # Ingest data into Bronze layer
            result = self.bronze_layer.ingest(data, metadata)

            # Add security information to result if available
            if self.enable_security_gateway:
                result.details["security_info"] = {
                    "file_validation": file_validation,
                    "json_validation": json_validation,
                    "security_level": self.security_level.value,
                    "correlation_id": correlation_id,
                }

            logger.info("Successfully ingested file %s into Bronze layer", file_path)
            return result

        except FileNotFoundError:
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return self._create_error_result(
                start_time, error_msg, file_path, correlation_id=correlation_id
            )

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in file {file_path}: {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(
                start_time, error_msg, file_path, correlation_id=correlation_id
            )

        except Exception as e:
            error_msg = f"Failed to ingest file {file_path}: {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(
                start_time, error_msg, file_path, correlation_id=correlation_id
            )

    async def ingest_file_async(self, file_path: Union[str, Path]) -> ProcessingResult:
        """Asynchronous wrapper for :meth:`ingest_file`."""
        return await asyncio.to_thread(self.ingest_file, file_path)

    def ingest_json_string(
        self, json_string: str, source_name: str = "string_input"
    ) -> ProcessingResult:
        """Ingest JSON string with optional security validation.

        Args:
            json_string: JSON string to ingest
            source_name: Name to use for the source in metadata

        Returns:
            ProcessingResult with ingestion status and security validation results
        """
        start_time = datetime.now()
        correlation_id = str(uuid4())

        try:
            # Process JSON string (with optional security validation)
            if self.enable_security_gateway and self.security_gateway is not None:
                json_validation = self.security_gateway.sanitize_api_input(
                    json_string,
                    input_type="json",
                    context={
                        "source": source_name,
                        "correlation_id": correlation_id,
                    },
                )
                if not json_validation["is_safe"]:
                    error_msg = (
                        f"JSON string security validation failed: "
                        f"{json_validation['security_issues']}"
                    )
                    logger.warning(error_msg)
                    return self._create_error_result(
                        start_time,
                        error_msg,
                        Path(source_name),
                        security_info=json_validation,
                        correlation_id=correlation_id,
                    )
                data = json_validation["sanitized_data"]
            else:
                # Standard JSON validation with size check
                validate_json_size(json_string, max_size_mb=10)
                data = json.loads(json_string)
                validate_json_dict(data)

            # Create metadata
            source_path = Path(f"string_input/{source_name}")
            metadata = self._create_metadata(source_path, data)

            # Add security information if available
            if self.enable_security_gateway:
                metadata.custom_metadata["security_validation"] = json_validation
                metadata.custom_metadata["security_level"] = self.security_level.value
                metadata.custom_metadata["correlation_id"] = correlation_id

            # Ingest data into Bronze layer
            result = self.bronze_layer.ingest(data, metadata)

            # Add security information to result if available
            if self.enable_security_gateway:
                result.details["security_info"] = {
                    "json_validation": json_validation,
                    "security_level": self.security_level.value,
                    "correlation_id": correlation_id,
                }

            logger.info(
                "Successfully ingested JSON string '%s' into Bronze layer", source_name
            )
            return result

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON string '{source_name}': {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(
                start_time, error_msg, Path(source_name), correlation_id=correlation_id
            )

        except Exception as e:
            error_msg = f"Failed to ingest JSON string '{source_name}': {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(
                start_time, error_msg, Path(source_name), correlation_id=correlation_id
            )

    async def ingest_json_string_async(
        self, json_string: str, source_name: str = "string_input"
    ) -> ProcessingResult:
        """Asynchronous wrapper for :meth:`ingest_json_string`."""
        return await asyncio.to_thread(
            self.ingest_json_string, json_string, source_name
        )

    def ingest_batch(
        self, file_paths: List[Union[str, Path]], max_workers: int = 4
    ) -> List[ProcessingResult]:
        """Ingest multiple JSON files in parallel."""
        normalized_paths = [Path(path) for path in file_paths]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(self.ingest_file, normalized_paths))

        return results

    async def ingest_batch_async(
        self, file_paths: List[Union[str, Path]], max_workers: int = 4
    ) -> List[ProcessingResult]:
        """Asynchronous wrapper for :meth:`ingest_batch`."""
        return await asyncio.to_thread(self.ingest_batch, file_paths, max_workers)

    def ingest_data_dict(
        self, data: dict[str, Any], source_name: str = "dict_input"
    ) -> ProcessingResult:
        """Ingest dictionary data with optional security validation.

        Args:
            data: Dictionary data to ingest
            source_name: Name to use for the source in metadata

        Returns:
            ProcessingResult with ingestion status and security validation results
        """
        start_time = datetime.now()
        correlation_id = str(uuid4())

        try:
            # Process dictionary data (with optional security validation)
            if self.enable_security_gateway and self.security_gateway is not None:
                dict_validation = self.security_gateway.sanitize_api_input(
                    data,
                    input_type="json",
                    context={
                        "source": source_name,
                        "correlation_id": correlation_id,
                    },
                )
                if not dict_validation["is_safe"]:
                    error_msg = (
                        f"Dictionary data security validation failed: "
                        f"{dict_validation['security_issues']}"
                    )
                    logger.warning(error_msg)
                    return self._create_error_result(
                        start_time,
                        error_msg,
                        Path(source_name),
                        security_info=dict_validation,
                        correlation_id=correlation_id,
                    )
                sanitized_data = dict_validation["sanitized_data"]
            else:
                sanitized_data = data

            # Create metadata
            source_path = Path(f"dict_input/{source_name}")
            metadata = self._create_metadata(source_path, sanitized_data)

            # Add security information if available
            if self.enable_security_gateway:
                metadata.custom_metadata["security_validation"] = dict_validation
                metadata.custom_metadata["security_level"] = self.security_level.value
                metadata.custom_metadata["correlation_id"] = correlation_id

            # Ingest data into Bronze layer
            result = self.bronze_layer.ingest(sanitized_data, metadata)

            # Add security information to result if available
            if self.enable_security_gateway:
                result.details["security_info"] = {
                    "dict_validation": dict_validation,
                    "security_level": self.security_level.value,
                    "correlation_id": correlation_id,
                }

            logger.info(
                "Successfully ingested dictionary '%s' into Bronze layer", source_name
            )
            return result

        except Exception as e:
            error_msg = f"Failed to ingest dictionary '{source_name}': {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(
                start_time,
                error_msg,
                Path(source_name),
                correlation_id=correlation_id,
            )

    async def ingest_data_dict_async(
        self, data: dict[str, Any], source_name: str = "dict_input"
    ) -> ProcessingResult:
        """Asynchronous wrapper for :meth:`ingest_data_dict`."""
        return await asyncio.to_thread(self.ingest_data_dict, data, source_name)

    def get_security_configuration(self) -> dict[str, Any]:
        """Get current security configuration."""
        config = {
            "security_level": self.security_level,
            "security_gateway_enabled": self.enable_security_gateway,
        }

        if self.enable_security_gateway and self.security_gateway:
            config["json_parser_config"] = (
                self.security_gateway.create_secure_json_parser()
            )

        return config

    def enable_security(
        self, security_level: Union[SecurityLevel, str] = SecurityLevel.STANDARD
    ) -> None:
        """Enable security gateway for data processing.

        Args:
            security_level: Security level enum or string
        """
        self.enable_security_gateway = True

        if isinstance(security_level, str):
            self.security_level = SecurityLevel.from_string(security_level)
        else:
            self.security_level = security_level

        # Reset gateway to pick up new security level
        self._security_gateway = None
        logger.info("Security gateway enabled with level=%s", self.security_level.value)

    def disable_security(self) -> None:
        """Disable security gateway for performance-critical scenarios."""
        self.enable_security_gateway = False
        self._security_gateway = None
        logger.info("Security gateway disabled")

    def _create_metadata(
        self, source_path: Path, data: dict[str, Any]
    ) -> LayerMetadata:
        """Create metadata for ingested data."""
        # Calculate file size if it's a real file
        file_size_bytes = 0
        if source_path.exists():
            file_size_bytes = source_path.stat().st_size

        # Calculate data hash
        data_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
        data_hash = hashlib.blake2b(data_str.encode("utf-8")).hexdigest()

        # Detect format (if format detection service is available)
        format_type = SupportedFormat.UNKNOWN
        if hasattr(self, "format_service") and self.format_service:
            try:
                detection_result = self.format_service.detect_format(data)
                format_type = detection_result.detected_format
            except Exception:
                # If format detection fails, keep UNKNOWN
                pass

        return LayerMetadata(
            source_path=source_path,
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
            record_count=len(data) if isinstance(data, dict) else 1,
            file_size_bytes=file_size_bytes,
            data_hash=data_hash,
            format_type=format_type,
        )

    def _create_error_result(
        self,
        start_time: datetime,
        error_msg: str,
        source_path: Path,
        *,
        security_info: Optional[Mapping[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> ProcessingResult:
        """Create error processing result with optional security context."""
        # Create metadata for the error result
        metadata = LayerMetadata(
            source_path=source_path,
            layer_name="bronze",
            ingestion_timestamp=start_time,
            processing_timestamp=datetime.now(),
        )

        # Create quality metrics indicating failure
        quality_metrics = DataQualityMetrics(
            overall_score=0.0,
            quality_issues=[error_msg],
            validation_errors=1,
        )

        processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        result = ProcessingResult(
            status=ProcessingStatus.FAILED,
            processed_count=0,
            success_count=0,
            error_count=1,
            warning_count=0,
            skipped_count=0,
            processing_time_ms=processing_time_ms,
            start_timestamp=start_time,
            metadata=metadata,
            quality_metrics=quality_metrics,
            end_timestamp=datetime.now(),
            errors=[error_msg],
        )

        # Add security information if available
        if security_info or self.enable_security_gateway:
            security_payload = security_info or {
                "security_level": self.security_level,
                "security_gateway_enabled": (self.enable_security_gateway),
            }
            if correlation_id:
                security_payload = dict(security_payload)
                security_payload["correlation_id"] = correlation_id
            result.details["security_info"] = security_payload

        return result

    def _read_file_content(self, file_path: Path) -> str:
        """Return file contents, leveraging the shared cache."""
        cached = self._content_cache.get_cached_content(file_path)
        if cached is not None:
            return cached

        with open(file_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        self._content_cache.cache_content(file_path, content)
        return content
