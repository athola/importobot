"""Shared test data for bronze medallion tests to eliminate duplication."""

from typing import Any, Dict

# Common test case structure used across bronze layer tests
COMMON_TEST_CASE_STRUCTURE: Dict[str, Any] = {
    "testcaseid": "1",
    "priority": "High",
    "execution_type": "Manual",
    "preconditions": "User exists in system",
    "steps": {
        "step": [
            {
                "step_number": "1",
                "actions": "Open browser and navigate to login page",
                "expectedresults": "Login page is displayed correctly",
                "execution_type": "Manual",
            },
            {
                "step_number": "2",
                "actions": "Enter valid credentials",
                "expectedresults": "User logged in successfully",
                "execution_type": "Manual",
            },
        ]
    },
    "custom_fields": {
        "automation_status": "Automated",
        "test_type": "Functional",
    },
    "time": "30",
    "tests": "2",
}

# Common test suite structure for bronze layer tests
COMMON_TEST_SUITE_STRUCTURE: Dict[str, Any] = {
    "testsuite": [COMMON_TEST_CASE_STRUCTURE],
    "time": "60",
    "tests": "1",
}
