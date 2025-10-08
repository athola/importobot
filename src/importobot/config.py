"""Configuration constants for Importobot."""

import logging
import os
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:  # pragma: no cover - circular import guard for type checking
    from importobot.medallion.storage.config import StorageConfig

# Module-level logger for configuration warnings
logger = logging.getLogger(__name__)

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


def _int_from_env(var_name: str, default: int, *, minimum: int | None = None) -> int:
    """Parse integer environment variable with validation."""
    raw_value = os.getenv(var_name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid %s=%s; falling back to default %d", var_name, raw_value, default
        )
        return default
    if minimum is not None and value < minimum:
        logger.warning(
            "%s must be >= %d (received %d); using default %d",
            var_name,
            minimum,
            value,
            default,
        )
        return default
    return value


DETECTION_CACHE_MAX_SIZE = _int_from_env(
    "IMPORTOBOT_DETECTION_CACHE_MAX_SIZE", 1000, minimum=1
)
DETECTION_CACHE_COLLISION_LIMIT = _int_from_env(
    "IMPORTOBOT_DETECTION_CACHE_COLLISION_LIMIT", 3, minimum=1
)
DETECTION_CACHE_TTL_SECONDS = _int_from_env(
    "IMPORTOBOT_DETECTION_CACHE_TTL_SECONDS", 0, minimum=0
)
FILE_CONTENT_CACHE_MAX_MB = _int_from_env(
    "IMPORTOBOT_FILE_CACHE_MAX_MB", 100, minimum=1
)
FILE_CONTENT_CACHE_TTL_SECONDS = _int_from_env(
    "IMPORTOBOT_FILE_CACHE_TTL_SECONDS", 0, minimum=0
)
PERFORMANCE_CACHE_MAX_SIZE = _int_from_env(
    "IMPORTOBOT_PERFORMANCE_CACHE_MAX_SIZE", 1000, minimum=1
)
PERFORMANCE_CACHE_TTL_SECONDS = _int_from_env(
    "IMPORTOBOT_PERFORMANCE_CACHE_TTL_SECONDS", 0, minimum=0
)
OPTIMIZATION_CACHE_TTL_SECONDS = _int_from_env(
    "IMPORTOBOT_OPTIMIZATION_CACHE_TTL_SECONDS", 0, minimum=0
)


def update_medallion_config(
    config: Union["StorageConfig", None] = None, **kwargs: Any
) -> "StorageConfig":
    """Update medallion configuration placeholder.

    Uses lazy import to avoid circular dependency with medallion.storage.config.
    """
    # Import moved inside function to break circular dependency
    # pylint: disable=import-outside-toplevel
    from importobot.medallion.storage.config import StorageConfig

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
