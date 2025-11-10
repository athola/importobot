"""TDD Integration tests for complete format detection workflow.

# Test data contains long strings

Tests the integration of FormatDetector, FormatRegistry, and format definitions
working together to accurately detect test management system formats with
real-world data patterns and edge cases.

Business Requirements:
- End-to-end format detection must achieve >80% accuracy
- Integration must handle real-world data variations
- System must gracefully handle malformed or ambiguous data
- Detection confidence must correlate with actual format matches
- Performance must be acceptable for Bronze layer ingestion
"""

import time
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from importobot.medallion.bronze.format_detector import FormatDetector
from importobot.medallion.interfaces.enums import SupportedFormat
from tests.utils import create_test_case_base

try:  # pragma: no cover - optional dependency guard
    import numpy

    _ = numpy  # Mark as used to avoid F401
except ImportError as exc:  # pragma: no cover
    raise unittest.SkipTest(
        "numpy dependency required for format detection tests"
    ) from exc


class TestFormatDetectionIntegration(unittest.TestCase):
    """Integration tests for complete format detection workflow."""

    def setUp(self) -> None:
        """Set up test environment with detector and real-world test data."""
        self.detector = FormatDetector()

        # Real-world test data samples based on actual exports
        self.test_data_samples: dict[str, dict[str, Any]] = {
            "zephyr_complete": {
                "project": {"key": "MYPROJ", "name": "My Project"},
                "testCase": {
                    "key": "MYPROJ-TC-123",
                    "name": "User Authentication Test",
                    "description": "Verify user login functionality",
                    "steps": [
                        {
                            "stepDescription": "Navigate to login page",
                            "expectedResult": "Login page is displayed",
                            "testData": "Valid credentials",
                        },
                        {
                            "stepDescription": "Enter username and password",
                            "expectedResult": "User is logged in successfully",
                        },
                    ],
                    "priority": "HIGH",
                    "component": "Authentication",
                    "labels": ["login", "security", "regression"],
                },
                "execution": {
                    "status": "PASSED",
                    "executedOn": "2024-01-15T10:30:00Z",
                    "executedBy": "john.tester@company.com",
                    "environment": "staging",
                    "actualResult": "Login successful",
                    "defects": [],
                },
                "cycle": {
                    "name": "Sprint 23 Testing",
                    "version": "v2.1.0",
                    "environment": "staging",
                    "startDate": "2024-01-10",
                    "endDate": "2024-01-20",
                },
            },
            "xray_with_jira": {
                "expand": "renderedFields,names,schema,operations",
                "maxResults": 50,
                "total": 156,
                "issues": [
                    {
                        "key": "XRT-456",
                        "self": (
                            "https://company.atlassian.net/rest/api/2/issue/XRT-456"
                        ),
                        "fields": {
                            "summary": "API Authentication Endpoint Test",
                            "description": (
                                "Test the /auth endpoint with various credentials"
                            ),
                            "issuetype": {
                                "name": "Test",
                                "iconUrl": (
                                    "https://company.atlassian.net/images/icons/"
                                    "issuetypes/test.png"
                                ),
                            },
                            "priority": {"name": "High"},
                            "status": {"name": "Ready for Testing"},
                            "assignee": {
                                "displayName": "Jane Tester",
                                "emailAddress": "jane.tester@company.com",
                            },
                            "customfield_10100": {"value": "Manual"},  # Xray test type
                            "labels": ["api", "authentication", "regression", "smoke"],
                        },
                    }
                ],
                "testExecutions": [
                    {
                        "key": "XTE-789",
                        "status": "PASS",
                        "executedBy": "jane.tester@company.com",
                        "executedOn": "2024-01-15T14:22:00Z",
                        "testInfo": {
                            "key": "XRT-456",
                            "summary": "API Authentication Test",
                        },
                        "evidences": [
                            {
                                "filename": "api_response.json",
                                "contentType": "application/json",
                            }
                        ],
                    }
                ],
            },
            "testrail_api_response": {
                "runs": [
                    {
                        "id": 123,
                        "suite_id": 456,
                        "project_id": 1,
                        "name": "API Integration Test Run",
                        "description": "Testing API endpoints for v2.1 release",
                        "milestone_id": 789,
                        "assignedto_id": 5,
                        "include_all": True,
                        "is_completed": False,
                        "created_on": 1705320000,
                        "created_by": 5,
                        "url": "https://company.testrail.net/index.php?/runs/view/123",
                    }
                ],
                "tests": [
                    {
                        "id": 1001,
                        "case_id": 2001,
                        "status_id": 1,  # Passed
                        "title": "Test GET /users endpoint",
                        "run_id": 123,
                        "assignedto_id": 5,
                        "created_on": 1705320000,
                    },
                    {
                        "id": 1002,
                        "case_id": 2002,
                        "status_id": 5,  # Failed
                        "title": "Test POST /users endpoint",
                        "run_id": 123,
                        "comment": "Validation error on email field",
                    },
                ],
                "cases": [
                    create_test_case_base(
                        test_id=2001,
                        title="Verify GET users returns user list",
                        refs="REQ-123,REQ-124",
                    ),
                    {
                        **create_test_case_base(
                            test_id=2002,
                            title="Verify POST users creates new user",
                            refs="REQ-125",
                        ),
                        "custom_steps_separated": [
                            {
                                "content": "Send GET request to /api/v1/users",
                                "expected": "Returns 200 status with user array",
                            },
                            {
                                "content": "Validate response schema",
                                "expected": "Response matches OpenAPI specification",
                            },
                        ],
                    },
                ],
            },
            "testlink_xml_export": {
                "testsuites": [
                    {
                        "testsuite": {
                            "@name": "Login and Authentication",
                            "@package": "com.company.auth",
                            "properties": {
                                "property": [
                                    {"@name": "testlink.version", "@value": "1.9.20"},
                                    {"@name": "export.date", "@value": "2024-01-15"},
                                ]
                            },
                            "testcase": [
                                {
                                    "@name": "TC001 - User Login",
                                    "summary": (
                                        "Verify user can login with valid credentials"
                                    ),
                                    "preconditions": (
                                        "User account exists and is active"
                                    ),
                                    "steps": [
                                        {
                                            "step": {
                                                "number": 1,
                                                "actions": ("Navigate to login page"),
                                                "expectedresults": (
                                                    "Login form is displayed"
                                                ),
                                            }
                                        },
                                        {
                                            "step": {
                                                "number": 2,
                                                "actions": (
                                                    "Enter username and password"
                                                ),
                                                "expectedresults": (
                                                    "User is redirected to dashboard"
                                                ),
                                            }
                                        },
                                    ],
                                }
                            ],
                        }
                    }
                ]
            },
            "generic_unstructured": {
                "tests": [
                    {
                        "id": "test_001",
                        "name": "Basic functionality test",
                        "steps": ["Step 1", "Step 2", "Step 3"],
                        "expected": ["Result 1", "Result 2", "Result 3"],
                        "created_date": "2024-01-15",
                    }
                ]
            },
            "ambiguous_data": {
                "test": {
                    "case": "Something that could be anything",
                    "steps": ["Do something", "Expect something"],
                },
                "execution": "maybe this means something",
                "project": "AMBIG",
            },
            "malformed_data": {
                "testCase": {"incomplete": True},
                "missing_required": None,
                "nested": {
                    "level1": {"level2": {"level3": {"level4": {"level5": "too deep"}}}}
                },
            },
        }

    def test_end_to_end_zephyr_detection(self) -> None:
        """Test complete Zephyr format detection workflow."""
        test_data = self.test_data_samples["zephyr_complete"]

        result = self.detector.detect_format(test_data)

        assert result == SupportedFormat.ZEPHYR

    def test_end_to_end_xray_detection(self) -> None:
        """Test complete Xray format detection workflow."""
        test_data = self.test_data_samples["xray_with_jira"]

        result = self.detector.detect_format(test_data)

        assert result == SupportedFormat.JIRA_XRAY

    def test_end_to_end_testrail_detection(self) -> None:
        """Test complete TestRail format detection workflow."""
        test_data = self.test_data_samples["testrail_api_response"]

        result = self.detector.detect_format(test_data)

        assert result == SupportedFormat.TESTRAIL

    def test_end_to_end_testlink_detection(self) -> None:
        """Test complete TestLink format detection workflow."""
        test_data = self.test_data_samples["testlink_xml_export"]

        result = self.detector.detect_format(test_data)

        assert result == SupportedFormat.TESTLINK

    def test_ambiguous_data_handling(self) -> None:
        """Test handling of ambiguous or unclear data."""
        test_data = self.test_data_samples["ambiguous_data"]

        result = self.detector.detect_format(test_data)

        # Should still return a result but likely UNKNOWN or GENERIC
        assert result in [SupportedFormat.UNKNOWN, SupportedFormat.GENERIC]

    def test_malformed_data_handling(self) -> None:
        """Test handling of malformed or incomplete data."""
        test_data = self.test_data_samples["malformed_data"]

        result = self.detector.detect_format(test_data)

        # Should handle gracefully without crashing
        assert result is not None
        assert result in list(SupportedFormat)

    @patch("importobot.medallion.bronze.format_detector.FormatRegistry")
    def test_registry_integration(self, mock_registry: Any) -> None:
        """Test integration with FormatRegistry."""

        # Create mock format definitions with required methods
        mock_zephyr_format = MagicMock()
        mock_zephyr_format.get_all_fields.return_value = []
        mock_zephyr_format.unique_indicators = []
        mock_zephyr_format.strong_indicators = []
        mock_zephyr_format.moderate_indicators = []
        mock_zephyr_format.weak_indicators = []

        mock_xray_format = MagicMock()
        mock_xray_format.get_all_fields.return_value = []
        mock_xray_format.unique_indicators = []
        mock_xray_format.strong_indicators = []
        mock_xray_format.moderate_indicators = []
        mock_xray_format.weak_indicators = []

        # Mock registry to return specific formats
        mock_registry_instance = mock_registry.return_value
        mock_registry_instance.get_all_formats.return_value = {
            SupportedFormat.ZEPHYR: mock_zephyr_format,
            SupportedFormat.JIRA_XRAY: mock_xray_format,
        }

        # Create detector after the patch is applied
        detector = FormatDetector()

        test_data = self.test_data_samples["zephyr_complete"]
        result = detector.detect_format(test_data)

        # Verify registry was called
        mock_registry_instance.get_all_formats.assert_called()
        # Note: With empty mock formats, detection may fall back to UNKNOWN
        assert result in [SupportedFormat.ZEPHYR, SupportedFormat.UNKNOWN]

    def test_performance_acceptability(self) -> None:
        """Test that detection performance is acceptable for Bronze layer."""

        test_data = self.test_data_samples["zephyr_complete"]

        start_time = time.time()
        result = self.detector.detect_format(test_data)
        end_time = time.time()

        detection_time = end_time - start_time

        # Should complete in under 1 second for Bronze layer
        assert detection_time < 1.0
        assert result is not None


@unittest.skipUnless(FormatDetector is not None, "numpy dependency required")
class TestFormatDetectionBoundaryConditions(unittest.TestCase):
    """Test boundary conditions and stress scenarios for format detection."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.detector = FormatDetector()

    def test_empty_data_handling(self) -> None:
        """Test handling of completely empty data."""
        result = self.detector.detect_format({})

        assert result is not None
        assert result in list(SupportedFormat)

    def test_extremely_large_data_handling(self) -> None:
        """Test handling of extremely large data structures."""
        # Create a large but valid Zephyr-like structure
        large_data = {
            "testCase": {
                "key": "LARGE-001",
                "name": "Large Test Case",
                "steps": [
                    {"stepDescription": f"Step {i}", "expectedResult": f"Result {i}"}
                    for i in range(1000)
                ],
            },
            "execution": {"status": "PASSED"},
        }

        result = self.detector.detect_format(large_data)

        assert result is not None
        assert result in list(SupportedFormat)

    def test_deeply_nested_data_handling(self) -> None:
        """Test handling of deeply nested data structures."""
        deeply_nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
                                "testCase": {
                                    "key": "NESTED-001",
                                    "name": "Nested Test",
                                }
                            }
                        }
                    }
                }
            }
        }

        result = self.detector.detect_format(deeply_nested)

        assert result is not None
        assert result in list(SupportedFormat)

    def test_unicode_and_special_characters(self) -> None:
        """Test handling of Unicode and special characters."""
        unicode_data = {
            "testCase": {
                "key": "UNICODE-001",
                "name": "Test with émojis  and spëcial chars",
                "description": "Test with 中文, العربية, and 日本語",
                "steps": [
                    {
                        "stepDescription": "Step with ümlauts",
                        "expectedResult": "Result with spëcial chars",
                    }
                ],
            }
        }

        result = self.detector.detect_format(unicode_data)

        assert result is not None
        assert result in list(SupportedFormat)
