"""Default values and configuration constants for test generation."""

import os
from dataclasses import dataclass, field
from typing import Any

_SAFE_HOME_ROOT = os.path.join(os.path.expanduser("~"), "importobot")


@dataclass
class WebDefaults:
    """Default values for web automation."""

    url: str = "https://example.com"
    browser: str = "chrome"
    locator: str = "id:element"
    timeout: str = "30s"


@dataclass
class UserDefaults:
    """Default values for user credentials."""

    username: str = "testuser"
    password: str = "testpass"


@dataclass
class SSHDefaults:
    """Default values for SSH connections."""

    host: str = "localhost"
    port: int = 22


@dataclass
class DatabaseDefaults:
    """Default values for database operations."""

    query: str = "SELECT * FROM test_table"
    connection: str = "default"
    host: str = "localhost"
    port: int = 5432


@dataclass
class APIDefaults:
    """Default values for API operations."""

    endpoint: str = "/api/test"
    method: str = "GET"
    session: str = "default_session"


@dataclass
class FileDefaults:
    """Default values for file operations."""

    path: str = os.path.join(_SAFE_HOME_ROOT, "test_file.txt")
    content: str = "test content"


class DataDefaults:
    """Organized default values for test data generation."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize defaults with optional overrides."""
        self.web = WebDefaults()
        self.user = UserDefaults()
        self.ssh = SSHDefaults()
        self.database = DatabaseDefaults()
        self.api = APIDefaults()
        self.file = FileDefaults()

        # Apply any provided overrides using dot notation
        for key, value in kwargs.items():
            if "." in key:
                category, attr = key.split(".", 1)
                if hasattr(self, category):
                    category_obj = getattr(self, category)
                    if hasattr(category_obj, attr):
                        setattr(category_obj, attr, value)


@dataclass
class ProgressReportingConfig:
    """Configuration for progress reporting functionality."""

    # Progress reporting intervals
    progress_report_percentage: int = 10  # Report every 10%
    file_write_batch_size: int = 25  # Batch size for file writes
    file_write_progress_threshold: int = 50  # Start reporting progress for batches > 50
    file_write_progress_interval: int = 20  # Report every 20 files in large batches

    # Cache management
    intent_cache_limit: int = 512
    intent_cache_cleanup_threshold: int = 1024
    pattern_cache_limit: int = 256


@dataclass
class KeywordPatterns:
    """Configurable patterns for keyword detection."""

    browser_patterns: list[str] = field(
        default_factory=lambda: ["Open Browser", "OpenBrowser", "Navigate To", "Go To"]
    )

    input_patterns: list[str] = field(
        default_factory=lambda: [
            "Input Text",
            "InputText",
            "Input Password",
            "Type Text",
        ]
    )

    click_patterns: list[str] = field(
        default_factory=lambda: ["Click", "Click Element", "Click Button", "Click Link"]
    )

    wait_patterns: list[str] = field(
        default_factory=lambda: ["Wait", "Sleep", "Wait Until", "Wait For"]
    )

    verification_patterns: list[str] = field(
        default_factory=lambda: [
            "Should Be Equal",
            "Should Contain",
            "Should Be",
            "Verify",
        ]
    )

    ssh_patterns: list[str] = field(
        default_factory=lambda: ["SSH", "Ssh", "Execute Command", "Open Connection"]
    )

    database_patterns: list[str] = field(
        default_factory=lambda: ["Database", "DB", "Sql", "Query", "Execute Sql"]
    )

    api_patterns: list[str] = field(
        default_factory=lambda: ["API", "Request", "Get", "Post", "Put", "Delete"]
    )


@dataclass
class LibraryMapping:
    """Mapping of library names to their common aliases."""

    library_aliases: dict[str, list[str]] = field(
        default_factory=lambda: {
            "selenium": ["SeleniumLibrary", "selenium", "Selenium"],
            "ssh": ["SSHLibrary", "ssh", "SSH"],
            "requests": ["RequestsLibrary", "requests", "Requests"],
            "database": ["DatabaseLibrary", "database", "Database"],
            "builtin": ["BuiltIn", "builtin", "Built-in"],
            "os": ["OperatingSystem", "os", "OS"],
        }
    )


# Global configuration instances
TEST_DATA_DEFAULTS = DataDefaults()
PROGRESS_CONFIG = ProgressReportingConfig()
KEYWORD_PATTERNS = KeywordPatterns()
LIBRARY_MAPPING = LibraryMapping()


def get_default_value(category: str, key: str, default_value: str = "") -> str:
    """Get a default value by category and key."""
    defaults_map = {
        "web": {
            "url": TEST_DATA_DEFAULTS.web.url,
            "browser": TEST_DATA_DEFAULTS.web.browser,
            "locator": TEST_DATA_DEFAULTS.web.locator,
            "timeout": TEST_DATA_DEFAULTS.web.timeout,
        },
        "user": {
            "username": TEST_DATA_DEFAULTS.user.username,
            "password": TEST_DATA_DEFAULTS.user.password,
        },
        "ssh": {
            "host": TEST_DATA_DEFAULTS.ssh.host,
            "port": str(TEST_DATA_DEFAULTS.ssh.port),
            "username": TEST_DATA_DEFAULTS.user.username,
        },
        "database": {
            "query": TEST_DATA_DEFAULTS.database.query,
            "connection": TEST_DATA_DEFAULTS.database.connection,
            "host": TEST_DATA_DEFAULTS.database.host,
            "port": str(TEST_DATA_DEFAULTS.database.port),
        },
        "api": {
            "endpoint": TEST_DATA_DEFAULTS.api.endpoint,
            "method": TEST_DATA_DEFAULTS.api.method,
            "session": TEST_DATA_DEFAULTS.api.session,
        },
        "file": {
            "path": TEST_DATA_DEFAULTS.file.path,
            "content": TEST_DATA_DEFAULTS.file.content,
        },
    }

    return defaults_map.get(category, {}).get(key, default_value)


def configure_defaults(**kwargs: Any) -> None:
    """Configure default values at runtime using dot notation."""
    test_defaults = TEST_DATA_DEFAULTS
    progress_config = PROGRESS_CONFIG
    keyword_patterns = KEYWORD_PATTERNS

    for key, value in kwargs.items():
        # Handle nested defaults with dot notation (web.url, user.username, etc.)
        if "." in key:
            category, attr = key.split(".", 1)
            if hasattr(test_defaults, category):
                category_obj = getattr(test_defaults, category)
                if hasattr(category_obj, attr):
                    setattr(category_obj, attr, value)
        # Check top-level DataDefaults attributes
        elif hasattr(test_defaults, key):
            setattr(test_defaults, key, value)
        # Check progress config
        elif hasattr(progress_config, key):
            setattr(progress_config, key, value)
        # Check keyword patterns
        elif hasattr(keyword_patterns, key):
            setattr(keyword_patterns, key, value)


def get_library_canonical_name(library_name: str) -> str:
    """Get the canonical name for a library from its alias."""
    library_lower = library_name.lower()

    for canonical, aliases in LIBRARY_MAPPING.library_aliases.items():
        if library_lower in [alias.lower() for alias in aliases]:
            return canonical

    return library_name.lower()


# Internal utility - not part of public API
__all__: list[str] = []
