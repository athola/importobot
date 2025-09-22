"""Default values and configuration constants for test generation."""

from dataclasses import dataclass, field
from typing import Any


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

    path: str = "/tmp/test_file.txt"
    content: str = "test content"


class DataDefaults:
    """Organized default values for test data generation."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize with support for both new and legacy attribute names."""
        # Initialize nested defaults
        self.web = WebDefaults()
        self.user = UserDefaults()
        self.ssh = SSHDefaults()
        self.database = DatabaseDefaults()
        self.api = APIDefaults()
        self.file = FileDefaults()

        # Handle legacy attribute names in constructor
        legacy_mapping = {
            "default_url": ("web", "url"),
            "default_browser": ("web", "browser"),
            "default_locator": ("web", "locator"),
            "default_timeout": ("web", "timeout"),
            "default_username": ("user", "username"),
            "default_password": ("user", "password"),
            "default_ssh_host": ("ssh", "host"),
            "default_ssh_port": ("ssh", "port"),
            "default_db_query": ("database", "query"),
            "default_db_connection": ("database", "connection"),
            "default_db_host": ("database", "host"),
            "default_db_port": ("database", "port"),
            "default_api_endpoint": ("api", "endpoint"),
            "default_api_method": ("api", "method"),
            "default_api_session": ("api", "session"),
            "default_file_path": ("file", "path"),
            "default_file_content": ("file", "content"),
        }

        for key, value in kwargs.items():
            if key in legacy_mapping:
                category, attr = legacy_mapping[key]
                category_obj = getattr(self, category)
                setattr(category_obj, attr, value)
            elif hasattr(self, key):
                setattr(self, key, value)

    # Backward compatibility properties for tests
    @property
    def default_url(self) -> str:
        """Backward compatibility property."""
        return self.web.url

    @property
    def default_browser(self) -> str:
        """Backward compatibility property."""
        return self.web.browser

    @property
    def default_locator(self) -> str:
        """Backward compatibility property."""
        return self.web.locator

    @property
    def default_timeout(self) -> str:
        """Backward compatibility property."""
        return self.web.timeout

    @property
    def default_username(self) -> str:
        """Backward compatibility property."""
        return self.user.username

    @property
    def default_password(self) -> str:
        """Backward compatibility property."""
        return self.user.password

    @property
    def default_ssh_host(self) -> str:
        """Backward compatibility property."""
        return self.ssh.host

    @property
    def default_ssh_port(self) -> int:
        """Backward compatibility property."""
        return self.ssh.port

    @property
    def default_db_query(self) -> str:
        """Backward compatibility property."""
        return self.database.query

    @property
    def default_db_connection(self) -> str:
        """Backward compatibility property."""
        return self.database.connection

    @property
    def default_db_host(self) -> str:
        """Backward compatibility property."""
        return self.database.host

    @property
    def default_db_port(self) -> int:
        """Backward compatibility property."""
        return self.database.port

    @property
    def default_api_endpoint(self) -> str:
        """Backward compatibility property."""
        return self.api.endpoint

    @property
    def default_api_method(self) -> str:
        """Backward compatibility property."""
        return self.api.method

    @property
    def default_api_session(self) -> str:
        """Backward compatibility property."""
        return self.api.session

    @property
    def default_file_path(self) -> str:
        """Backward compatibility property."""
        return self.file.path

    @property
    def default_file_content(self) -> str:
        """Backward compatibility property."""
        return self.file.content


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


def get_default_value(category: str, key: str, fallback: str = "") -> str:
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

    return defaults_map.get(category, {}).get(key, fallback)


def configure_defaults(**kwargs: Any) -> None:
    """Configure default values at runtime."""
    # Access module-level instances to modify their attributes
    test_defaults = TEST_DATA_DEFAULTS
    progress_config = PROGRESS_CONFIG
    keyword_patterns = KEYWORD_PATTERNS

    # Backward compatibility mapping for old attribute names
    legacy_mapping = {
        "default_url": ("web", "url"),
        "default_browser": ("web", "browser"),
        "default_locator": ("web", "locator"),
        "default_timeout": ("web", "timeout"),
        "default_username": ("user", "username"),
        "default_password": ("user", "password"),
        "default_ssh_host": ("ssh", "host"),
        "default_ssh_port": ("ssh", "port"),
        "default_db_query": ("database", "query"),
        "default_db_connection": ("database", "connection"),
        "default_db_host": ("database", "host"),
        "default_db_port": ("database", "port"),
        "default_api_endpoint": ("api", "endpoint"),
        "default_api_method": ("api", "method"),
        "default_api_session": ("api", "session"),
        "default_file_path": ("file", "path"),
        "default_file_content": ("file", "content"),
    }

    for key, value in kwargs.items():
        # Handle legacy attribute names
        if key in legacy_mapping:
            category, attr = legacy_mapping[key]
            category_obj = getattr(test_defaults, category)
            setattr(category_obj, attr, value)
        # Check top-level DataDefaults attributes
        elif hasattr(test_defaults, key):
            setattr(test_defaults, key, value)
        # Check nested defaults (web, user, ssh, etc.)
        elif "." in key:
            category, attr = key.split(".", 1)
            if hasattr(test_defaults, category):
                category_obj = getattr(test_defaults, category)
                if hasattr(category_obj, attr):
                    setattr(category_obj, attr, value)
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
