"""Tests for Medallion architecture interfaces."""

import unittest
from datetime import datetime
from pathlib import Path

from importobot.medallion.interfaces.data_models import (
    DataQualityMetrics,
    LayerData,
    LayerMetadata,
    LayerQuery,
    LineageInfo,
    ProcessingResult,
)
from importobot.medallion.interfaces.enums import ProcessingStatus, SupportedFormat
from importobot.utils.validation_models import QualitySeverity, ValidationResult


class TestMedallionInterfaces(unittest.TestCase):
    """Test cases for Medallion architecture interface classes."""

    def test_test_format_type_enum(self):
        """Test SupportedFormat enum values."""
        assert SupportedFormat.ZEPHYR.value == "zephyr"
        assert SupportedFormat.TESTLINK.value == "testlink"
        assert SupportedFormat.JIRA_XRAY.value == "jira_xray"
        assert SupportedFormat.TESTRAIL.value == "testrail"
        assert SupportedFormat.GENERIC.value == "generic"
        assert SupportedFormat.UNKNOWN.value == "unknown"

    def test_quality_severity_enum(self):
        """Test QualitySeverity enum values."""
        assert QualitySeverity.CRITICAL.value == "critical"
        assert QualitySeverity.HIGH.value == "high"
        assert QualitySeverity.MEDIUM.value == "medium"
        assert QualitySeverity.LOW.value == "low"
        assert QualitySeverity.INFO.value == "info"

    def test_processing_status_enum(self):
        """Test ProcessingStatus enum values."""
        assert ProcessingStatus.PENDING.value == "pending"
        assert ProcessingStatus.IN_PROGRESS.value == "in_progress"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.SKIPPED.value == "skipped"

    def test_layer_metadata_creation(self):
        """Test LayerMetadata dataclass creation."""
        source_path = Path("/test/data.json")
        timestamp = datetime.now()

        metadata = LayerMetadata(
            source_path=source_path,
            layer_name="bronze",
            ingestion_timestamp=timestamp,
            format_type=SupportedFormat.ZEPHYR,
            record_count=10,
            file_size_bytes=1024,
        )

        assert metadata.source_path == source_path
        assert metadata.layer_name == "bronze"
        assert metadata.ingestion_timestamp == timestamp
        assert metadata.format_type == SupportedFormat.ZEPHYR
        assert metadata.record_count == 10
        assert metadata.file_size_bytes == 1024
        assert metadata.version == "1.0"  # Default value

    def test_data_quality_metrics_creation(self):
        """Test DataQualityMetrics dataclass creation."""
        metrics = DataQualityMetrics(
            completeness_score=85.5,
            consistency_score=90.0,
            validity_score=95.0,
            accuracy_score=88.0,
            uniqueness_score=100.0,
            overall_score=91.7,
        )

        assert metrics.completeness_score == 85.5
        assert metrics.consistency_score == 90.0
        assert metrics.validity_score == 95.0
        assert metrics.accuracy_score == 88.0
        assert metrics.uniqueness_score == 100.0
        assert metrics.overall_score == 91.7
        assert metrics.validation_errors == 0  # Default value
        assert len(metrics.quality_issues) == 0  # Default empty list

    def test_validation_result_creation(self):
        """Test ValidationResult dataclass creation."""
        validation = ValidationResult(
            is_valid=True,
            severity=QualitySeverity.LOW,
            error_count=0,
            warning_count=2,
            issues=["Minor formatting issue", "Optional field missing"],
        )

        assert validation.is_valid
        assert validation.severity == QualitySeverity.LOW
        assert validation.error_count == 0
        assert validation.warning_count == 2
        assert len(validation.issues) == 2
        assert "Minor formatting issue" in validation.issues

    def test_lineage_info_creation(self):
        """Test LineageInfo dataclass creation."""
        timestamp = datetime.now()
        lineage = LineageInfo(
            data_id="test123",
            source_layer="bronze",
            target_layer="silver",
            transformation_type="standardization",
            transformation_timestamp=timestamp,
            parent_ids=["parent1", "parent2"],
        )

        assert lineage.data_id == "test123"
        assert lineage.source_layer == "bronze"
        assert lineage.target_layer == "silver"
        assert lineage.transformation_type == "standardization"
        assert lineage.transformation_timestamp == timestamp
        assert lineage.parent_ids == ["parent1", "parent2"]
        assert len(lineage.child_ids) == 0  # Default empty list

    def test_processing_result_creation(self):
        """Test ProcessingResult dataclass creation."""
        start_time = datetime.now()
        metadata = LayerMetadata(
            source_path=Path("/test.json"),
            layer_name="bronze",
            ingestion_timestamp=start_time,
        )
        quality_metrics = DataQualityMetrics(overall_score=85.0)

        result = ProcessingResult(
            status=ProcessingStatus.COMPLETED,
            processed_count=100,
            success_count=95,
            error_count=2,
            warning_count=3,
            skipped_count=0,
            processing_time_ms=1500.0,
            start_timestamp=start_time,
            metadata=metadata,
            quality_metrics=quality_metrics,
        )

        assert result.status == ProcessingStatus.COMPLETED
        assert result.processed_count == 100
        assert result.success_count == 95
        assert result.error_count == 2
        assert result.warning_count == 3
        assert result.skipped_count == 0
        assert result.processing_time_ms == 1500.0
        assert result.metadata == metadata
        assert result.quality_metrics == quality_metrics

    def test_layer_query_creation(self):
        """Test LayerQuery dataclass creation."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

        query = LayerQuery(
            layer_name="bronze",
            data_ids=["id1", "id2", "id3"],
            date_range=(start_date, end_date),
            format_types=[SupportedFormat.ZEPHYR, SupportedFormat.TESTLINK],
            quality_threshold=80.0,
            limit=50,
            offset=10,
            filters={"status": "active", "priority": "high"},
        )

        assert query.layer_name == "bronze"
        assert len(query.data_ids) == 3
        assert query.date_range == (start_date, end_date)
        assert len(query.format_types) == 2
        assert query.quality_threshold == 80.0
        assert query.limit == 50
        assert query.offset == 10
        assert query.filters["status"] == "active"

    def test_layer_data_creation(self):
        """Test LayerData dataclass creation."""
        records = [{"test": "data1"}, {"test": "data2"}]
        metadata_list = [
            LayerMetadata(Path("/test1.json"), "bronze", datetime.now()),
            LayerMetadata(Path("/test2.json"), "bronze", datetime.now()),
        ]
        query = LayerQuery(layer_name="bronze")

        layer_data = LayerData(
            records=records,
            metadata=metadata_list,
            total_count=100,
            retrieved_count=2,
            query=query,
        )

        assert len(layer_data.records) == 2
        assert len(layer_data.metadata) == 2
        assert layer_data.total_count == 100
        assert layer_data.retrieved_count == 2
        assert layer_data.query == query
        assert isinstance(layer_data.retrieved_at, datetime)

    def test_layer_metadata_defaults(self):
        """Test LayerMetadata default values."""
        metadata = LayerMetadata(
            source_path=Path("/test.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        assert metadata.data_hash == ""
        assert metadata.version == "1.0"
        assert metadata.format_type == SupportedFormat.UNKNOWN
        assert metadata.record_count == 0
        assert metadata.file_size_bytes == 0
        assert metadata.processing_duration_ms == 0.0
        assert metadata.user_id == "system"
        assert metadata.session_id == ""
        assert len(metadata.custom_metadata) == 0

    def test_data_quality_metrics_defaults(self):
        """Test DataQualityMetrics default values."""
        metrics = DataQualityMetrics()

        assert metrics.completeness_score == 0.0
        assert metrics.consistency_score == 0.0
        assert metrics.validity_score == 0.0
        assert metrics.accuracy_score == 0.0
        assert metrics.uniqueness_score == 0.0
        assert metrics.overall_score == 0.0
        assert len(metrics.quality_issues) == 0
        assert metrics.validation_errors == 0
        assert metrics.validation_warnings == 0
        assert metrics.data_anomalies == 0
        assert isinstance(metrics.calculated_at, datetime)

    def test_validation_result_defaults(self):
        """Test ValidationResult default values."""
        validation = ValidationResult(
            is_valid=True,
            severity=QualitySeverity.INFO,
        )

        assert validation.is_valid
        assert validation.severity == QualitySeverity.INFO
        assert validation.error_count == 0
        assert validation.warning_count == 0
        assert len(validation.issues) == 0
        assert len(validation.details) == 0
        assert isinstance(validation.validation_timestamp, datetime)


if __name__ == "__main__":
    unittest.main()
