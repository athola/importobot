"""Integration tests for Robot Framework execution and conversion logic."""

import json

from importobot.core.converter import convert_file
from tests.test_helpers import (  # type: ignore[import-untyped]
    assert_robot_content_equivalent,
    assert_robot_framework_syntax_valid,
)


def test_zephyr_to_robot_conversion_content_logic_only(tmp_path):
    """
    Ensures that a .robot file generated from a specific Zephyr JSON
    matches the expected Robot Framework content (test case logic only).
    """
    zephyr_json_content = {
        "name": "Retrieve File From Remote Host",
        "objective": "To retrieve a file from a remote host using SSH.",
        "precondition": (
            "SSH connection details (host, username, password) are available."
        ),
        "labels": ["ssh", "file_transfer"],
        "priority": "Medium",
        "status": "Draft",
        "steps": [
            {
                "description": "Open an SSH connection and log in to the remote host.",
                "testData": (
                    "Remote Host: ${REMOTE_HOST}, Username: ${USERNAME}, "
                    "Password: ${PASSWORD}"
                ),
                "expectedResult": (
                    "Successfully connected and logged in to the remote host."
                ),
            },
            {
                "description": "Retrieve the specified file from the remote host.",
                "testData": (
                    "Remote File Path: ${REMOTE_FILE_PATH}, "
                    "Local Destination Path: ${LOCAL_DEST_PATH}"
                ),
                "expectedResult": (
                    "File successfully downloaded to the local destination."
                ),
            },
            {
                "description": "Close the SSH connection.",
                "testData": "N/A",
                "expectedResult": "SSH connection closed.",
            },
        ],
    }

    # This is what parser.py currently generates for the test case logic
    # Note: SSHLibrary is NOT included due to "Retrieve File From Remote Host" exclusion
    expected_robot_content = """*** Settings ***
Documentation    To retrieve a file from a remote host using SSH.
Force Tags    ssh    file_transfer    Medium
Library    OperatingSystem
Library    SSHLibrary
*** Test Cases ***
Retrieve File From Remote Host
[Documentation]    To retrieve a file from a remote host using SSH.
# Step: Open an SSH connection and log in to the remote host.
# Test Data: Remote Host: ${REMOTE_HOST}, Username: ${USERNAME},
# Test Data (cont.): Password: ${PASSWORD}
# ⚠️  Security Warning: Hardcoded password detected in test data
# Expected Result: Successfully connected and logged in to the remote host.
Open Connection    ${REMOTE_HOST}    ${USERNAME}    ${PASSWORD}
# Step: Retrieve the specified file from the remote host.
# Test Data: Remote File Path: ${REMOTE_FILE_PATH},
# Test Data (cont.): Local Destination Path: ${LOCAL_DEST_PATH}
# Expected Result: File successfully downloaded to the local destination.
Get File    ${REMOTE_FILE_PATH}    ${LOCAL_DEST_PATH}
# Step: Close the SSH connection.
# Test Data: N/A
# Expected Result: SSH connection closed.
Close Connection
"""

    input_json_file = tmp_path / "zephyr_test_case.json"
    input_json_file.write_text(json.dumps(zephyr_json_content, indent=2))

    output_robot_file = tmp_path / "generated_robot_file.robot"

    convert_file(str(input_json_file), str(output_robot_file))

    generated_content = output_robot_file.read_text()

    # Use semantic Robot Framework comparison instead of brittle string matching

    # First ensure generated content has valid structure
    assert_robot_framework_syntax_valid(generated_content)

    # Then do semantic comparison with a default-to-exact match for regression testing
    try:
        assert_robot_content_equivalent(generated_content, expected_robot_content)
    except AssertionError:
        # If semantic comparison fails, fall back to exact comparison for debugging
        normalized_generated = "\n".join(
            [line.strip() for line in generated_content.splitlines() if line.strip()]
        )
        normalized_expected = "\n".join(
            [
                line.strip()
                for line in expected_robot_content.splitlines()
                if line.strip()
            ]
        )
        assert normalized_generated == normalized_expected
