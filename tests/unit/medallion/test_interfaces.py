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
        self.assertEqual(SupportedFormat.ZEPHYR.value, "zephyr")
        self.assertEqual(SupportedFormat.TESTLINK.value, "testlink")
        self.assertEqual(SupportedFormat.JIRA_XRAY.value, "jira_xray")
        self.assertEqual(SupportedFormat.TESTRAIL.value, "testrail")
        self.assertEqual(SupportedFormat.GENERIC.value, "generic")
        self.assertEqual(SupportedFormat.UNKNOWN.value, "unknown")

    def test_quality_severity_enum(self):
        """Test QualitySeverity enum values."""
        self.assertEqual(QualitySeverity.CRITICAL.value, "critical")
        self.assertEqual(QualitySeverity.HIGH.value, "high")
        self.assertEqual(QualitySeverity.MEDIUM.value, "medium")
        self.assertEqual(QualitySeverity.LOW.value, "low")
        self.assertEqual(QualitySeverity.INFO.value, "info")

    def test_processing_status_enum(self):
        """Test ProcessingStatus enum values."""
        self.assertEqual(ProcessingStatus.PENDING.value, "pending")
        self.assertEqual(ProcessingStatus.IN_PROGRESS.value, "in_progress")
        self.assertEqual(ProcessingStatus.COMPLETED.value, "completed")
        self.assertEqual(ProcessingStatus.FAILED.value, "failed")
        self.assertEqual(ProcessingStatus.SKIPPED.value, "skipped")

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

        self.assertEqual(metadata.source_path, source_path)
        self.assertEqual(metadata.layer_name, "bronze")
        self.assertEqual(metadata.ingestion_timestamp, timestamp)
        self.assertEqual(metadata.format_type, SupportedFormat.ZEPHYR)
        self.assertEqual(metadata.record_count, 10)
        self.assertEqual(metadata.file_size_bytes, 1024)
        self.assertEqual(metadata.version, "1.0")  # Default value

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

        self.assertEqual(metrics.completeness_score, 85.5)
        self.assertEqual(metrics.consistency_score, 90.0)
        self.assertEqual(metrics.validity_score, 95.0)
        self.assertEqual(metrics.accuracy_score, 88.0)
        self.assertEqual(metrics.uniqueness_score, 100.0)
        self.assertEqual(metrics.overall_score, 91.7)
        self.assertEqual(metrics.validation_errors, 0)  # Default value
        self.assertEqual(len(metrics.quality_issues), 0)  # Default empty list

    def test_validation_result_creation(self):
        """Test ValidationResult dataclass creation."""
        validation = ValidationResult(
            is_valid=True,
            severity=QualitySeverity.LOW,
            error_count=0,
            warning_count=2,
            issues=["Minor formatting issue", "Optional field missing"],
        )

        self.assertTrue(validation.is_valid)
        self.assertEqual(validation.severity, QualitySeverity.LOW)
        self.assertEqual(validation.error_count, 0)
        self.assertEqual(validation.warning_count, 2)
        self.assertEqual(len(validation.issues), 2)
        self.assertIn("Minor formatting issue", validation.issues)

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

        self.assertEqual(lineage.data_id, "test123")
        self.assertEqual(lineage.source_layer, "bronze")
        self.assertEqual(lineage.target_layer, "silver")
        self.assertEqual(lineage.transformation_type, "standardization")
        self.assertEqual(lineage.transformation_timestamp, timestamp)
        self.assertEqual(lineage.parent_ids, ["parent1", "parent2"])
        self.assertEqual(len(lineage.child_ids), 0)  # Default empty list

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

        self.assertEqual(result.status, ProcessingStatus.COMPLETED)
        self.assertEqual(result.processed_count, 100)
        self.assertEqual(result.success_count, 95)
        self.assertEqual(result.error_count, 2)
        self.assertEqual(result.warning_count, 3)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(result.processing_time_ms, 1500.0)
        self.assertEqual(result.metadata, metadata)
        self.assertEqual(result.quality_metrics, quality_metrics)

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

        self.assertEqual(query.layer_name, "bronze")
        self.assertEqual(len(query.data_ids), 3)
        self.assertEqual(query.date_range, (start_date, end_date))
        self.assertEqual(len(query.format_types), 2)
        self.assertEqual(query.quality_threshold, 80.0)
        self.assertEqual(query.limit, 50)
        self.assertEqual(query.offset, 10)
        self.assertEqual(query.filters["status"], "active")

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

        self.assertEqual(len(layer_data.records), 2)
        self.assertEqual(len(layer_data.metadata), 2)
        self.assertEqual(layer_data.total_count, 100)
        self.assertEqual(layer_data.retrieved_count, 2)
        self.assertEqual(layer_data.query, query)
        self.assertIsInstance(layer_data.retrieved_at, datetime)

    def test_layer_metadata_defaults(self):
        """Test LayerMetadata default values."""
        metadata = LayerMetadata(
            source_path=Path("/test.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(),
        )

        self.assertEqual(metadata.data_hash, "")
        self.assertEqual(metadata.version, "1.0")
        self.assertEqual(metadata.format_type, SupportedFormat.UNKNOWN)
        self.assertEqual(metadata.record_count, 0)
        self.assertEqual(metadata.file_size_bytes, 0)
        self.assertEqual(metadata.processing_duration_ms, 0.0)
        self.assertEqual(metadata.user_id, "system")
        self.assertEqual(metadata.session_id, "")
        self.assertEqual(len(metadata.custom_metadata), 0)

    def test_data_quality_metrics_defaults(self):
        """Test DataQualityMetrics default values."""
        metrics = DataQualityMetrics()

        self.assertEqual(metrics.completeness_score, 0.0)
        self.assertEqual(metrics.consistency_score, 0.0)
        self.assertEqual(metrics.validity_score, 0.0)
        self.assertEqual(metrics.accuracy_score, 0.0)
        self.assertEqual(metrics.uniqueness_score, 0.0)
        self.assertEqual(metrics.overall_score, 0.0)
        self.assertEqual(len(metrics.quality_issues), 0)
        self.assertEqual(metrics.validation_errors, 0)
        self.assertEqual(metrics.validation_warnings, 0)
        self.assertEqual(metrics.data_anomalies, 0)
        self.assertIsInstance(metrics.calculated_at, datetime)

    def test_validation_result_defaults(self):
        """Test ValidationResult default values."""
        validation = ValidationResult(
            is_valid=True,
            severity=QualitySeverity.INFO,
        )

        self.assertTrue(validation.is_valid)
        self.assertEqual(validation.severity, QualitySeverity.INFO)
        self.assertEqual(validation.error_count, 0)
        self.assertEqual(validation.warning_count, 0)
        self.assertEqual(len(validation.issues), 0)
        self.assertEqual(len(validation.details), 0)
        self.assertIsInstance(validation.validation_timestamp, datetime)


if __name__ == "__main__":
    unittest.main()
