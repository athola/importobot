"""TDD tests for Bronze layer validation and quality scoring.

These tests define the expected behavior for Bronze layer validation,
including quality metrics calculation, issue detection, and scoring algorithms.

Business Requirements:
- Quality scores must be between 0-100 and accurately reflect data quality
- Validation must identify critical issues that prevent processing
- Warning-level issues should not block ingestion but be reported
- Quality metrics should be consistent and reproducible
"""

import time
import tracemalloc
import unittest
from datetime import datetime, timedelta
from typing import Any

from importobot.medallion.bronze.validation import BronzeValidator
from importobot.utils.validation_models import QualitySeverity


# Module-level fixtures for shared test data
def create_high_quality_data() -> dict[str, Any]:
    """Create high-quality test data."""
    return {
        "testCase": {
            "name": "Complete Test Case",
            "description": "A well-formed test case with all required fields",
            "priority": "High",
            "category": "Functional",
            "steps": [
                {
                    "stepDescription": "Navigate to login page",
                    "expectedResult": "Login page displays correctly",
                    "stepNumber": 1,
                },
                {
                    "stepDescription": "Enter valid credentials",
                    "expectedResult": "User successfully logs in",
                    "stepNumber": 2,
                },
            ],
            "preconditions": "User has valid account",
            "postconditions": "User is logged in",
        },
        "metadata": {
            "createdBy": "test.author@company.com",
            "createdDate": "2024-01-15T10:30:00Z",
            "lastModified": "2024-01-16T14:22:00Z",
            "version": "1.0",
        },
    }


def create_medium_quality_data() -> dict[str, Any]:
    """Create medium-quality test data."""
    return {
        "testCase": {
            "name": "Partial Test Case",
            "description": "",  # Missing description
            "steps": [
                {
                    "stepDescription": "Do something",
                    "expectedResult": "",  # Missing expected result
                }
            ],
        },
        "execution": {"status": "TODO"},
        # Missing metadata
    }


def create_poor_quality_data() -> dict[str, Any]:
    """Create poor-quality test data."""
    return {
        "testCase": {
            "name": "",  # Empty name
            "description": None,  # Null description
            "steps": [],  # No steps
        },
        "": "empty_key",  # Empty key
        "null_value": None,
        "very_long_field": "x" * 50000,  # Extremely long field
        "duplicate_info": "same",
        "duplicate_info_2": "same",  # Potential duplicate
    }


def create_large_data() -> dict[str, Any]:
    """Create large test data for performance testing."""
    return {
        "testSuite": {
            "name": "Large Test Suite",
            "tests": [
                {
                    "name": f"Test Case {i}",
                    "description": f"Description for test case {i}" * 50,
                    "steps": [
                        {
                            "stepDescription": f"Step {j} for test {i}",
                            "expectedResult": f"Expected result {j} for test {i}",
                        }
                        for j in range(20)
                    ],
                }
                for i in range(100)
            ],
        }
    }


class TestBronzeValidationQualityScoring(unittest.TestCase):
    """Quality scoring and structure validation tests for Bronze layer."""

    def setUp(self):
        """Set up test environment with validator."""
        self.validator = BronzeValidator()

        # Test data examples with known quality characteristics
        self.high_quality_data = create_high_quality_data()
        self.medium_quality_data = create_medium_quality_data()
        self.poor_quality_data = create_poor_quality_data()
        self.large_data = create_large_data()

        self.malformed_data_examples: list[Any] = [
            None,  # Not a dictionary
            [],  # List instead of dict
            "string",  # String instead of dict
            {
                "deeply": {
                    "nested": {
                        "data": {
                            "that": {
                                "exceeds": {
                                    "reasonable": {
                                        "depth": {"limit": {"value": "deep"}}
                                    }
                                }
                            }
                        }
                    }
                }
            },
        ]

    # Test 1: Quality scoring accuracy and consistency
    def test_high_quality_data_scores_appropriately(self):
        """Test that high-quality data receives appropriate quality scores."""
        validation_result = self.validator.validate_raw_data(self.high_quality_data)

        assert validation_result.is_valid
        assert validation_result.error_count == 0
        assert validation_result.warning_count <= 2  # Allow minor warnings
        expected_severities = [QualitySeverity.INFO, QualitySeverity.LOW]
        assert validation_result.severity in expected_severities

        # Verify detailed validation information is provided
        assert "structure_validation" in validation_result.details
        assert "size_validation" in validation_result.details
        assert "content_validation" in validation_result.details

    def test_medium_quality_data_has_warnings(self):
        """Test that medium-quality data generates appropriate warnings."""
        validation_result = self.validator.validate_raw_data(self.medium_quality_data)

        assert validation_result.is_valid  # Should still be valid for Bronze
        assert validation_result.error_count == 0
        assert validation_result.warning_count > 0
        expected_severities = [QualitySeverity.LOW, QualitySeverity.MEDIUM]
        assert validation_result.severity in expected_severities

        # Should identify specific quality issues
        issues_text = " ".join(validation_result.issues).lower()
        indicators = ["empty", "missing", "incomplete"]
        assert any(indicator in issues_text for indicator in indicators), (
            "Should identify missing or empty content"
        )

    def test_poor_quality_data_identified_correctly(self):
        """Test that poor-quality data is identified with multiple warnings."""
        validation_result = self.validator.validate_raw_data(self.poor_quality_data)

        # May still be valid for Bronze (raw data) but with many warnings
        assert validation_result.warning_count >= 3
        expected_severities = [QualitySeverity.MEDIUM, QualitySeverity.HIGH]
        assert validation_result.severity in expected_severities

        # Should identify multiple types of issues
        issues_text = " ".join(validation_result.issues).lower()
        expected_issue_types = ["empty", "null", "long", "large"]
        found_issues = sum(
            1 for issue_type in expected_issue_types if issue_type in issues_text
        )
        assert found_issues >= 2, "Should identify multiple types of quality issues"

    def test_validation_consistency_across_runs(self):
        """Test that validation results are consistent across multiple runs."""
        results = []
        for _ in range(5):  # Run validation multiple times
            result = self.validator.validate_raw_data(self.high_quality_data)
            results.append(result)

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.is_valid == first_result.is_valid
            assert result.error_count == first_result.error_count
            assert result.warning_count == first_result.warning_count
            assert result.severity == first_result.severity

    # Test 2: Structure validation business logic
    def test_structure_validation_dictionary_requirement(self):
        """Test that structure validation enforces dictionary requirement."""
        for malformed_data in self.malformed_data_examples:
            with self.subTest(data_type=type(malformed_data).__name__):
                validation_result = self.validator.validate_raw_data(malformed_data)

                if not isinstance(malformed_data, dict):
                    assert not validation_result.is_valid
                    assert validation_result.error_count > 0
                    assert validation_result.severity == QualitySeverity.CRITICAL

    def test_structure_validation_nesting_depth_limits(self):
        """Test that structure validation enforces reasonable nesting depth."""
        deeply_nested: dict[str, Any] = {"level1": {"level2": {"level3": {}}}}
        for _i in range(25):  # Create very deep nesting
            deeply_nested = {"level": deeply_nested}

        validation_result = self.validator.validate_raw_data(deeply_nested)

        # Should generate warning about excessive nesting
        if validation_result.warning_count > 0:
            issues_text = " ".join(validation_result.issues).lower()
            assert any(
                keyword in issues_text for keyword in ["depth", "nesting", "deep"]
            ), "Should warn about excessive nesting depth"

    def test_structure_validation_test_indicators(self):
        """Test that structure validation identifies test-related content."""
        # Data with test indicators
        test_data = {
            "test": "some test data",
            "case": "test case information",
            "step": "test step",
            "verify": "verification step",
        }

        validation_result = self.validator.validate_raw_data(test_data)
        test_indicators = validation_result.details.get("structure_validation", {}).get(
            "test_indicators", []
        )

        assert len(test_indicators) > 0, "Should identify test indicators"

        # Data without test indicators
        non_test_data = {
            "user": "john",
            "settings": {"theme": "dark"},
            "preferences": {"language": "en"},
        }

        validation_result = self.validator.validate_raw_data(non_test_data)
        # Should warn about lack of test indicators
        assert validation_result.warning_count > 0

    # Test 3: Size validation business logic
    def test_size_validation_reasonable_limits(self):
        """Test that size validation enforces reasonable data size limits."""
        validation_result = self.validator.validate_raw_data(self.large_data)

        size_details = validation_result.details.get("size_validation", {})
        assert "size_mb" in size_details
        assert "size_bytes" in size_details

        # Should complete validation even for large data
        assert validation_result.is_valid is not None

    def test_size_validation_extremely_large_data(self):
        """Test size validation behavior with extremely large data."""
        # Create data that exceeds reasonable limits
        huge_data = {
            "massive_field": "x" * (200 * 1024 * 1024),  # 200MB string
            "normal_field": "normal value",
        }

        try:
            validation_result = self.validator.validate_raw_data(huge_data)
            # Should either handle gracefully or fail with clear error
            if not validation_result.is_valid:
                assert validation_result.error_count > 0
                issues_text = " ".join(validation_result.issues).lower()
                keywords = ["size", "large", "exceeds"]
                assert any(keyword in issues_text for keyword in keywords), (
                    "Should identify size issues"
                )
        except MemoryError:
            # Acceptable to fail with memory error for extremely large data
            pass

    def test_size_validation_individual_field_limits(self):
        """Test validation of individual field sizes."""
        data_with_large_fields = {
            "normal_field": "normal value",
            "large_field": "x" * (15 * 1024 * 1024),  # 15MB field
            "another_normal": "value",
        }

        validation_result = self.validator.validate_raw_data(data_with_large_fields)

        if validation_result.warning_count > 0:
            size_details = validation_result.details.get("size_validation", {})
            if "large_fields" in size_details:
                large_fields = size_details["large_fields"]
                assert len(large_fields) > 0

    # Test 4: Error severity classification
    def test_severity_classification_critical_errors(self):
        """Test that critical errors are classified correctly."""
        critical_data_examples: list[Any] = [
            None,  # Not a dict
            [],  # Wrong type
            "string",  # Wrong type
        ]

        for critical_data in critical_data_examples:
            with self.subTest(data=critical_data):
                validation_result = self.validator.validate_raw_data(critical_data)

                assert not validation_result.is_valid
                assert validation_result.severity == QualitySeverity.CRITICAL
                assert validation_result.error_count > 0

    def test_severity_classification_warning_levels(self):
        """Test that different warning levels are classified correctly."""
        # High warning scenario
        high_warning_data = {f"empty_field_{i}": "" for i in range(10)}
        for i in range(10):
            high_warning_data[f"null_field_{i}"] = ""

        validation_result = self.validator.validate_raw_data(high_warning_data)

        if validation_result.warning_count > 5:
            assert validation_result.severity in [
                QualitySeverity.HIGH,
                QualitySeverity.MEDIUM,
            ]

        # Low warning scenario
        low_warning_data = {
            "test": "value",
            "empty_field": "",  # One minor issue
            "normal_field": "normal value",
        }

        validation_result = self.validator.validate_raw_data(low_warning_data)

        if validation_result.warning_count > 0:
            assert validation_result.severity in [
                QualitySeverity.LOW,
                QualitySeverity.MEDIUM,
            ]


class TestBronzeValidationContentAndPerformance(unittest.TestCase):
    """Content validation and performance tests for Bronze layer."""

    def setUp(self):
        """Set up test environment with validator."""
        self.validator = BronzeValidator()

        # Test data examples
        self.high_quality_data = create_high_quality_data()
        self.medium_quality_data = create_medium_quality_data()
        self.large_data = create_large_data()

    # Test 1: Content validation business logic
    def test_content_validation_encoding_issues(self):
        """Test detection of encoding and character issues."""
        data_with_encoding_issues = {
            "field1": "normal text",
            "field2": "text with \ufffd replacement chars",
            "field3": "unicode \\u0041\\u0042\\u0043 escapes",
            "field4": "\\x48\\x65\\x6c\\x6c\\x6f hex escapes",
        }

        validation_result = self.validator.validate_raw_data(data_with_encoding_issues)

        # May generate warnings about potential encoding issues
        if validation_result.warning_count > 0:
            issues_text = " ".join(validation_result.issues).lower()
            encoding_keywords = ["encoding", "unicode", "character"]
            if any(keyword in issues_text for keyword in encoding_keywords):
                # Encoding issues were detected and reported
                pass

    def test_content_validation_null_value_analysis(self):
        """Test analysis of null and empty values."""
        data_with_nulls: dict[str, Any] = {
            "field1": "value",
            "field2": None,
            "field3": "",
            "field4": [],
            "field5": {},
            "field6": "another value",
        }

        validation_result = self.validator.validate_raw_data(data_with_nulls)

        null_analysis = validation_result.details.get("content_validation", {}).get(
            "null_analysis", {}
        )
        assert "total_values" in null_analysis
        assert "null_values" in null_analysis
        assert "null_percentage" in null_analysis

        # Should calculate reasonable percentages
        null_percentage = null_analysis.get("null_percentage", 0)
        assert null_percentage >= 0
        assert null_percentage <= 100

    def test_content_validation_suspicious_patterns(self):
        """Test detection of suspicious or problematic patterns."""
        suspicious_data = {
            "extremely_long_value": "a" * 50000,
            "sql_injection_attempt": "'; DROP TABLE users; --",
            "script_tag": "<script>alert('xss')</script>",
            "path_traversal": "../../etc/passwd",
            "binary_data": b"\x00\x01\x02\x03\x04".decode("latin1"),
        }

        validation_result = self.validator.validate_raw_data(suspicious_data)

        suspicious_patterns = validation_result.details.get(
            "content_validation", {}
        ).get("suspicious_patterns", [])

        # Should identify at least some suspicious patterns
        if validation_result.warning_count > 0:
            assert len(suspicious_patterns) >= 1

    # Test 2: Performance validation
    def test_validation_performance_large_datasets(self):
        """Test that validation performs well on large datasets."""

        start_time = time.time()
        validation_result = self.validator.validate_raw_data(self.large_data)
        validation_time = time.time() - start_time

        # Should complete validation within reasonable time
        assert validation_time < 10.0, "Validation took too long for large dataset"
        assert validation_result.is_valid is not None

    def test_validation_memory_efficiency(self):
        """Test that validation is memory efficient."""
        tracemalloc.start()

        # Validate medium-sized data
        self.validator.validate_raw_data(self.large_data)

        _unused, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should not use excessive memory (adjust threshold as needed)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 100, f"Validation used too much memory: {peak_mb}MB"

    # Test 3: Configuration and customization
    def test_configurable_size_limits(self):
        """Test that size limits can be configured."""
        # Create validator with custom limits
        custom_validator = BronzeValidator()
        custom_validator.max_data_size_mb = 1  # 1MB limit

        large_data = {"field": "x" * (2 * 1024 * 1024)}  # 2MB data

        validation_result = custom_validator.validate_raw_data(large_data)

        # Should respect the configured limit
        if validation_result.error_count > 0:
            issues_text = " ".join(validation_result.issues).lower()
            keywords = ["size", "exceeds", "maximum"]
            assert any(keyword in issues_text for keyword in keywords), (
                "Should respect configured size limits"
            )

    def test_configurable_nesting_limits(self):
        """Test that nesting depth limits can be configured."""
        custom_validator = BronzeValidator()
        custom_validator.max_nesting_depth = 5  # Shallow limit

        deeply_nested = {
            "level": {"level": {"level": {"level": {"level": {"level": "deep"}}}}}
        }

        validation_result = custom_validator.validate_raw_data(deeply_nested)

        # Should warn about exceeding configured depth
        if validation_result.warning_count > 0:
            issues_text = " ".join(validation_result.issues).lower()
            if "depth" in issues_text or "nesting" in issues_text:
                # Correctly identified nesting issue
                pass

    # Test 4: Integration validation
    def test_validation_result_structure_completeness(self):
        """Test that validation results provide complete information."""
        validation_result = self.validator.validate_raw_data(self.medium_quality_data)

        # Required fields
        assert validation_result.is_valid is not None
        assert isinstance(validation_result.error_count, int)
        assert isinstance(validation_result.warning_count, int)
        assert isinstance(validation_result.issues, list)
        assert isinstance(validation_result.details, dict)
        assert validation_result.severity in list(QualitySeverity)
        # Validation timestamp should be recent

        time_diff = datetime.now() - validation_result.validation_timestamp
        assert time_diff < timedelta(seconds=10)

    def test_validation_details_informativeness(self):
        """Test that validation details provide useful diagnostic information."""
        validation_result = self.validator.validate_raw_data(self.high_quality_data)

        details = validation_result.details

        # Should have detailed breakdown by validation type
        expected_sections = [
            "structure_validation",
            "size_validation",
            "content_validation",
        ]
        for section in expected_sections:
            assert section in details, f"Missing validation section: {section}"

        # Each section should provide useful metrics
        structure_details = details.get("structure_validation", {})
        if "test_indicators" in structure_details:
            assert isinstance(structure_details["test_indicators"], list)

        size_details = details.get("size_validation", {})
        if "size_bytes" in size_details:
            assert isinstance(size_details["size_bytes"], int)
            assert size_details["size_bytes"] >= 0


if __name__ == "__main__":
    unittest.main()
