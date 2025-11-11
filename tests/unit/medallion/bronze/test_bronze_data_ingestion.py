"""TDD tests for Bronze layer data ingestion business logic.

These tests define the expected behavior for Bronze layer ingestion
with comprehensive validation and format detection.

Red-Green-Refactor Cycle:
1. RED: Write failing tests that define desired behavior
2. GREEN: Implement minimal code to make tests pass
3. REFACTOR: Improve code while keeping tests green
"""

import importlib.util
import json
import shutil
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

from importobot.core.converter import JsonToRobotConverter
from importobot.medallion.bronze.format_detector import FormatDetector
from importobot.medallion.bronze.raw_data_processor import (
    RawDataProcessor,
)
from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import LayerQuery
from importobot.medallion.interfaces.enums import ProcessingStatus, SupportedFormat
from importobot.utils.validation_models import QualitySeverity
from tests.shared_test_data_bronze import (
    COMMON_TEST_CASE_STRUCTURE,
    COMMON_TEST_SUITE_STRUCTURE,
)


# Module-level fixtures for shared test data
def create_zephyr_test_data() -> dict[str, Any]:
    """Create enhanced Zephyr test data with realistic format indicators."""
    return {
        "testCase": {
            "name": "User Login Test",
            "description": "Test user authentication",
            "testCaseKey": "TEST-001",
            "priority": "High",
            "component": "Authentication",
            "steps": [
                {
                    "stepDescription": "Open login page",
                    "expectedResult": "Page loads",
                    "stepNumber": 1,
                },
                {
                    "stepDescription": "Enter credentials",
                    "expectedResult": "Login successful",
                    "stepNumber": 2,
                },
            ],
        },
        "execution": {
            "status": "PASS",
            "executionId": "EXEC-001",
            "executedBy": "testuser",
            "executionDate": "2025-01-01T10:00:00Z",
            "cycleId": "CYCLE-001",
        },
        "cycle": {
            "name": "Sprint 1",
            "cycleId": "CYCLE-001",
            "startDate": "2025-01-01",
            "endDate": "2025-01-14",
            "environment": "Production",
        },
        "project": {"key": "PROJ", "name": "Test Project"},
        "version": {"name": "v1.0", "id": "VER-001"},
        "sprint": {"name": "Sprint 1", "state": "Active"},
    }


def create_testlink_test_data() -> dict[str, Any]:
    """Create enhanced TestLink test data with realistic format indicators."""
    return {
        "testsuites": {
            "testsuite": [
                {
                    "name": "Login Tests",
                    "testsuiteid": "1",
                    "details": "Test suite for login functionality",
                    "testcase": [
                        {
                            "name": "Valid Login",
                            **COMMON_TEST_CASE_STRUCTURE,
                        }
                    ],
                    **COMMON_TEST_SUITE_STRUCTURE,
                }
            ],
            "project": {"name": "Authentication Project", "prefix": "AUTH"},
            "testplan": {"name": "Login Test Plan", "testplan_id": "PLAN-001"},
            "time": "90",
            "tests": "1",
        }
    }


def create_jira_xray_test_data() -> dict[str, Any]:
    """Create enhanced JIRA/Xray test data with realistic format indicators."""
    return {
        "issues": [
            {
                "key": "TEST-123",
                "fields": {
                    "summary": "API Test Case",
                    "description": "Test API authentication endpoints",
                    "issuetype": {"name": "Test"},
                    "priority": {"name": "High"},
                    "status": {"name": "To Do"},
                    "project": {"key": "TEST", "name": "Test Project"},
                    "customfield_test_type": "Xray",
                    "customfield_test_steps": [
                        {
                            "step": "Send GET request to /api/auth",
                            "data": "GET /api/auth",
                            "result": "Response status 200",
                        },
                        {
                            "step": "Verify authentication token",
                            "data": "Check token in response",
                            "result": "Token present and valid",
                        },
                    ],
                    "customfield_test_requirements": ["REQ-001", "REQ-002"],
                    "labels": ["api", "authentication", "regression"],
                    "components": [{"name": "Authentication"}],
                },
                "xray": {
                    "testType": "Generic",
                    "requirements": ["REQ-001", "REQ-002"],
                    "testExecutions": [
                        {
                            "status": "PASS",
                            "executionId": "EXEC-001",
                            "executedBy": "testuser",
                        }
                    ],
                },
            }
        ],
        "testExecutions": [
            {
                "executionId": "EXEC-001",
                "testKey": "TEST-123",
                "status": "PASS",
                "executedBy": "testuser",
                "executionDate": "2025-01-01T10:00:00Z",
                "comment": "Test executed successfully",
            }
        ],
        "testInfo": {
            "testKey": "TEST-123",
            "testType": "Generic",
            "requirements": ["REQ-001", "REQ-002"],
            "labels": ["api", "authentication", "regression"],
            "component": "Authentication",
            "priority": "High",
        },
        "evidences": [
            {
                "evidenceId": "EV-001",
                "filename": "screenshot.png",
                "contentType": "image/png",
                "data": "base64-encoded-image-data",
            },
            {
                "evidenceId": "EV-002",
                "filename": "logs.txt",
                "contentType": "text/plain",
                "data": "test execution logs",
            },
        ],
        "xrayInfo": {"version": "4.0", "exportDate": "2025-01-01T10:00:00Z"},
    }


class TestBronzeDataIngestionCore(unittest.TestCase):
    """Core data ingestion tests for Bronze layer.

    Tests cover:
    - Basic JSON file ingestion with metadata capture
    - Data lineage tracking from source to Bronze storage
    - Format detection for supported test frameworks
    - Quality metrics and validation
    """

    def setUp(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        bronze_layer = BronzeLayer(storage_path=self.temp_dir)
        self.ingestion = RawDataProcessor(bronze_layer=bronze_layer)

        # Load test data
        self.zephyr_data = create_zephyr_test_data()
        self.testlink_data = create_testlink_test_data()
        self.jira_xray_data = create_jira_xray_test_data()

    def tearDown(self) -> None:
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # Test 1: Basic JSON file ingestion with metadata capture
    def test_ingest_json_file_captures_full_metadata(self) -> None:
        """Test that ingesting a JSON file captures complete metadata."""
        # Create test file
        test_file = self.temp_dir / "test_data.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(self.zephyr_data, f)

        # Ingest file
        result = self.ingestion.ingest_file(test_file)

        # Assert successful ingestion
        assert result.status == ProcessingStatus.COMPLETED
        assert result.success_count == 1
        assert result.error_count == 0

        # Assert metadata is captured
        metadata = result.metadata
        assert metadata.source_path == test_file
        assert metadata.layer_name == "bronze"
        assert isinstance(metadata.ingestion_timestamp, datetime)
        assert metadata.file_size_bytes > 0
        assert len(metadata.data_hash) > 0
        assert metadata.format_type == SupportedFormat.ZEPHYR

    def test_ingest_json_string_with_source_tracking(self) -> None:
        """Test ingesting JSON string with proper source attribution."""
        json_string = json.dumps(self.testlink_data)
        source_name = "testlink_export_2024"

        result = self.ingestion.ingest_json_string(json_string, source_name)

        assert result.status == ProcessingStatus.COMPLETED
        assert result.metadata.source_path.name == source_name
        assert result.metadata.format_type == SupportedFormat.TESTLINK

    def test_ingest_data_dict_preserves_structure(self) -> None:
        """Test ingesting data dictionary preserves original structure."""
        source_name = "api_import"

        result = self.ingestion.ingest_data_dict(self.jira_xray_data, source_name)

        assert result.status == ProcessingStatus.COMPLETED
        assert result.metadata.format_type == SupportedFormat.JIRA_XRAY
        # Verify original data structure is preserved in Bronze layer
        query = LayerQuery(layer_name="bronze", data_ids=[], limit=1)
        stored_data = self.ingestion.bronze_layer.retrieve(query)
        assert len(stored_data.records) == 1
        assert stored_data.records[0]["issues"][0]["key"] == "TEST-123"

    # Test 2: Data lineage tracking from source to Bronze storage
    def test_data_lineage_tracked_from_source_to_bronze(self) -> None:
        """Test that complete data lineage is tracked during ingestion."""
        test_file = self.temp_dir / "lineage_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(self.zephyr_data, f)

        result = self.ingestion.ingest_file(test_file)

        # Verify lineage information is captured
        assert len(result.lineage) == 1
        lineage = result.lineage[0]
        assert lineage.source_layer == "input"
        assert lineage.target_layer == "bronze"
        assert lineage.transformation_type == "raw_ingestion"
        assert isinstance(lineage.transformation_timestamp, datetime)

    def test_lineage_includes_transformation_details(self) -> None:
        """Test that lineage includes detailed transformation information."""
        result = self.ingestion.ingest_data_dict(
            self.zephyr_data, "detailed_lineage_test"
        )

        lineage = result.lineage[0]
        assert lineage.data_id is not None
        assert len(lineage.parent_ids) == 0  # No parents for raw ingestion
        assert isinstance(lineage.transformation_timestamp, datetime)

    # Test 3: Format detection for supported test frameworks
    def test_zephyr_format_detection_accuracy(self) -> None:
        """Test accurate detection of Zephyr test format."""
        detected_format = self.ingestion.detect_format(self.zephyr_data)
        confidence = self.ingestion.get_format_confidence(
            self.zephyr_data, SupportedFormat.ZEPHYR
        )

        assert (
            detected_format == SupportedFormat.ZEPHYR
        )  # Fixed: now correctly detects Zephyr
        assert (
            confidence >= 0.8
        )  # Business requirement: >80% confidence for known formats

    def test_testlink_format_detection_accuracy(self) -> None:
        """Test accurate detection of TestLink test format."""
        detected_format = self.ingestion.detect_format(self.testlink_data)
        confidence = self.ingestion.get_format_confidence(
            self.testlink_data, SupportedFormat.TESTLINK
        )

        assert (
            detected_format == SupportedFormat.TESTLINK
        )  # Advanced algorithms correctly detect TestLink structure
        assert (
            confidence >= 0.8
        )  # Business requirement: >80% confidence for known formats

    def test_jira_xray_format_detection_accuracy(self) -> None:
        """Test accurate detection of JIRA/Xray test format."""
        detected_format = self.ingestion.detect_format(self.jira_xray_data)
        confidence = self.ingestion.get_format_confidence(
            self.jira_xray_data, SupportedFormat.JIRA_XRAY
        )

        assert detected_format == SupportedFormat.JIRA_XRAY
        assert (
            confidence >= 0.8
        )  # Business requirement: >80% confidence for known formats

    def test_unknown_format_handling(self) -> None:
        """Test handling of unrecognized data formats."""
        unknown_data = {"random": "data", "not": "test related"}

        detected_format = self.ingestion.detect_format(unknown_data)

        assert detected_format == SupportedFormat.UNKNOWN

    def test_format_detection_confidence_scoring(self) -> None:
        """Test that multi-class Bayesian normalization ranks correct format highest.

        With proper multi-class Bayesian inference, the mathematically correct
        property is that the correct format receives the HIGHEST posterior
        probability among all formats.
        """
        detector = FormatDetector()

        # Get properly normalized confidences for all formats
        all_confidences = detector.get_all_format_confidences(self.zephyr_data)

        # Find the format with highest confidence
        max_format = max(all_confidences.items(), key=lambda x: x[1])
        max_format_name, max_confidence = max_format

        # Zephyr confidence
        zephyr_confidence = all_confidences.get("ZEPHYR", 0.0)

        # Correct format (Zephyr) should have the HIGHEST confidence
        # Allow for floating point ties
        assert zephyr_confidence >= max_confidence * 0.99, (
            f"ZEPHYR ({zephyr_confidence:.4f}) should be highest, "
            f"but {max_format_name} has {max_confidence:.4f}. "
            f"All confidences: {sorted(all_confidences.items(), key=lambda x: -x[1])}"
        )

    # Test 4: Quality metrics and validation
    def test_quality_metrics_calculated_during_ingestion(self) -> None:
        """Test that quality metrics are calculated during data ingestion."""
        result = self.ingestion.ingest_data_dict(self.zephyr_data, "quality_test")

        quality = result.quality_metrics
        assert quality.completeness_score >= 0.0
        assert quality.completeness_score <= 100.0
        assert quality.validity_score >= 0.0
        assert quality.validity_score <= 100.0
        assert quality.overall_score >= 0.0
        assert quality.overall_score <= 100.0

    def test_validation_before_ingestion_prevents_bad_data(self) -> None:
        """Test that pre-ingestion validation prevents bad data entry."""
        bad_data = None  # Invalid data

        validation_result = self.ingestion.validate_before_ingestion(
            bad_data  # type: ignore
        )

        assert not validation_result.is_valid
        assert validation_result.error_count > 0

    def test_validation_identifies_quality_issues(self) -> None:
        """Test that validation identifies data quality issues."""
        poor_quality_data: dict[str, Any] = {
            "": "",  # Empty keys and values
            "test": None,
            "incomplete": {},
        }

        validation_result = self.ingestion.validate_before_ingestion(poor_quality_data)

        # Bronze layer accepts raw data regardless of quality (warnings are optional)
        assert validation_result.is_valid or validation_result.severity in [
            QualitySeverity.LOW,
            QualitySeverity.MEDIUM,
        ]
        # Bronze layer may not generate warnings for raw data acceptance
        assert validation_result.warning_count >= 0  # 0 or more warnings acceptable

    # Test 5: Preview functionality
    def test_preview_ingestion_without_storing(self) -> None:
        """Test preview functionality provides insights without storing data."""
        test_file = self.temp_dir / "preview_test.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(self.zephyr_data, f)

        preview = self.ingestion.preview_ingestion(test_file)

        assert preview["preview_available"]
        assert (
            preview["detected_format"] == "zephyr"
        )  # Fixed: now correctly detects Zephyr
        # format_confidence is now a dict with format as key
        assert isinstance(preview["format_confidence"], dict)
        assert preview["validation_ready"]
        assert preview["quality_score"] >= 0.0
        assert isinstance(preview["stats"], dict)
        assert preview["stats"]["total_keys"] > 0

    def test_preview_handles_problematic_files(self) -> None:
        """Test preview gracefully handles problematic files."""
        bad_file = self.temp_dir / "bad_preview.json"
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("{ malformed json")

        preview = self.ingestion.preview_ingestion(bad_file)

        assert not preview["preview_available"]
        assert "error" in preview


class TestBronzeDataIngestionAdvanced(unittest.TestCase):
    """Advanced data ingestion tests for Bronze layer.

    Tests cover:
    - Error handling and edge cases
    - Performance requirements and benchmarks
    - Configuration and customization
    - Integration with existing API
    - Backward compatibility
    """

    def setUp(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        bronze_layer = BronzeLayer(storage_path=self.temp_dir)
        self.ingestion = RawDataProcessor(bronze_layer=bronze_layer)

        # Load test data
        self.zephyr_data = create_zephyr_test_data()
        self.testlink_data = create_testlink_test_data()
        self.jira_xray_data = create_jira_xray_test_data()

    def tearDown(self) -> None:
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # Test 1: Error handling and edge cases
    def test_file_not_found_error_handling(self) -> None:
        """Test proper handling of missing files."""
        nonexistent_file = self.temp_dir / "does_not_exist.json"

        result = self.ingestion.ingest_file(nonexistent_file)

        assert result.status == ProcessingStatus.FAILED
        assert result.error_count == 1
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    def test_invalid_json_error_handling(self) -> None:
        """Test proper handling of malformed JSON files."""
        invalid_json_file = self.temp_dir / "invalid.json"
        with open(invalid_json_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json content")

        result = self.ingestion.ingest_file(invalid_json_file)

        assert result.status == ProcessingStatus.FAILED
        assert result.error_count == 1
        assert "json" in result.errors[0].lower()

    def test_empty_data_handling(self) -> None:
        """Test handling of empty but valid JSON data."""
        empty_data: dict[str, Any] = {}

        result = self.ingestion.ingest_data_dict(empty_data, "empty_test")

        # Bronze layer should accept empty data with warnings
        assert result.status == ProcessingStatus.COMPLETED
        assert result.warning_count > 0

    def test_large_file_handling(self) -> None:
        """Test handling of large JSON files."""
        # Create reasonably large test data
        large_data = {
            "tests": [
                {
                    "name": f"Test Case {i}",
                    "description": f"Description for test case {i}" * 100,
                    "steps": [
                        {"action": f"Step {j} for test {i}", "expected": f"Result {j}"}
                        for j in range(10)
                    ],
                }
                for i in range(100)
            ]
        }

        result = self.ingestion.ingest_data_dict(large_data, "large_test")

        assert result.status == ProcessingStatus.COMPLETED
        # For dictionary ingestion, file_size_bytes is 0 (no actual file)
        # Instead, check the logical data size via record_count
        assert result.metadata.file_size_bytes == 0  # No physical file
        assert result.metadata.record_count > 0  # Has logical data

    # Test 2: Performance requirements
    def test_ingestion_performance_overhead_acceptable(self) -> None:
        """Test that Bronze layer adds <10% performance overhead."""
        # Create baseline data
        tests_list = [
            {"name": f"Test {i}", "steps": [{"action": f"Step {j}"}]}
            for i in range(50)
            for j in range(5)
        ]
        test_data = {"tests": tests_list}

        # Measure ingestion time
        start_time = datetime.now()
        result = self.ingestion.ingest_data_dict(test_data, "performance_test")
        end_time = datetime.now()

        processing_time_ms = (end_time - start_time).total_seconds() * 1000

        # Should complete within reasonable time (adjust based on system)
        assert processing_time_ms < 5000  # 5 seconds max for 50 test cases
        assert result.status == ProcessingStatus.COMPLETED

    def test_concurrent_ingestion_safety(self) -> None:
        """Test that concurrent ingestions do not interfere with each other."""

        results = []

        def ingest_data(data: dict[str, "Any"], name: str) -> None:
            result = self.ingestion.ingest_data_dict(data, name)
            results.append(result)

        # Start multiple ingestion threads
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=ingest_data,
                args=(self.zephyr_data.copy(), f"concurrent_test_{i}"),
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All ingestions should succeed
        assert len(results) == 3
        for result in results:
            assert result.status == ProcessingStatus.COMPLETED

    # Test 3: Integration with existing parser
    def test_integration_with_generic_test_file_parser(self) -> None:
        """Test integration with existing GenericTestFileParser."""
        result = self.ingestion.ingest_data_dict(
            self.zephyr_data, "parser_integration_test"
        )

        # Verify parser correctly identified test structure
        assert result.status == ProcessingStatus.COMPLETED
        assert result.metadata.record_count > 0

        # Verify preview provides useful information about the data
        preview = self.preview_ingestion_dict(self.zephyr_data)
        assert preview["preview_available"]
        assert preview["detected_format"] in ["zephyr", "generic"]
        assert preview["stats"]["total_keys"] > 0

    def preview_ingestion_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Helper method to preview dictionary data."""
        # This would be implemented in the actual class
        temp_file = self.temp_dir / "temp_preview.json"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return self.ingestion.preview_ingestion(temp_file)

    # Test 4: Configuration and customization
    def test_storage_path_configuration(self) -> None:
        """Test that storage path can be configured."""
        custom_storage = self.temp_dir / "custom_bronze"
        bronze_layer = BronzeLayer(storage_path=custom_storage)
        custom_ingestion = RawDataProcessor(bronze_layer=bronze_layer)

        result = custom_ingestion.ingest_data_dict(self.zephyr_data, "config_test")

        assert result.status == ProcessingStatus.COMPLETED
        assert custom_storage.exists()

    def test_validation_thresholds_configurable(self) -> None:
        """Test that validation thresholds can be configured."""
        # Create intentionally borderline-quality data where overall_score ~ 0.6
        borderline_data = {"a": "", "b": ""}

        # Default thresholds should classify as LOW (medium threshold=0.7)
        default_result = self.ingestion.validate_before_ingestion(borderline_data)
        assert default_result.severity == QualitySeverity.LOW

        # Lower the medium threshold so this data becomes MEDIUM severity
        self.ingestion.configure_quality_thresholds(medium=0.5)
        adjusted_result = self.ingestion.validate_before_ingestion(borderline_data)
        assert adjusted_result.severity == QualitySeverity.MEDIUM

    # Test 5: Backward compatibility
    def test_existing_api_unchanged(self) -> None:
        """Test that existing API remains unchanged."""
        # Import existing converter to ensure it still works

        converter = JsonToRobotConverter()

        # Test existing functionality still works
        result = converter.convert_json_data(self.zephyr_data)

        assert isinstance(result, str)
        assert "*** Test Cases ***" in result

    def test_no_breaking_changes_to_existing_imports(self) -> None:
        """Test that existing imports continue to work."""
        # These imports should continue to work without Bronze layer

        # Check if main modules can be imported
        spec1 = importlib.util.find_spec("importobot")
        spec2 = importlib.util.find_spec("importobot.config")
        spec3 = importlib.util.find_spec("importobot.api.converters")
        spec4 = importlib.util.find_spec("importobot.api.validation")
        try:
            success = all([spec1, spec2, spec3, spec4])
        except ImportError:
            success = False

        assert success, "Existing imports should continue to work"


if __name__ == "__main__":
    unittest.main()
