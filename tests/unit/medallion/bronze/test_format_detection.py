"""TDD tests for format detection across all supported test frameworks.

# Test data contains long strings

These tests define the expected behavior for detecting various test management
formats (Zephyr, TestLink, JIRA/Xray, TestRail) with high accuracy and confidence.

Business Requirements:
- Format detection must achieve >80% confidence for known formats (BR-FORMAT-001)
- Must distinguish between similar formats accurately (BR-FORMAT-002)
- Must handle edge cases and malformed data gracefully (BR-SECURITY-002)
- Must support format evolution and variations

Business References:
- BR-FORMAT-001: Format Detection Accuracy (Business Spec v2.3, Section 4.2)
- BR-FORMAT-002: Format Disambiguation (Business Spec v2.3, Section 4.3)
- BR-FORMAT-003: Generic Format Acceptance (Business Spec v2.3, Section 4.4)
- BR-PERFORMANCE-001: Format Detection Speed (Business Spec v2.3, Section 6.1)
- BR-SECURITY-002: Input Validation Robustness (Business Spec v2.3, Section 7.2)
"""

import time
import unittest
from typing import Any

from importobot.medallion.bronze.format_detector import FormatDetector
from importobot.medallion.interfaces.enums import SupportedFormat
from tests.business_requirements import (
    MAX_CONFIDENCE_CALCULATION_TIME,
    MAX_FORMAT_DETECTION_TIME,
    MIN_FORMAT_CONFIDENCE_HIGH_QUALITY,
    MIN_FORMAT_CONFIDENCE_STANDARD,
    MIN_GENERIC_FORMAT_CONFIDENCE,
)
from tests.shared_test_data_bronze import (
    COMMON_TEST_CASE_STRUCTURE,
    COMMON_TEST_SUITE_STRUCTURE,
)

try:  # pragma: no cover - optional dependency guard
    import numpy  # type: ignore

    _ = numpy  # Mark as used to avoid F401
except ImportError as exc:  # pragma: no cover
    raise unittest.SkipTest(
        "numpy dependency required for format detection tests"
    ) from exc


class TestFormatDetectionBusinessLogic(unittest.TestCase):
    """Business logic tests for format detection capabilities."""

    def setUp(self):
        """Set up test environment with format detector."""
        self.detector = FormatDetector()

        # Real-world format examples based on actual exports
        self.zephyr_examples: list[dict[str, Any]] = [
            # Standard Zephyr export
            {
                "testCase": {
                    "key": "TEST-123",
                    "name": "User Authentication Test",
                    "description": "Verify user can log in with valid credentials",
                    "testCaseKey": "TEST-123",
                    "priority": "High",
                    "component": "Authentication",
                    "steps": [
                        {
                            "stepDescription": "Navigate to login page",
                            "expectedResult": "Login page is displayed",
                            "stepNumber": 1,
                        },
                        {
                            "stepDescription": "Enter valid username and password",
                            "expectedResult": "User is authenticated successfully",
                            "stepNumber": 2,
                        },
                    ],
                },
                "execution": {
                    "status": "PASSED",
                    "executedOn": "2024-01-15T10:30:00Z",
                    "executedBy": "tester@company.com",
                    "executionId": "EXEC-001",
                    "cycleId": "CYCLE-001",
                },
                "cycle": {
                    "name": "Sprint 1 Testing",
                    "cycleId": "CYCLE-001",
                    "startDate": "2024-01-01",
                    "endDate": "2024-01-14",
                    "environment": "Production",
                    "version": "1.0",
                },
                "project": {"key": "PROJ", "name": "Test Project"},
                "version": {"name": "v1.0", "id": "VER-001"},
                "sprint": {"name": "Sprint 1", "state": "Active"},
            },
            # Minimal but complete Zephyr structure
            {
                "testCase": {
                    "name": "Simple Test",
                    "testCaseKey": "TEST-456",
                    "priority": "Medium",
                    "component": "General",
                    "steps": [
                        {
                            "stepDescription": "Basic test step",
                            "expectedResult": "Expected outcome",
                            "stepNumber": 1,
                        }
                    ],
                },
                "execution": {
                    "status": "TODO",
                    "executionId": "EXEC-002",
                    "cycleId": "CYCLE-002",
                    "executedBy": "tester@company.com",
                    "executionDate": "2024-01-01T10:00:00Z",
                },
                "cycle": {
                    "name": "Test Cycle",
                    "cycleId": "CYCLE-002",
                    "environment": "Testing",
                    "startDate": "2024-01-01",
                    "endDate": "2024-01-07",
                    "version": "1.0",
                },
                "project": {"key": "PROJ", "name": "Test Project"},
                "version": {"name": "v1.0", "id": "VER-001"},
                "sprint": {"name": "Sprint 1", "state": "Active"},
            },
            # Complex Zephyr with custom fields
            {
                "project": {"key": "PROJ", "name": "Test Project"},
                "testCase": {
                    "key": "PROJ-456",
                    "name": "API Integration Test",
                    "testCaseKey": "PROJ-456",
                    "priority": "High",
                    "component": "Authentication",
                    "customFields": {"priority": "High", "component": "Authentication"},
                    "steps": [
                        {
                            "stepDescription": "Send API request",
                            "expectedResult": "Response status 200",
                            "stepNumber": 1,
                        }
                    ],
                },
                "execution": {
                    "environment": "staging",
                    "status": "TODO",
                    "executionId": "EXEC-003",
                    "cycleId": "CYCLE-789",
                },
                "cycle": {
                    "key": "CYCLE-789",
                    "name": "API Testing Cycle",
                    "environment": "Staging",
                },
                "version": {"name": "v2.0", "id": "VER-002"},
                "sprint": {"name": "Sprint 2", "state": "Planning"},
            },
        ]

        self.testlink_examples: list[dict[str, Any]] = [
            # Standard TestLink XML-to-JSON structure
            {
                "testsuites": {
                    "testsuite": {
                        "name": "Login Test Suite",
                        "details": "Tests for user authentication functionality",
                        "testsuiteid": "1",
                        "testcase": [
                            {
                                "name": "Valid Login Test",
                                "summary": "Test valid user login",
                                **COMMON_TEST_CASE_STRUCTURE,
                            }
                        ],
                        **COMMON_TEST_SUITE_STRUCTURE,
                    },
                    "project": {"name": "Authentication Project", "prefix": "AUTH"},
                    "testplan": {"name": "Login Test Plan", "testplan_id": "PLAN-001"},
                    "time": "90",
                    "tests": "1",
                }
            },
            # Multiple test suites
            {
                "testsuites": [
                    {
                        "testsuite": {
                            "name": "Smoke Tests",
                            "testcase": [{"name": "Basic Test"}],
                        }
                    },
                    {
                        "testsuite": {
                            "name": "Regression Tests",
                            "testcase": [{"name": "Advanced Test"}],
                        }
                    },
                ]
            },
            # TestLink with execution results
            {
                "testsuites": {
                    "testsuite": {
                        "name": "Execution Results",
                        "tests": "5",
                        "failures": "1",
                        "time": "120.5",
                        "testsuiteid": "2",
                        "testcase": [
                            {
                                "name": "Test 1",
                                "status": "passed",
                                "time": "30.2",
                                "testcaseid": "2",
                                "priority": "Medium",
                                "execution_type": "Automated",
                            }
                        ],
                        "total_time": "120.5",
                        "total_tests": "1",
                    },
                    "project": {"name": "Execution Project", "prefix": "EXEC"},
                    "time": "120.5",
                    "tests": "1",
                }
            },
        ]

        self.jira_xray_examples: list[dict[str, Any]] = [
            # Standard JIRA REST API response with Xray-specific fields
            {
                "expand": "renderedFields,names,schema,operations",
                "issues": [
                    {
                        "key": "XRT-123",
                        "fields": {
                            "summary": "API Authentication Test",
                            "description": "Verify API token authentication",
                            "issuetype": {
                                "name": "Test",
                                "iconUrl": "https://jira.company.com/secure/viewavatar",
                            },
                            "customfield_10001": {"value": "Manual"},
                            "labels": ["api", "authentication", "regression"],
                        },
                    }
                ],
                "testExecutions": [
                    {
                        "executionId": "EXEC-001",
                        "testKey": "XRT-123",
                        "status": "PASS",
                        "executedBy": "tester@company.com",
                        "executionDate": "2024-01-15T10:30:00Z",
                    }
                ],
                "testInfo": {
                    "testKey": "XRT-123",
                    "testType": "Generic",
                    "requirements": ["REQ-001"],
                    "labels": ["api", "authentication", "regression"],
                },
                "evidences": [
                    {
                        "evidenceId": "EV-001",
                        "filename": "screenshot.png",
                        "contentType": "image/png",
                    }
                ],
                "maxResults": 50,
                "total": 1,
            },
            # Xray test execution
            {
                "issues": [
                    {
                        "key": "EXEC-456",
                        "fields": {
                            "summary": "Test Execution for Sprint 1",
                            "issuetype": {"name": "Test Execution"},
                            "customfield_xray_tests": [
                                {"key": "XRT-123", "status": "PASS"},
                                {"key": "XRT-124", "status": "FAIL"},
                            ],
                        },
                    }
                ],
                "testExecutions": [
                    {
                        "executionId": "EXEC-456",
                        "testKey": "XRT-123",
                        "status": "PASS",
                        "executedBy": "tester@company.com",
                    },
                    {
                        "executionId": "EXEC-457",
                        "testKey": "XRT-124",
                        "status": "FAIL",
                        "executedBy": "tester@company.com",
                    },
                ],
                "testInfo": {
                    "testKey": "EXEC-456",
                    "testType": "Test Execution",
                    "requirements": ["REQ-002"],
                },
            },
            # Xray test set
            {
                "issues": [
                    {
                        "key": "XTS-789",
                        "fields": {
                            "summary": "Login Test Set",
                            "issuetype": {"name": "Test Set"},
                            "XrayTestSet": {"tests": ["XRT-123", "XRT-124", "XRT-125"]},
                        },
                    }
                ],
                "testExecutions": [
                    {
                        "executionId": "EXEC-789",
                        "testKey": "XTS-789",
                        "status": "TODO",
                        "executedBy": "tester@company.com",
                    }
                ],
                "testInfo": {
                    "testKey": "XTS-789",
                    "testType": "Test Set",
                    "requirements": ["REQ-003"],
                    "component": "Authentication",
                },
                "evidences": [
                    {
                        "evidenceId": "EV-789",
                        "filename": "testset_evidence.png",
                        "contentType": "image/png",
                    }
                ],
            },
        ]

        self.testrail_examples: list[dict[str, Any]] = [
            # TestRail API response structure
            {
                "runs": [
                    {
                        "id": 123,
                        "suite_id": 456,
                        "name": "API Test Run",
                        "description": "Testing API endpoints",
                        "milestone_id": 789,
                        "assignedto_id": 1,
                        "include_all": True,
                        "is_completed": False,
                        "created_on": 1640995200,
                        "created_by": 1,
                        "url": "https://testrail.company.com/index.php?/runs/view/123",
                    }
                ],
                "tests": [
                    {
                        "id": 1001,
                        "case_id": 2001,
                        "status_id": 1,
                        "title": "Test API Authentication",
                        "run_id": 123,
                        "type_id": 3,
                        "priority_id": 2,
                        "milestone_id": 789,
                        "assignedto_id": 1,
                        "estimate": "30m",
                        "estimate_forecast": None,
                        "refs": "REQ-123, REQ-124",
                    }
                ],
                "cases": [
                    {
                        "id": 2001,
                        "title": "Test API Authentication",
                        "section_id": 101,
                        "template_id": 1,
                        "type_id": 3,
                        "priority_id": 2,
                        "milestone_id": 789,
                        "refs": "REQ-123, REQ-124",
                        "created_by": 1,
                        "created_on": 1640995200,
                        "updated_by": 1,
                        "updated_on": 1640995200,
                        "suite_id": 456,
                    }
                ],
                "results": [
                    {
                        "id": 3001,
                        "test_id": 1001,
                        "status_id": 1,
                        "comment": "Test passed successfully",
                        "created_on": 1640995200,
                        "assignedto_id": 1,
                        "defects": None,
                        "version": "1.0",
                    }
                ],
                "project_id": 1,
                "suite_id": 456,
            },
            # Enhanced TestRail test cases with required indicators
            {
                "runs": [
                    {
                        "id": 124,
                        "suite_id": 456,
                        "name": "Login Test Run",
                        "is_completed": False,
                        "created_on": 1640995200,
                        "created_by": 1,
                    }
                ],
                "cases": [
                    {
                        "id": 2001,
                        "case_id": 2001,
                        "title": "Verify User Login",
                        "section_id": 101,
                        "template_id": 1,
                        "type_id": 3,
                        "priority_id": 2,
                        "milestone_id": 789,
                        "refs": "REQ-123",
                        "custom_steps_separated": [
                            {
                                "content": "Navigate to login page",
                                "expected": "Login form is displayed",
                            }
                        ],
                    }
                ],
                "tests": [
                    {
                        "id": 1002,
                        "case_id": 2001,
                        "status_id": 1,
                        "title": "Verify User Login",
                        "run_id": 124,
                        "type_id": 3,
                        "priority_id": 2,
                        "assignedto_id": 1,
                        "estimate": "15m",
                    }
                ],
                "results": [
                    {
                        "id": 3002,
                        "test_id": 1002,
                        "status_id": 1,
                        "comment": "Login test passed successfully",
                        "created_on": 1640995200,
                        "assignedto_id": 1,
                        "version": "1.0",
                    }
                ],
                "suite_id": 456,
                "project_id": 1,
            },
            # Enhanced TestRail results with required indicators
            {
                "runs": [
                    {
                        "id": 125,
                        "suite_id": 457,
                        "name": "Results Test Run",
                        "is_completed": True,
                        "created_on": 1640995200,
                    }
                ],
                "cases": [
                    {
                        "id": 2002,
                        "case_id": 2002,
                        "title": "API Response Test",
                        "section_id": 102,
                        "type_id": 3,
                        "priority_id": 2,
                        "refs": "REQ-456",
                    }
                ],
                "tests": [
                    {
                        "id": 1003,
                        "case_id": 2002,
                        "status_id": 5,
                        "title": "API Response Test",
                        "run_id": 125,
                        "type_id": 3,
                    }
                ],
                "results": [
                    {
                        "id": 3003,
                        "test_id": 1003,
                        "status_id": 5,
                        "comment": "API response test failed",
                        "created_on": 1640995200,
                        "assignedto_id": 1,
                        "defects": "BUG-789",
                        "version": "1.1",
                    }
                ],
                "suite_id": 457,
                "project_id": 2,
            },
        ]

        self.generic_examples: list[dict[str, Any]] = [
            # Generic test structure
            {
                "tests": [
                    {
                        "name": "Basic Test",
                        "description": "A simple test case",
                        "steps": [
                            {"action": "Do something", "expected": "Something happens"}
                        ],
                    }
                ]
            },
            # Alternative generic structure
            {
                "test_cases": [
                    {
                        "id": "TC001",
                        "title": "Test Case 1",
                        "procedure": "Test procedure",
                        "expected_result": "Expected outcome",
                    }
                ]
            },
            # Simple testcases structure
            {
                "testcases": {
                    "suite": "Basic Tests",
                    "cases": [{"name": "Test 1", "steps": ["Step 1", "Step 2"]}],
                }
            },
        ]

        self.ambiguous_examples: list[dict[str, Any]] = [
            # Could be multiple formats
            {"test": "ambiguous", "case": "example", "data": "unclear format"},
            # Empty but valid
            {},
            # Non-test data
            {
                "user": {"name": "John", "email": "john@test.com"},
                "settings": {"theme": "dark", "language": "en"},
            },
        ]

    # Test 1: Zephyr format detection accuracy
    def test_zephyr_format_detection_high_confidence(self):
        """Test that Zephyr formats are detected with high confidence."""
        for i, example in enumerate(self.zephyr_examples):
            with self.subTest(example_index=i):
                detected_format = self.detector.detect_format(example)
                confidence = self.detector.get_format_confidence(
                    example, SupportedFormat.ZEPHYR
                )

                self.assertEqual(
                    detected_format,
                    SupportedFormat.ZEPHYR,
                    f"Failed to detect Zephyr format in example {i}",
                )
                self.assertGreaterEqual(
                    confidence,
                    MIN_FORMAT_CONFIDENCE_STANDARD,
                    f"Low confidence ({confidence}) for Zephyr example {i}",
                )

    def test_zephyr_key_indicators_recognition(self):
        """Test recognition of key Zephyr indicators."""
        # Test with minimal Zephyr structure
        minimal_zephyr = {"testCase": {"key": "TEST-1"}, "execution": {}}
        detected = self.detector.detect_format(minimal_zephyr)
        self.assertEqual(detected, SupportedFormat.ZEPHYR)

        # Test with cycle information
        cycle_zephyr = {"cycle": {"name": "Sprint 1"}, "testCase": {}}
        detected = self.detector.detect_format(cycle_zephyr)
        self.assertEqual(detected, SupportedFormat.ZEPHYR)

    # Test 2: TestLink format detection accuracy
    def test_testlink_format_detection_high_confidence(self):
        """Test that TestLink formats are detected with high confidence."""
        for i, example in enumerate(self.testlink_examples):
            with self.subTest(example_index=i):
                detected_format = self.detector.detect_format(example)
                confidence = self.detector.get_format_confidence(
                    example, SupportedFormat.TESTLINK
                )

                self.assertEqual(
                    detected_format,
                    SupportedFormat.TESTLINK,
                    f"Failed to detect TestLink format in example {i}",
                )
                self.assertGreaterEqual(
                    confidence,
                    MIN_FORMAT_CONFIDENCE_STANDARD,
                    f"Low confidence ({confidence}) for TestLink example {i}",
                )

    def test_testlink_variations_detection(self):
        """Test detection of various TestLink structural variations."""
        # Single testsuite
        single_suite = {"testsuite": {"name": "Test", "testcase": []}}
        self.assertEqual(
            self.detector.detect_format(single_suite), SupportedFormat.TESTLINK
        )

        # Multiple testsuites
        multi_suites = {"testsuites": [{"testsuite": {"name": "Test"}}]}
        self.assertEqual(
            self.detector.detect_format(multi_suites), SupportedFormat.TESTLINK
        )

        # JUnit-style structure (should still be TestLink)
        junit_style = {"testsuite": {"tests": "10", "failures": "1", "testcase": []}}
        self.assertEqual(
            self.detector.detect_format(junit_style), SupportedFormat.TESTLINK
        )

    # Test 3: JIRA/Xray format detection accuracy
    def test_jira_xray_format_detection_high_confidence(self):
        """Test that JIRA/Xray formats are detected with high confidence."""
        for i, example in enumerate(self.jira_xray_examples):
            with self.subTest(example_index=i):
                detected_format = self.detector.detect_format(example)
                confidence = self.detector.get_format_confidence(
                    example, SupportedFormat.JIRA_XRAY
                )

                self.assertEqual(
                    detected_format,
                    SupportedFormat.JIRA_XRAY,
                    f"Failed to detect JIRA/Xray format in example {i}",
                )
                self.assertGreaterEqual(
                    confidence,
                    MIN_FORMAT_CONFIDENCE_STANDARD,
                    f"Low confidence ({confidence}) for JIRA/Xray example {i}",
                )

    def test_jira_key_pattern_recognition(self):
        """Test recognition of JIRA issue key patterns.

        Note: With proper Bayesian inference, JIRA_XRAY's high prior (0.30) means
        that structural evidence (issues, fields) still produces high confidence
        even with invalid key patterns. This is mathematically correct.
        """
        # Standard JIRA key pattern
        jira_with_key = {
            "issues": [{"key": "PROJ-123", "fields": {"issuetype": {"name": "Test"}}}]
        }
        detected = self.detector.detect_format(jira_with_key)
        self.assertEqual(detected, SupportedFormat.JIRA_XRAY)

        # Valid key pattern should produce very high confidence
        valid_confidence = self.detector.get_format_confidence(
            jira_with_key, SupportedFormat.JIRA_XRAY
        )

        # Invalid key pattern should have lower confidence than valid
        invalid_key = {"issues": [{"key": "invalid-key", "fields": {}}]}
        invalid_confidence = self.detector.get_format_confidence(
            invalid_key, SupportedFormat.JIRA_XRAY
        )
        self.assertLess(invalid_confidence, valid_confidence)

    # Test 4: TestRail format detection accuracy
    def test_testrail_format_detection_high_confidence(self):
        """Test that TestRail formats are detected with high confidence."""
        for i, example in enumerate(self.testrail_examples):
            with self.subTest(example_index=i):
                detected_format = self.detector.detect_format(example)
                confidence = self.detector.get_format_confidence(
                    example, SupportedFormat.TESTRAIL
                )

                self.assertEqual(
                    detected_format,
                    SupportedFormat.TESTRAIL,
                    f"Failed to detect TestRail format in example {i}",
                )
                # Remove debug prints for cleaner output
                self.assertGreaterEqual(
                    confidence,
                    MIN_FORMAT_CONFIDENCE_STANDARD,
                    f"Low confidence ({confidence}) for TestRail example {i}",
                )

    def test_testrail_api_structure_recognition(self):
        """Test recognition of TestRail API response structures."""
        # Test with suite_id and project_id indicators
        testrail_cases = {
            "cases": [{"id": 1, "title": "Test"}],
            "suite_id": 123,
            "project_id": 456,
        }
        detected = self.detector.detect_format(testrail_cases)
        self.assertEqual(detected, SupportedFormat.TESTRAIL)

        # Test with run structure
        testrail_runs = {
            "runs": [{"id": 1, "suite_id": 123}],
            "milestone_id": 789,
        }
        detected = self.detector.detect_format(testrail_runs)
        self.assertEqual(detected, SupportedFormat.TESTRAIL)

    # Test 5: Generic format detection
    def test_generic_format_detection_fallback(self):
        """Test that generic test structures are properly detected.

        Note: Generic format has low prior (0.04) by design, reflecting its rarity.
        With proper Bayesian inference, even good evidence produces moderate confidence.
        This is mathematically correct - low priors require
        strong evidence for high confidence.
        """
        for i, example in enumerate(self.generic_examples):
            with self.subTest(example_index=i):
                detected_format = self.detector.detect_format(example)
                confidence = self.detector.get_format_confidence(
                    example, SupportedFormat.GENERIC
                )

                self.assertEqual(
                    detected_format,
                    SupportedFormat.GENERIC,
                    f"Failed to detect generic format in example {i}",
                )
                self.assertGreaterEqual(
                    confidence,
                    MIN_GENERIC_FORMAT_CONFIDENCE,
                    f"Low confidence ({confidence}) for generic example {i}",
                )

    # Test 6: Format disambiguation
    def test_format_disambiguation_accuracy(self):
        """Test that similar formats are correctly distinguished."""
        # Zephyr vs JIRA/Xray disambiguation
        zephyr_data = {"testCase": {"key": "TEST-1"}, "execution": {}}
        jira_data = {
            "issues": [{"key": "TEST-1", "fields": {"issuetype": {"name": "Test"}}}]
        }

        self.assertEqual(
            self.detector.detect_format(zephyr_data), SupportedFormat.ZEPHYR
        )
        self.assertEqual(
            self.detector.detect_format(jira_data), SupportedFormat.JIRA_XRAY
        )

        # TestLink vs Generic disambiguation
        testlink_data = {"testsuite": {"testcase": [{"name": "Test"}]}}
        generic_data = {"tests": [{"name": "Test"}]}

        self.assertEqual(
            self.detector.detect_format(testlink_data), SupportedFormat.TESTLINK
        )
        self.assertEqual(
            self.detector.detect_format(generic_data), SupportedFormat.GENERIC
        )

    def test_confidence_relative_scoring(self):
        """Test that confidence scores correctly rank format likelihood."""
        # Create data that could match multiple formats
        ambiguous_data = {
            "test": {"name": "Test Case", "steps": []},
            "case": {"id": "TC-1"},
            "execution": {"status": "pending"},
        }

        # Get confidence for all formats
        confidences = {}
        for format_type in [
            SupportedFormat.ZEPHYR,
            SupportedFormat.TESTLINK,
            SupportedFormat.JIRA_XRAY,
            SupportedFormat.TESTRAIL,
            SupportedFormat.GENERIC,
        ]:
            confidences[format_type] = self.detector.get_format_confidence(
                ambiguous_data, format_type
            )

        # The detected format should be one of the reasonable candidates
        # Note: detect_format() uses weighted scoring, not just individual confidence
        detected = self.detector.detect_format(ambiguous_data)
        max_confidence_format = max(confidences, key=lambda x: confidences[x])

        # Allow for UNKNOWN if no format reaches threshold
        if detected != SupportedFormat.UNKNOWN:
            # The detected format should have non-zero confidence
            self.assertGreater(confidences[detected], 0.0)
            # And it should be a reasonable choice
            # (not necessarily the max individual confidence)
            self.assertIn(
                detected,
                [
                    SupportedFormat.ZEPHYR,
                    SupportedFormat.TESTRAIL,
                    SupportedFormat.GENERIC,
                    max_confidence_format,
                ],
            )

    # Test 7: Edge cases and error handling
    def test_unknown_format_handling(self):
        """Test proper handling of unrecognizable formats."""
        for example in self.ambiguous_examples:
            detected_format = self.detector.detect_format(example)

            # Should either detect a valid format or return UNKNOWN
            self.assertIn(detected_format, list(SupportedFormat))

            # Confidence for wrong format should be low
            if detected_format != SupportedFormat.UNKNOWN:
                wrong_formats = [
                    f
                    for f in SupportedFormat
                    if f not in (detected_format, SupportedFormat.UNKNOWN)
                ]
                for wrong_format in wrong_formats[:2]:  # Test a few wrong formats
                    confidence = self.detector.get_format_confidence(
                        example, wrong_format
                    )
                    error_msg = (
                        f"Too high confidence ({confidence}) for "
                        f"wrong format {wrong_format}"
                    )
                    self.assertLess(
                        confidence, MIN_FORMAT_CONFIDENCE_STANDARD, error_msg
                    )

    def test_malformed_data_resilience(self):
        """Test resilience against malformed or unexpected data."""
        malformed_examples: list[Any] = [
            None,
            [],
            "string instead of dict",
            {
                "deeply": {
                    "nested": {
                        "structure": {"that": {"goes": {"very": {"deep": "value"}}}}
                    }
                }
            },
            {str(i): f"value_{i}" for i in range(1000)},  # Very large dict
        ]

        for example in malformed_examples:
            try:
                detected = self.detector.detect_format(example)
                # Should handle gracefully, return UNKNOWN for non-dict types
                if not isinstance(example, dict):
                    self.assertEqual(detected, SupportedFormat.UNKNOWN)
            except Exception as e:
                error_msg = (
                    f"Format detection crashed on malformed data {type(example)}: {e}"
                )
                self.fail(error_msg)

    def test_empty_data_handling(self):
        """Test handling of empty data structures."""
        empty_examples: list[dict[str, Any]] = [
            {},
            {"": ""},
            {"null": None},
            {"empty_list": []},
            {"empty_dict": {}},
        ]

        for example in empty_examples:
            detected = self.detector.detect_format(example)
            # Should not crash and should return a valid format type
            self.assertIn(detected, list(SupportedFormat))

    # Test 8: Performance requirements
    def test_format_detection_performance(self):
        """Test that format detection performs reasonably on large data."""
        # Create large test dataset
        large_data = {
            "testCase": {
                "name": "Large Test",
                "steps": [
                    {"stepDescription": f"Step {i}", "expectedResult": f"Result {i}"}
                    for i in range(1000)
                ],
            },
            "execution": {"status": "TODO"},
            "cycle": {"name": "Performance Test"},
        }

        # Measure detection time
        start_time = time.time()
        detected = self.detector.detect_format(large_data)
        detection_time = time.time() - start_time

        # Should detect correctly and quickly
        self.assertEqual(detected, SupportedFormat.ZEPHYR)
        self.assertLess(
            detection_time, MAX_FORMAT_DETECTION_TIME, "Format detection took too long"
        )

    def test_confidence_calculation_performance(self):
        """Test that confidence calculation performs well."""
        data = self.zephyr_examples[0]

        start_time = time.time()
        confidence = 0.0
        for _ in range(100):  # Multiple calculations
            confidence = self.detector.get_format_confidence(
                data, SupportedFormat.ZEPHYR
            )
        calculation_time = time.time() - start_time

        self.assertLess(
            calculation_time,
            MAX_CONFIDENCE_CALCULATION_TIME,
            "Confidence calculation too slow",
        )
        self.assertGreaterEqual(confidence, MIN_FORMAT_CONFIDENCE_HIGH_QUALITY)

    # Test 9: Extensibility and configuration
    def test_supported_formats_enumeration(self):
        """Test that all supported formats can be enumerated."""
        supported_formats = self.detector.get_supported_formats()

        expected_formats = [
            SupportedFormat.ZEPHYR,
            SupportedFormat.TESTLINK,
            SupportedFormat.JIRA_XRAY,
            SupportedFormat.TESTRAIL,
            SupportedFormat.GENERIC,
        ]

        for expected_format in expected_formats:
            self.assertIn(expected_format, supported_formats)

    def test_format_patterns_completeness(self):
        """Test that format patterns cover all expected scenarios."""
        # Each format should have comprehensive pattern coverage
        for format_type in [
            SupportedFormat.ZEPHYR,
            SupportedFormat.TESTLINK,
            SupportedFormat.JIRA_XRAY,
            SupportedFormat.TESTRAIL,
        ]:
            # Test that the format has reasonable pattern coverage
            test_data = getattr(self, f"{format_type.value}_examples")[0]
            confidence = self.detector.get_format_confidence(test_data, format_type)

            self.assertGreaterEqual(
                confidence,
                MIN_FORMAT_CONFIDENCE_STANDARD,
                f"Format {format_type} should have high confidence on its own examples",
            )

    # Test 10: Real-world validation
    def test_real_world_format_variations(self):
        """Test detection on real-world format variations."""
        # Test with mixed case and extra fields
        real_world_zephyr = {
            "TestCase": {  # Different casing
                "Key": "PROJ-123",
                "Name": "Real World Test",
                "customField1": "extra data",
                "customField2": {"nested": "value"},
            },
            "Execution": {"Status": "PASS"},
            "Cycle": {"name": "Real World Cycle"},  # Add missing required field
            "additionalMetadata": {"source": "automated_export"},
        }

        detected = self.detector.detect_format(real_world_zephyr)
        self.assertEqual(detected, SupportedFormat.ZEPHYR)

        # Test with legacy TestLink structure
        legacy_testlink = {
            "testsuite": {
                "@name": "Legacy Suite",  # XML attribute style
                "testcase": {
                    "@name": "Legacy Test",
                    "step": [  # Different from expected 'steps'
                        {"action": "Do something", "result": "Something happens"}
                    ],
                },
            }
        }

        detected = self.detector.detect_format(legacy_testlink)
        self.assertEqual(detected, SupportedFormat.TESTLINK)


if __name__ == "__main__":
    unittest.main()
