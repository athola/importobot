"""Integration tests for new Zephyr format conversion with Robot Framework execution."""

import importlib
import json
import os
import socket
import socketserver
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler

import pytest

import importobot.config
from importobot.core.converter import convert_file
from tests.utils import parse_robot_file


class MyHandler(SimpleHTTPRequestHandler):
    """Custom HTTP request handler for mock web server."""

    def do_GET(self):
        if self.path == "/login.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"""
                <html>
                    <body>
                        <h1>Login</h1>
                        <input type="text" id="username" />
                        <input type="password" id="password" />
                        <button id="login_button"
                                onclick="document.body.innerHTML += '<p>Success!</p>'">
                            Login
                        </button>
                    </body>
                </html>
            """
            )
        else:
            super().do_GET()


@pytest.fixture(scope="module")
def mock_web_server():
    """Start and stop a mock web server for Selenium tests."""
    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port = s.getsockname()[1]

    # Set the environment variable for the config to pick up
    os.environ["IMPORTOBOT_TEST_SERVER_URL"] = f"http://localhost:{port}"
    # Reload the config to pick up the new URL
    importlib.reload(importobot.config)

    httpd = None
    server_thread = None
    try:
        socketserver.TCPServer.allow_reuse_address = True
        httpd = socketserver.TCPServer(("", port), MyHandler)
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print(f"Mock server started on port {port} in a separate thread.")
        yield
    finally:
        if httpd:
            httpd.shutdown()
            httpd.server_close()
        if server_thread and server_thread.is_alive():
            server_thread.join(timeout=1)  # Give the thread a moment to finish
        print("Mock server stopped.")


def test_zephyr_integration_keyword_types(tmp_path):
    """Tests that the generated robot file contains expected keywords."""
    zephyr_json_content = {
        "name": "Sample Zephyr Test",
        "objective": "Testing Zephyr format conversion to Robot Framework.",
        "precondition": "User has valid login credentials.",
        "testScript": {
            "type": "STEP_BY_STEP",
            "steps": [
                {
                    "description": "Navigate to the application login page.",
                    "expectedResult": "Login page is displayed successfully.",
                },
                {
                    "description": "Enter valid username in the 'Username' field.",
                    "testData": "username: testuser@example.com",
                    "expectedResult": "The username field accepts the input.",
                },
                {
                    "description": "Enter valid password in the 'Password' field.",
                    "testData": "password: password123",
                    "expectedResult": "The password field accepts the input.",
                },
                {
                    "description": "Click the 'Login' button.",
                    "expectedResult": (
                        "User is redirected to the application dashboard."
                    ),
                },
            ],
        },
    }

    input_json_file = tmp_path / "test_case.json"
    input_json_file.write_text(json.dumps(zephyr_json_content, indent=2))

    output_robot_file = tmp_path / "output.robot"

    convert_file(str(input_json_file), str(output_robot_file))

    assert output_robot_file.exists(), "Output robot file was not created"

    # Parse generated robot file for testing
    generated_data = parse_robot_file(str(output_robot_file))

    # Verify minimum expected structure
    assert len(generated_data) >= 1
    assert any(
        "Sample Zephyr Test" in item.get("name", "") for item in generated_data
    ), "Test case name not found in generated data"

    # Verify key functional keywords are present
    # Get keywords from both individual keyword items and nested keywords lists
    keyword_names = []
    for item in generated_data:
        if "keyword" in item:
            keyword_names.append(item["keyword"])
        elif "keywords" in item:
            keyword_names.extend([kw["keyword"] for kw in item["keywords"]])

    assert "Open Browser" in keyword_names
    assert "Input Text" in keyword_names
    assert "Click Button" in keyword_names or "Click Element" in keyword_names


def test_robot_execution_against_mock_server(
    tmp_path,
    mock_web_server,  # pylint: disable=unused-argument,redefined-outer-name
):
    """
    Generates a .robot file and executes it against the mock web server
    to verify its functionality.
    """
    zephyr_json_content = {
        "projectKey": "YOUR_PROJECT_KEY",
        "name": "Verify User Login Functionality",
        "priorityName": "High",
        "statusName": "Draft",
        "objective": (
            "To ensure users can successfully log in to the application "
            "with valid credentials."
        ),
        "precondition": "User has an active account and valid login credentials.",
        "testScript": {
            "type": "STEP_BY_STEP",
            "steps": [
                {
                    "description": "Navigate to the application login page.",
                    "expectedResult": "Login",
                },
                {
                    "description": "Enter a valid username in the 'Username' field.",
                    "testData": "username: testuser@example.com",
                    "expectedResult": "The username field accepts the input.",
                },
                {
                    "description": "Enter a valid password in the 'Password' field.",
                    "testData": "password: password123",
                    "expectedResult": "The password field accepts the input.",
                },
                {
                    "description": "Click the 'Login' button.",
                    "expectedResult": "Login",
                },
            ],
        },
    }

    input_json_file = tmp_path / "mock_server_test_case.json"
    input_json_file.write_text(json.dumps(zephyr_json_content, indent=2))

    output_robot_file = tmp_path / "mock_server_test.robot"

    convert_file(str(input_json_file), str(output_robot_file))

    # Verify that the Robot Framework file was created
    assert output_robot_file.exists()

    # Run Robot Framework on the generated file against the mock server
    # We need to ensure robot command is available in the test environment
    chrome_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    robot_command = [
        "robot",
        "--outputdir",
        str(tmp_path),
        "--variable",
        "BROWSER:chrome",  # Use Chrome for execution
        "--variable",
        "SELENIUM_SPEED:0.1",  # Slow down for observation
        "--variable",
        f"SELENIUM_CHROME_DRIVER:{chrome_path}",  # Explicitly set chromedriver path
        str(output_robot_file),
    ]
    # Ensure the mock server URL environment variable is passed to robot
    test_env = os.environ.copy()
    result = subprocess.run(
        robot_command, capture_output=True, text=True, check=False, env=test_env
    )

    # Assert that Robot Framework execution was successful (exit code 0)
    assert result.returncode == 0, (
        f"Robot Framework execution failed with exit code {result.returncode}.\n"
        f"Stdout: {result.stdout}\nStderr: {result.stderr}"
    )
