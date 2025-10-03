"""Tests for default values and configuration constants."""

from importobot.utils.defaults import (
    KEYWORD_PATTERNS,
    LIBRARY_MAPPING,
    PROGRESS_CONFIG,
    TEST_DATA_DEFAULTS,
    DataDefaults,
    KeywordPatterns,
    LibraryMapping,
    ProgressReportingConfig,
    configure_defaults,
    get_default_value,
    get_library_canonical_name,
)


class TestDataDefaults:
    """Test DataDefaults dataclass."""

    def test_default_values(self):
        """Test that DataDefaults has expected default values."""
        defaults = DataDefaults()

        # Web automation defaults
        assert defaults.web.url == "https://example.com"
        assert defaults.web.browser == "chrome"
        assert defaults.web.locator == "id:element"
        assert defaults.web.timeout == "30s"

        # User credentials defaults
        assert defaults.user.username == "testuser"
        assert defaults.user.password == "testpass"

        # SSH defaults
        assert defaults.ssh.host == "localhost"
        assert defaults.ssh.port == 22

        # Database defaults
        assert defaults.database.query == "SELECT * FROM test_table"
        assert defaults.database.connection == "default"
        assert defaults.database.host == "localhost"
        assert defaults.database.port == 5432

        # API defaults
        assert defaults.api.endpoint == "/api/test"
        assert defaults.api.method == "GET"
        assert defaults.api.session == "default_session"

        # File defaults
        assert defaults.file.path == "/tmp/test_file.txt"
        assert defaults.file.content == "test content"

    def test_custom_values_with_dot_notation(self):
        """Test that DataDefaults can be customized using dot notation."""
        custom_defaults = DataDefaults(
            **{
                "web.url": "https://custom.com",
                "web.browser": "firefox",
                "user.username": "customuser",
                "database.port": 3306,
            }
        )

        assert custom_defaults.web.url == "https://custom.com"
        assert custom_defaults.web.browser == "firefox"
        assert custom_defaults.user.username == "customuser"
        assert custom_defaults.database.port == 3306

        # Other values should remain default
        assert custom_defaults.user.password == "testpass"
        assert custom_defaults.database.host == "localhost"


class TestProgressReportingConfig:
    """Test ProgressReportingConfig dataclass."""

    def test_default_values(self):
        """Test that ProgressReportingConfig has expected default values."""
        config = ProgressReportingConfig()

        assert config.progress_report_percentage == 10
        assert config.file_write_batch_size == 25
        assert config.file_write_progress_threshold == 50
        assert config.file_write_progress_interval == 20

        assert config.intent_cache_limit == 512
        assert config.intent_cache_cleanup_threshold == 1024
        assert config.pattern_cache_limit == 256

    def test_custom_values(self):
        """Test that ProgressReportingConfig can be customized."""
        config = ProgressReportingConfig(
            progress_report_percentage=5,
            file_write_batch_size=50,
        )

        assert config.progress_report_percentage == 5
        assert config.file_write_batch_size == 50

        # Other values should remain default
        assert config.file_write_progress_threshold == 50
        assert config.intent_cache_limit == 512


class TestKeywordPatterns:
    """Test KeywordPatterns dataclass."""

    def test_default_values(self):
        """Test that KeywordPatterns has expected default values."""
        patterns = KeywordPatterns()

        assert "Open Browser" in patterns.browser_patterns
        assert "Input Text" in patterns.input_patterns
        assert "Click" in patterns.click_patterns
        assert "Wait" in patterns.wait_patterns
        assert "Should Be Equal" in patterns.verification_patterns
        assert "SSH" in patterns.ssh_patterns
        assert "Database" in patterns.database_patterns
        assert "API" in patterns.api_patterns


class TestLibraryMapping:
    """Test LibraryMapping dataclass."""

    def test_default_values(self):
        """Test that LibraryMapping has expected default values."""
        mapping = LibraryMapping()

        assert "SeleniumLibrary" in mapping.library_aliases["selenium"]
        assert "SSHLibrary" in mapping.library_aliases["ssh"]
        assert "RequestsLibrary" in mapping.library_aliases["requests"]
        assert "DatabaseLibrary" in mapping.library_aliases["database"]
        assert "BuiltIn" in mapping.library_aliases["builtin"]
        assert "OperatingSystem" in mapping.library_aliases["os"]


class TestGetDefaultValue:
    """Test get_default_value function."""

    def test_get_existing_values(self):
        """Test getting existing default values."""
        assert get_default_value("web", "url") == "https://example.com"
        assert get_default_value("user", "username") == "testuser"
        assert get_default_value("ssh", "host") == "localhost"
        assert get_default_value("ssh", "port") == "22"  # Note: converted to string

    def test_get_nonexistent_values(self):
        """Test getting non-existent default values."""
        assert (
            get_default_value("nonexistent", "nonexistent", fallback="custom_default")
            == "custom_default"
        )
        assert get_default_value("web", "nonexistent") == ""
        assert get_default_value("nonexistent", "url") == ""


class TestGetLibraryCanonicalName:
    """Test get_library_canonical_name function."""

    def test_get_canonical_names(self):
        """Test getting canonical library names."""
        assert get_library_canonical_name("SeleniumLibrary") == "selenium"
        assert get_library_canonical_name("selenium") == "selenium"
        assert get_library_canonical_name("Selenium") == "selenium"
        assert get_library_canonical_name("SELENIUM") == "selenium"

        assert get_library_canonical_name("SSHLibrary") == "ssh"
        assert get_library_canonical_name("ssh") == "ssh"

        assert get_library_canonical_name("BuiltIn") == "builtin"
        assert get_library_canonical_name("Built-in") == "builtin"

    def test_get_unknown_library(self):
        """Test getting canonical name for unknown library."""
        assert get_library_canonical_name("UnknownLibrary") == "unknownlibrary"
        assert get_library_canonical_name("Custom") == "custom"


class TestConfigureDefaults:
    """Test configure_defaults function."""

    def test_configure_with_dot_notation(self):
        """Test configuring defaults with dot notation."""
        # Store original values
        original_url = TEST_DATA_DEFAULTS.web.url
        original_username = TEST_DATA_DEFAULTS.user.username

        try:
            configure_defaults(
                **{
                    "web.url": "https://configured.com",
                    "user.username": "configureduser",
                }
            )

            assert TEST_DATA_DEFAULTS.web.url == "https://configured.com"
            assert TEST_DATA_DEFAULTS.user.username == "configureduser"

        finally:
            # Restore original values
            configure_defaults(
                **{"web.url": original_url, "user.username": original_username}
            )

    def test_configure_progress_config(self):
        """Test configuring progress configuration."""
        original_percentage = PROGRESS_CONFIG.progress_report_percentage

        try:
            configure_defaults(progress_report_percentage=25)
            assert PROGRESS_CONFIG.progress_report_percentage == 25

        finally:
            # Restore original value
            configure_defaults(progress_report_percentage=original_percentage)


class TestGlobalInstances:
    """Test global configuration instances."""

    def test_global_instances_exist(self):
        """Test that global instances are created."""
        assert isinstance(TEST_DATA_DEFAULTS, DataDefaults)
        assert isinstance(PROGRESS_CONFIG, ProgressReportingConfig)
        assert isinstance(KEYWORD_PATTERNS, KeywordPatterns)
        assert isinstance(LIBRARY_MAPPING, LibraryMapping)

    def test_global_instances_have_default_values(self):
        """Test that global instances have expected default values."""
        assert TEST_DATA_DEFAULTS.web.browser == "chrome"
        assert TEST_DATA_DEFAULTS.database.port == 5432
