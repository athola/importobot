"""Default values and configuration constants for test generation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TestDataDefaults:  # pylint: disable=too-many-instance-attributes
    """Default values for test data generation."""

    # Web automation defaults
    default_url: str = "https://example.com"
    default_browser: str = "chrome"
    default_locator: str = "id:element"
    default_timeout: str = "30s"

    # User credentials defaults
    default_username: str = "testuser"
    default_password: str = "testpass"

    # SSH defaults
    default_ssh_host: str = "localhost"
    default_ssh_port: int = 22

    # Database defaults
    default_db_query: str = "SELECT * FROM test_table"
    default_db_connection: str = "default"
    default_db_host: str = "localhost"
    default_db_port: int = 5432

    # API defaults
    default_api_endpoint: str = "/api/test"
    default_api_method: str = "GET"
    default_api_session: str = "default_session"

    # File defaults
    default_file_path: str = "/tmp/test_file.txt"
    default_file_content: str = "test content"


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

    browser_patterns: List[str] = field(
        default_factory=lambda: ["Open Browser", "OpenBrowser", "Navigate To", "Go To"]
    )

    input_patterns: List[str] = field(
        default_factory=lambda: [
            "Input Text",
            "InputText",
            "Input Password",
            "Type Text",
        ]
    )

    click_patterns: List[str] = field(
        default_factory=lambda: ["Click", "Click Element", "Click Button", "Click Link"]
    )

    wait_patterns: List[str] = field(
        default_factory=lambda: ["Wait", "Sleep", "Wait Until", "Wait For"]
    )

    verification_patterns: List[str] = field(
        default_factory=lambda: [
            "Should Be Equal",
            "Should Contain",
            "Should Be",
            "Verify",
        ]
    )

    ssh_patterns: List[str] = field(
        default_factory=lambda: ["SSH", "Ssh", "Execute Command", "Open Connection"]
    )

    database_patterns: List[str] = field(
        default_factory=lambda: ["Database", "DB", "Sql", "Query", "Execute Sql"]
    )

    api_patterns: List[str] = field(
        default_factory=lambda: ["API", "Request", "Get", "Post", "Put", "Delete"]
    )


@dataclass
class LibraryMapping:
    """Mapping of library names to their common aliases."""

    library_aliases: Dict[str, List[str]] = field(
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
TEST_DATA_DEFAULTS = TestDataDefaults()
PROGRESS_CONFIG = ProgressReportingConfig()
KEYWORD_PATTERNS = KeywordPatterns()
LIBRARY_MAPPING = LibraryMapping()


def get_default_value(category: str, key: str, fallback: str = "") -> str:
    """Get a default value by category and key."""
    defaults_map = {
        "web": {
            "url": TEST_DATA_DEFAULTS.default_url,
            "browser": TEST_DATA_DEFAULTS.default_browser,
            "locator": TEST_DATA_DEFAULTS.default_locator,
            "timeout": TEST_DATA_DEFAULTS.default_timeout,
        },
        "user": {
            "username": TEST_DATA_DEFAULTS.default_username,
            "password": TEST_DATA_DEFAULTS.default_password,
        },
        "ssh": {
            "host": TEST_DATA_DEFAULTS.default_ssh_host,
            "port": str(TEST_DATA_DEFAULTS.default_ssh_port),
            "username": TEST_DATA_DEFAULTS.default_username,
        },
        "database": {
            "query": TEST_DATA_DEFAULTS.default_db_query,
            "connection": TEST_DATA_DEFAULTS.default_db_connection,
            "host": TEST_DATA_DEFAULTS.default_db_host,
            "port": str(TEST_DATA_DEFAULTS.default_db_port),
        },
        "api": {
            "endpoint": TEST_DATA_DEFAULTS.default_api_endpoint,
            "method": TEST_DATA_DEFAULTS.default_api_method,
            "session": TEST_DATA_DEFAULTS.default_api_session,
        },
        "file": {
            "path": TEST_DATA_DEFAULTS.default_file_path,
            "content": TEST_DATA_DEFAULTS.default_file_content,
        },
    }

    return defaults_map.get(category, {}).get(key, fallback)


def configure_defaults(**kwargs: Any) -> None:
    """Configure default values at runtime."""
    # Access module-level instances to modify their attributes
    test_defaults = TEST_DATA_DEFAULTS
    progress_config = PROGRESS_CONFIG
    keyword_patterns = KEYWORD_PATTERNS

    for key, value in kwargs.items():
        if hasattr(test_defaults, key):
            setattr(test_defaults, key, value)
        elif hasattr(progress_config, key):
            setattr(progress_config, key, value)
        elif hasattr(keyword_patterns, key):
            setattr(keyword_patterns, key, value)


def get_library_canonical_name(library_name: str) -> str:
    """Get the canonical name for a library from its alias."""
    library_lower = library_name.lower()

    for canonical, aliases in LIBRARY_MAPPING.library_aliases.items():
        if library_lower in [alias.lower() for alias in aliases]:
            return canonical

    return library_name.lower()
