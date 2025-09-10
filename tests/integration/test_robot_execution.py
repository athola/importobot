import json


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
    expected_robot_content = """*** Settings ***
Documentation    Tests converted from JSON
Library    SeleniumLibrary

*** Test Cases ***

Retrieve File From Remote Host
    [Documentation]    To retrieve a file from a remote host using SSH.
    # Description: Open an SSH connection and log in to the remote host.
    # Action: Remote Host: ${REMOTE_HOST}, Username: ${USERNAME}, Password: ${PASSWORD}
    # Expected: Successfully connected and logged in to the remote host.
    No Operation  # TODO: Implement step

    # Description: Retrieve the specified file from the remote host.
    # Action: Remote File Path: ${REMOTE_FILE_PATH}, Local Destination Path: ${LOCAL_DEST_PATH}
    # Expected: File successfully downloaded to the local destination.
    No Operation  # TODO: Implement step

    # Description: Close the SSH connection.
    # Action: N/A
    # Expected: SSH connection closed.
    No Operation  # TODO: Implement step"""

    input_json_file = tmp_path / "zephyr_test_case.json"
    input_json_file.write_text(json.dumps(zephyr_json_content, indent=2))

    output_robot_file = tmp_path / "generated_robot_file.robot"

    from importobot.core.converter import convert_to_robot

    convert_to_robot(str(input_json_file), str(output_robot_file))

    generated_content = output_robot_file.read_text()

    normalized_generated = "\n".join(
        [line.strip() for line in generated_content.splitlines() if line.strip()]
    )
    normalized_expected = "\n".join(
        [line.strip() for line in expected_robot_content.splitlines() if line.strip()]
    )

    assert normalized_generated == normalized_expected
