"""Configuration constants for Importobot."""

import os

# Default values
DEFAULT_TEST_SERVER_HOST = "localhost"
DEFAULT_TEST_SERVER_PORT = 8000
DEFAULT_TEST_SERVER_URL = (
    f"http://{DEFAULT_TEST_SERVER_HOST}:{DEFAULT_TEST_SERVER_PORT}"
)

# Environment-configurable values
TEST_SERVER_URL = os.getenv("IMPORTOBOT_TEST_SERVER_URL", DEFAULT_TEST_SERVER_URL)
TEST_SERVER_PORT = int(
    os.getenv("IMPORTOBOT_TEST_SERVER_PORT", str(DEFAULT_TEST_SERVER_PORT))
)

# Test-specific URLs
LOGIN_PAGE_PATH = "/login.html"
TEST_LOGIN_URL = f"{TEST_SERVER_URL}{LOGIN_PAGE_PATH}"
