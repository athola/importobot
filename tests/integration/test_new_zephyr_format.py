import json
import socketserver
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler

import pytest

from importobot.core.converter import convert_to_robot
from tests.utils import parse_robot_file

PORT = 8000


class MyHandler(SimpleHTTPRequestHandler):
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
                        <input type=\"text\" id=\"username_field" />
                        <input type=\"password\" id=\"password_field" />
                        <button id=\"login_button\"\\
                            onclick=\"document.body.innerHTML += \\
                            '<h2>Login successful!</h2>'\"\\
                            >Login</button>
                    </body>
                </html>
            """
            )
        else:
            super().do_GET()


@pytest.fixture(scope="module")
def mock_web_server():
    """Starts and stops a mock web server for Selenium tests."""
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print(f"Mock server started on port {PORT} in a separate thread.")
        yield
        httpd.shutdown()
        httpd.server_close()
        print(f"Mock server stopped on port {PORT}.")


def test_zephyr_to_robot_conversion_new_format(tmp_path):
    """
    Ensures that a .robot file generated from the new Zephyr JSON format
    matches the expected Robot Framework content (test case logic only).
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

    input_json_file = tmp_path / "new_zephyr_test_case.json"
    input_json_file.write_text(json.dumps(zephyr_json_content, indent=2))

    output_robot_file = tmp_path / "generated_robot_file_new_format.robot"

    convert_to_robot(str(input_json_file), str(output_robot_file))

    generated_keywords = parse_robot_file(output_robot_file)

    # Verify Chrome options setup keywords are present
    assert generated_keywords[0]["keyword"] == "Evaluate"
    assert "selenium.webdriver" in generated_keywords[0]["args"][0]

    # Verify Chrome arguments are configured
    chrome_args = [kw for kw in generated_keywords if kw["keyword"] == "Call Method"]
    assert len(chrome_args) == 6  # 6 Chrome arguments

    # Verify key arguments are present
    chrome_arg_strings = [arg["args"][2] for arg in chrome_args]
    assert "argument=--headless" in chrome_arg_strings
    assert "argument=--no-sandbox" in chrome_arg_strings
    assert any("argument=--user-data-dir=" in arg for arg in chrome_arg_strings)

    # Find the Open Browser keyword
    open_browser_kw = next(
        kw for kw in generated_keywords if kw["keyword"] == "Open Browser"
    )
    assert open_browser_kw["args"][0] == "http://localhost:8000/login.html"
    assert open_browser_kw["args"][1] == "chrome"
    assert "options=${chrome_options}" in open_browser_kw["args"]

    # Verify key functional keywords are present
    keyword_names = [kw["keyword"] for kw in generated_keywords]
    assert "Go To" in keyword_names
    assert "Input Text" in keyword_names
    assert "Click Button" in keyword_names
    assert "Close Browser" in keyword_names


def test_robot_execution_against_mock_server(tmp_path, mock_web_server):
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

    convert_to_robot(str(input_json_file), str(output_robot_file))

    # Verify that the Robot Framework file was created
    assert output_robot_file.exists()

    # Run Robot Framework on the generated file against the mock server
    # We need to ensure robot command is available in the test environment
    robot_command = [
        "robot",
        "--outputdir",
        str(tmp_path),
        "--variable",
        "BROWSER:chrome",  # Use Chrome for execution
        str(output_robot_file),
    ]
    result = subprocess.run(robot_command, capture_output=True, text=True, check=False)

    # Assert that Robot Framework execution was successful (exit code 0)
    assert result.returncode == 0, (
        f"Robot Framework execution failed with exit code {result.returncode}.\n"
        f"Stdout: {result.stdout}\nStderr: {result.stderr}"
    )
