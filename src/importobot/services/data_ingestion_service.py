"""Unified data ingestion service with optional security hardening.

Handles core data ingestion responsibilities with configurable security validation.
Consolidates both basic and secure ingestion capabilities into a single service.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

from importobot.medallion.base_layers import BronzeLayer
from importobot.medallion.interfaces.data_models import (
    DataQualityMetrics,
    LayerMetadata,
    ProcessingResult,
)
from importobot.medallion.interfaces.enums import ProcessingStatus, SupportedFormat
from importobot.services.security_gateway import SecurityGateway
from importobot.services.security_types import SecurityLevel
from importobot.utils.logging import setup_logger
from importobot.utils.validation import validate_file_path, validate_json_dict

logger = setup_logger(__name__)


class DataIngestionService:
    """Unified data ingestion service with configurable security hardening."""

    def __init__(
        self,
        bronze_layer: BronzeLayer,
        security_level: Union[SecurityLevel, str] = SecurityLevel.STANDARD,
        enable_security_gateway: bool = False,
        format_service: Optional[Any] = None,
    ):
        """Initialize ingestion service.

        Args:
            bronze_layer: Bronze layer instance for data storage
            security_level: Security level enum or string
            enable_security_gateway: Whether to enable security gateway validation
            format_service: Optional format detection service
        """
        self.bronze_layer = bronze_layer

        if isinstance(security_level, str):
            self.security_level = SecurityLevel.from_string(security_level)
        else:
            self.security_level = security_level

        self.enable_security_gateway = enable_security_gateway
        self.format_service = format_service

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

        try:
            # Optional security validation for file path
            if self.enable_security_gateway and self.security_gateway is not None:
                file_validation = self.security_gateway.validate_file_operation(
                    file_path, "read"
                )
                if not file_validation["is_safe"]:
                    error_msg = (
                        f"File path security validation failed: "
                        f"{file_validation['security_issues']}"
                    )
                    logger.warning(error_msg)
                    return self._create_error_result(
                        start_time, error_msg, file_path, security_info=file_validation
                    )

            # Standard file validation
            validate_file_path(str(file_path))

            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Process content (with optional security validation)
            if self.enable_security_gateway and self.security_gateway is not None:
                json_validation = self.security_gateway.sanitize_api_input(
                    content, input_type="json", context={"source": str(file_path)}
                )
                if not json_validation["is_safe"]:
                    error_msg = (
                        f"JSON content security validation failed: "
                        f"{json_validation['security_issues']}"
                    )
                    logger.warning(error_msg)
                    return self._create_error_result(
                        start_time, error_msg, file_path, security_info=json_validation
                    )
                data = json_validation["sanitized_data"]
            else:
                # Standard JSON validation
                data = json.loads(content)
                validate_json_dict(data)

            # Create metadata
            metadata = self._create_metadata(file_path, data)

            # Add security information if available
            if self.enable_security_gateway:
                metadata.custom_metadata["security_validation"] = json_validation
                metadata.custom_metadata["security_level"] = self.security_level.value

            # Ingest data into Bronze layer
            result = self.bronze_layer.ingest(data, metadata)

            # Add security information to result if available
            if self.enable_security_gateway:
                result.details["security_info"] = {
                    "file_validation": file_validation,
                    "json_validation": json_validation,
                    "security_level": self.security_level.value,
                }

            logger.info("Successfully ingested file %s into Bronze layer", file_path)
            return result

        except FileNotFoundError:
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return self._create_error_result(start_time, error_msg, file_path)

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in file {file_path}: {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(start_time, error_msg, file_path)

        except Exception as e:
            error_msg = f"Failed to ingest file {file_path}: {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(start_time, error_msg, file_path)

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

        try:
            # Process JSON string (with optional security validation)
            if self.enable_security_gateway and self.security_gateway is not None:
                json_validation = self.security_gateway.sanitize_api_input(
                    json_string, input_type="json", context={"source": source_name}
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
                    )
                data = json_validation["sanitized_data"]
            else:
                # Standard JSON validation
                data = json.loads(json_string)
                validate_json_dict(data)

            # Create metadata
            source_path = Path(f"string_input/{source_name}")
            metadata = self._create_metadata(source_path, data)

            # Add security information if available
            if self.enable_security_gateway:
                metadata.custom_metadata["security_validation"] = json_validation
                metadata.custom_metadata["security_level"] = self.security_level.value

            # Ingest data into Bronze layer
            result = self.bronze_layer.ingest(data, metadata)

            # Add security information to result if available
            if self.enable_security_gateway:
                result.details["security_info"] = {
                    "json_validation": json_validation,
                    "security_level": self.security_level.value,
                }

            logger.info(
                "Successfully ingested JSON string '%s' into Bronze layer", source_name
            )
            return result

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON string '{source_name}': {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(start_time, error_msg, Path(source_name))

        except Exception as e:
            error_msg = f"Failed to ingest JSON string '{source_name}': {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(start_time, error_msg, Path(source_name))

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

        try:
            # Process dictionary data (with optional security validation)
            if self.enable_security_gateway and self.security_gateway is not None:
                dict_validation = self.security_gateway.sanitize_api_input(
                    data, input_type="json", context={"source": source_name}
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

            # Ingest data into Bronze layer
            result = self.bronze_layer.ingest(sanitized_data, metadata)

            # Add security information to result if available
            if self.enable_security_gateway:
                result.details["security_info"] = {
                    "dict_validation": dict_validation,
                    "security_level": self.security_level.value,
                }

            logger.info(
                "Successfully ingested dictionary '%s' into Bronze layer", source_name
            )
            return result

        except Exception as e:
            error_msg = f"Failed to ingest dictionary '{source_name}': {str(e)}"
            logger.error(error_msg)
            return self._create_error_result(start_time, error_msg, Path(source_name))

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
        data_hash = hashlib.md5(data_str.encode("utf-8")).hexdigest()

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
        security_info: Optional[dict] = None,
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
            result.details["security_info"] = security_info or {
                "security_level": self.security_level,
                "security_gateway_enabled": (self.enable_security_gateway),
            }

        return result
