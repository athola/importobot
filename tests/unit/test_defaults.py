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
        assert defaults.default_url == "https://example.com"
        assert defaults.default_browser == "chrome"
        assert defaults.default_locator == "id:element"
        assert defaults.default_timeout == "30s"

        # User credentials defaults
        assert defaults.default_username == "testuser"
        assert defaults.default_password == "testpass"

        # SSH defaults
        assert defaults.default_ssh_host == "localhost"
        assert defaults.default_ssh_port == 22

        # Database defaults
        assert defaults.default_db_query == "SELECT * FROM test_table"
        assert defaults.default_db_connection == "default"
        assert defaults.default_db_host == "localhost"
        assert defaults.default_db_port == 5432

        # API defaults
        assert defaults.default_api_endpoint == "/api/test"
        assert defaults.default_api_method == "GET"
        assert defaults.default_api_session == "default_session"

        # File defaults
        assert defaults.default_file_path == "/tmp/test_file.txt"
        assert defaults.default_file_content == "test content"

    def test_custom_values(self):
        """Test that DataDefaults can be customized."""
        custom_defaults = DataDefaults(
            default_url="https://custom.com",
            default_browser="firefox",
            default_username="customuser",
            default_db_port=3306,
        )

        assert custom_defaults.default_url == "https://custom.com"
        assert custom_defaults.default_browser == "firefox"
        assert custom_defaults.default_username == "customuser"
        assert custom_defaults.default_db_port == 3306

        # Other values should remain default
        assert custom_defaults.default_password == "testpass"
        assert custom_defaults.default_db_host == "localhost"


class TestProgressReportingConfig:
    """Test ProgressReportingConfig dataclass."""

    def test_default_values(self):
        """Test that ProgressReportingConfig has expected default values."""
        config = ProgressReportingConfig()

        assert config.progress_report_percentage == 10
        assert config.file_write_batch_size == 25
        assert config.file_write_progress_threshold == 50
        assert config.file_write_progress_interval == 20

    def test_custom_values(self):
        """Test that ProgressReportingConfig can be customized."""
        custom_config = ProgressReportingConfig(
            progress_report_percentage=5,
            file_write_batch_size=10,
            file_write_progress_threshold=25,
            file_write_progress_interval=5,
        )

        assert custom_config.progress_report_percentage == 5
        assert custom_config.file_write_batch_size == 10
        assert custom_config.file_write_progress_threshold == 25
        assert custom_config.file_write_progress_interval == 5


class TestKeywordPatterns:
    """Test KeywordPatterns dataclass."""

    def test_default_values(self):
        """Test that KeywordPatterns has expected default values."""
        patterns = KeywordPatterns()

        # Check that pattern attributes are lists
        assert isinstance(patterns.browser_patterns, list)
        assert isinstance(patterns.input_patterns, list)
        assert isinstance(patterns.click_patterns, list)
        assert isinstance(patterns.wait_patterns, list)
        assert isinstance(patterns.verification_patterns, list)
        assert isinstance(patterns.ssh_patterns, list)
        assert isinstance(patterns.database_patterns, list)
        assert isinstance(patterns.api_patterns, list)

        # Check that some expected keywords are present
        assert "Open Browser" in patterns.browser_patterns
        assert "Input Text" in patterns.input_patterns
        assert "Click Element" in patterns.click_patterns
        assert "Wait Until" in patterns.wait_patterns
        assert "Should Be Equal" in patterns.verification_patterns
        assert "Execute Command" in patterns.ssh_patterns
        assert "Query" in patterns.database_patterns
        assert "Get" in patterns.api_patterns

    def test_custom_values(self):
        """Test that KeywordPatterns can be customized."""
        custom_browser_patterns = ["Custom Browser Open", "Custom Navigate"]
        custom_patterns = KeywordPatterns(browser_patterns=custom_browser_patterns)

        assert custom_patterns.browser_patterns == custom_browser_patterns
        # Check that other patterns remain default
        assert "Input Text" in custom_patterns.input_patterns


class TestLibraryMapping:
    """Test LibraryMapping dataclass."""

    def test_default_values(self):
        """Test that LibraryMapping has expected default values."""
        mapping = LibraryMapping()

        assert isinstance(mapping.library_aliases, dict)
        assert len(mapping.library_aliases) > 0

        # Check some expected library aliases exist without duplicating the data
        assert "selenium" in mapping.library_aliases
        assert "ssh" in mapping.library_aliases
        assert "requests" in mapping.library_aliases
        assert "database" in mapping.library_aliases
        assert "builtin" in mapping.library_aliases
        assert "os" in mapping.library_aliases

        # Verify structure and content types
        for key, aliases in mapping.library_aliases.items():
            assert isinstance(key, str)
            assert isinstance(aliases, list)
            assert len(aliases) > 0
            assert all(isinstance(alias, str) for alias in aliases)

    def test_custom_values(self):
        """Test that LibraryMapping can be customized."""
        custom_aliases = {"custom_lib": ["CustomLibrary", "custom", "Custom"]}
        custom_mapping = LibraryMapping(library_aliases=custom_aliases)

        assert custom_mapping.library_aliases == custom_aliases


class TestGetDefaultValue:
    """Test get_default_value function."""

    def test_get_default_value_existing_category_key(self):
        """Test get_default_value with existing category and key."""
        # Test web automation defaults
        result = get_default_value("web", "url")
        assert result == "https://example.com"

        # Test database defaults
        result = get_default_value("database", "port")
        assert result == "5432"

    def test_get_default_value_nonexistent_category(self):
        """Test get_default_value with nonexistent category."""
        result = get_default_value("nonexistent", "some_key")
        assert result == ""

    def test_get_default_value_nonexistent_key(self):
        """Test get_default_value with nonexistent key."""
        result = get_default_value("web", "nonexistent_key")
        assert result == ""

    def test_get_default_value_custom_default_value(self):
        """Test get_default_value with custom default value parameter."""
        result = get_default_value(
            "nonexistent", "nonexistent", fallback="custom_default"
        )
        assert result == "custom_default"

    def test_get_default_value_all_categories(self):
        """Test get_default_value works for all default categories."""
        # Test various categories and keys
        test_cases = [
            ("web", "browser", "chrome"),
            ("ssh", "port", "22"),
            ("api", "method", "GET"),
            ("file", "content", "test content"),
        ]

        for category, key, expected in test_cases:
            result = get_default_value(category, key)
            assert result == expected, (
                f"Failed for {category}.{key}: expected {expected}, got {result}"
            )


class TestGlobalInstances:
    """Test global configuration instances."""

    def test_global_instances_exist(self):
        """Test that global instances are properly created."""

        assert isinstance(TEST_DATA_DEFAULTS, DataDefaults)
        assert isinstance(PROGRESS_CONFIG, ProgressReportingConfig)
        assert isinstance(KEYWORD_PATTERNS, KeywordPatterns)
        assert isinstance(LIBRARY_MAPPING, LibraryMapping)

    def test_global_instances_have_correct_defaults(self):
        """Test that global instances have the expected default values."""

        # Test some key defaults
        assert TEST_DATA_DEFAULTS.default_browser == "chrome"
        assert TEST_DATA_DEFAULTS.default_db_port == 5432
        assert PROGRESS_CONFIG.progress_report_percentage == 10
        assert PROGRESS_CONFIG.file_write_progress_threshold == 50


class TestConfigureDefaults:
    """Tests for the configure_defaults function."""

    def test_configure_defaults(self):
        """Test that configure_defaults can modify the default values."""
        # Change a value
        configure_defaults(default_url="https://new.example.com")
        assert get_default_value("web", "url") == "https://new.example.com"

        # Reset to original value
        configure_defaults(default_url="https://example.com")
        assert get_default_value("web", "url") == "https://example.com"


class TestGetLibraryCanonicalName:
    """Tests for the get_library_canonical_name function."""

    def test_get_library_canonical_name(self):
        """Test that the function returns the correct canonical name for different
        aliases."""
        assert get_library_canonical_name("SeleniumLibrary") == "selenium"
        assert get_library_canonical_name("ssh") == "ssh"
        assert get_library_canonical_name("requests") == "requests"
        assert get_library_canonical_name("Database") == "database"
        assert get_library_canonical_name("Built-in") == "builtin"
        assert get_library_canonical_name("os") == "os"

    def test_get_library_canonical_name_not_found(self):
        """Test that the function returns the lowercased name if no alias is found."""
        assert get_library_canonical_name("UnknownLibrary") == "unknownlibrary"
