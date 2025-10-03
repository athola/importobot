"""Configuration constants for Importobot."""

import os
from typing import Any, Union

from importobot.medallion.storage.config import StorageConfig

# Default values
DEFAULT_TEST_SERVER_URL = "http://localhost:8000"
TEST_SERVER_PORT = 8000

# Environment-configurable values
TEST_SERVER_URL = os.getenv("IMPORTOBOT_TEST_SERVER_URL", DEFAULT_TEST_SERVER_URL)

# Test-specific URLs
LOGIN_PAGE_PATH = "/login.html"
TEST_LOGIN_URL = f"{TEST_SERVER_URL}{LOGIN_PAGE_PATH}"

# Chrome options for headless browser testing
CHROME_OPTIONS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--headless",
    "--disable-web-security",
    "--allow-running-insecure-content",
]

# Configuration for maximum file sizes (in MB)
MAX_JSON_SIZE_MB = int(os.getenv("IMPORTOBOT_MAX_JSON_SIZE_MB", "10"))


def update_medallion_config(
    config: Union["StorageConfig", None] = None, **kwargs: Any
) -> "StorageConfig":
    """Update medallion configuration placeholder."""
    # Placeholder implementation for testing
    if config is None:
        config = StorageConfig()

    # kwargs used for potential future configuration updates
    _ = kwargs  # Mark as used for linting
    return config


def validate_medallion_config(_config: "StorageConfig") -> bool:
    """Validate medallion configuration placeholder."""
    # Placeholder implementation for testing
    return True
