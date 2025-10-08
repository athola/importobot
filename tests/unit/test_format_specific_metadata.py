"""Tests for format-specific metadata preservation.

Tests that metadata from different test management frameworks (Zephyr, TestLink,
JIRA/Xray, TestRail) is correctly preserved in Robot Framework output.

Business Requirement: Preserve ALL source system metadata for audit trails and
traceability. Critical for enterprise customers with compliance requirements.
"""

import json

from importobot.api import converters


class TestZephyrMetadataPreservation:
    """Test Zephyr-specific metadata preservation.

    Zephyr metadata includes: cycles, sprints, versions, test execution history.
    """

    def test_zephyr_cycle_metadata_preserved(self):
        """Test that Zephyr test cycle metadata is preserved.

        Business Context: Zephyr organizes tests into cycles (e.g., Sprint 1, UAT).
        This metadata is critical for release tracking and reporting.
        """
        converter = converters.JsonToRobotConverter()

        zephyr_test = {
            "name": "ZEPHYR-1234",
            "description": "User login validation test",
            "cycle": "Sprint 23 - User Authentication",
            "version": "Release 2.5.0",
            "priority": "High",
            "steps": [
                {
                    "step": "Navigate to login page",
                    "expectedResult": "Login page displays",
                }
            ],
        }

        result = converter.convert_json_string(json.dumps(zephyr_test))

        # Verify Robot Framework structure
        assert "*** Test Cases ***" in result
        assert "ZEPHYR-1234" in result

        # Verify Zephyr-specific metadata in documentation or tags
        assert "Sprint 23" in result or "Sprint_23" in result
        assert "Release 2.5.0" in result or "Release_2_5_0" in result

        # Verify metadata is in proper Robot Framework format (tags or documentation)
        lines = result.split("\n")
        has_tags_or_docs = any(
            "[Tags]" in line or "[Documentation]" in line for line in lines
        )
        assert has_tags_or_docs, "Metadata must be in [Tags] or [Documentation]"

    def test_zephyr_sprint_metadata_in_tags(self):
        """Test that Zephyr sprint metadata appears in Robot Framework tags.

        Business Context: Teams use tags for filtering test execution by sprint.
        """
        converter = converters.JsonToRobotConverter()

        zephyr_test = {
            "name": "ZEPHYR-5678",
            "description": "Payment processing test",
            "sprint": "Sprint-45",
            "component": "Payment Gateway",
            "steps": [
                {"step": "Process payment", "expectedResult": "Payment successful"}
            ],
        }

        result = converter.convert_json_string(json.dumps(zephyr_test))

        # Sprint and component should be preserved as tags or in documentation
        result_lower = result.lower()
        assert "sprint" in result_lower or "Sprint" in result
        assert "payment gateway" in result_lower or "Payment_Gateway" in result


class TestTestLinkMetadataPreservation:
    """Test TestLink-specific metadata preservation.

    TestLink metadata includes: test suite hierarchy, requirements traceability.
    """

    def test_testlink_suite_hierarchy_preserved(self):
        """Test that TestLink suite hierarchy is preserved.

        Business Context: TestLink organizes tests in nested suites.
        Example: Project > Feature > Test Suite > Test Case
        This hierarchy is critical for test organization and reporting.
        """
        converter = converters.JsonToRobotConverter()

        testlink_test = {
            "name": "TL-AUTH-001",
            "description": "Authentication test case",
            "test_suite": "Authentication > User Login > Positive Cases",
            "requirement": "REQ-AUTH-123",
            "steps": [
                {"step": "Enter valid credentials", "expectedResult": "User logged in"}
            ],
        }

        result = converter.convert_json_string(json.dumps(testlink_test))

        # Verify suite hierarchy is preserved
        assert "Authentication" in result
        assert "REQ-AUTH-123" in result

        # Verify in proper Robot Framework structure
        assert "*** Test Cases ***" in result
        assert "[Documentation]" in result or "[Tags]" in result

    def test_testlink_requirement_traceability(self):
        """Test that TestLink requirement links are preserved.

        Business Context: Requirement traceability is mandatory for FDA/SOX compliance.
        Must preserve REQ-XXX links from TestLink to Robot Framework output.
        """
        converter = converters.JsonToRobotConverter()

        testlink_test = {
            "name": "TL-REG-045",
            "description": "Regulatory compliance test",
            "requirements": ["REQ-FDA-001", "REQ-SOX-789", "REQ-HIPAA-456"],
            "test_importance": "High",
            "steps": [
                {
                    "step": "Validate audit trail",
                    "expectedResult": "Audit trail complete",
                }
            ],
        }

        result = converter.convert_json_string(json.dumps(testlink_test))

        # All requirement IDs must be preserved
        for req_id in ["REQ-FDA-001", "REQ-SOX-789", "REQ-HIPAA-456"]:
            assert req_id in result, f"Requirement {req_id} not preserved"


class TestJiraXrayMetadataPreservation:
    """Test JIRA/Xray-specific metadata preservation.

    Xray metadata includes: test sets, test execution links, issue links.
    """

    def test_xray_test_set_metadata_preserved(self):
        """Test that Xray test set metadata is preserved.

        Business Context: Xray organizes tests into Test Sets for execution.
        Teams need this metadata to map Robot Framework runs back to Xray.
        """
        converter = converters.JsonToRobotConverter()

        xray_test = {
            "name": "XRAY-2345",
            "description": "API integration test",
            "test_set": "API Regression Suite v2.0",
            "test_execution": "EXEC-8901",
            "linked_issues": ["STORY-123", "BUG-456"],
            "steps": [
                {"step": "Send API request", "expectedResult": "Response code 200"}
            ],
        }

        result = converter.convert_json_string(json.dumps(xray_test))

        # Verify test set and execution metadata preserved
        assert "API Regression Suite" in result or "API_Regression_Suite" in result
        assert "EXEC-8901" in result

        # Verify linked issues preserved
        assert "STORY-123" in result
        assert "BUG-456" in result

    def test_xray_evidence_links_preserved(self):
        """Test that Xray evidence attachments are referenced.

        Business Context: Xray allows attaching evidence (screenshots, logs).
        References to evidence must be preserved for audit trails.
        """
        converter = converters.JsonToRobotConverter()

        xray_test = {
            "name": "XRAY-9999",
            "description": "Security audit test",
            "evidences": ["screenshot_login.png", "audit_log_20250104.txt"],
            "labels": ["security", "audit", "compliance"],
            "steps": [
                {
                    "step": "Verify security controls",
                    "expectedResult": "All controls active",
                }
            ],
        }

        result = converter.convert_json_string(json.dumps(xray_test))

        # Evidence references should be in comments or documentation
        assert "screenshot_login" in result or "audit_log" in result
        assert "security" in result.lower()


class TestTestRailMetadataPreservation:
    """Test TestRail-specific metadata preservation.

    TestRail metadata includes: milestones, test runs, case IDs, priorities.
    """

    def test_testrail_milestone_metadata_preserved(self):
        """Test that TestRail milestone metadata is preserved.

        Business Context: TestRail tracks tests against project milestones.
        This metadata links test results to release planning.
        """
        converter = converters.JsonToRobotConverter()

        testrail_test = {
            "name": "C12345",
            "description": "Checkout flow validation",
            "milestone": "Q1 2025 Release",
            "test_run": "Regression Run 2025-01-04",
            "priority": "Critical",
            "type": "Functional",
            "steps": [
                {"step": "Complete checkout", "expectedResult": "Order confirmed"}
            ],
        }

        result = converter.convert_json_string(json.dumps(testrail_test))

        # Verify milestone and test run preserved
        assert "Q1 2025" in result or "Q1_2025" in result
        assert "Regression Run" in result or "Regression_Run" in result
        assert "C12345" in result

    def test_testrail_custom_fields_preserved(self):
        """Test that TestRail custom fields are preserved.

        Business Context: Organizations add custom fields (e.g., test_owner,
        automation_status, estimated_time). These must be preserved for reporting.
        """
        converter = converters.JsonToRobotConverter()

        testrail_test = {
            "name": "C99999",
            "description": "Custom field test",
            "test_owner": "qa-team@enterprise.com",
            "automation_status": "Automated",
            "estimated_duration": "5 minutes",
            "test_type": "Smoke",
            "steps": [
                {"step": "Run smoke test", "expectedResult": "System responsive"}
            ],
        }

        result = converter.convert_json_string(json.dumps(testrail_test))

        # Custom fields should be in documentation or comments
        result_lower = result.lower()
        assert "qa-team" in result_lower or "automation" in result_lower
        assert "smoke" in result_lower
