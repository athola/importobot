"""Comprehensive TDD tests for Zephyr PlatformCommandParser - Platform Agnostic."""

from importobot.core.zephyr_parsers import PlatformCommandParser


class TestPlatformCommandParser:
    """Test PlatformCommandParser class."""

    def setup_method(self):
        """Set up test fixtures with test-specific platform configuration.

        Uses test data instead of customer-specific hard-coded platforms.
        In production, platforms should be provided via --input-schema.
        """
        self.parser = PlatformCommandParser()
        # Configure test platforms (would come from --input-schema in production)
        self.parser.PLATFORM_KEYWORDS = {
            "TEST_PLATFORM1": ["target", "default", "standard"],
            "TEST_PLATFORM2": ["alternative", "secondary"],
            "TEST_PLATFORM3": ["embedded", "device"],
            "OTHER": ["other", "misc"],
        }

    def test_default_platform_keywords_empty(self):
        """Test that default PLATFORM_KEYWORDS is empty (no hard-coded customer data)."""
        default_parser = PlatformCommandParser()
        assert default_parser.PLATFORM_KEYWORDS == {}
        assert isinstance(default_parser.PLATFORM_KEYWORDS, dict)

    def test_platform_keywords_structure(self):
        """Test PLATFORM_KEYWORDS has expected structure after configuration."""
        # Test that we have configurable platform mappings
        assert isinstance(self.parser.PLATFORM_KEYWORDS, dict)
        assert len(self.parser.PLATFORM_KEYWORDS) > 0

        # Each platform should have a list of keywords
        for platform, keywords in self.parser.PLATFORM_KEYWORDS.items():
            assert isinstance(platform, str)
            assert isinstance(keywords, list)
            assert len(keywords) > 0

    def test_platform_keywords_content(self):
        """Test platform keywords contain expected values."""
        # Test that platform keywords are configurable and not hardcoded
        # This allows users to define their own platform mappings
        for keywords in self.parser.PLATFORM_KEYWORDS.values():
            assert isinstance(keywords, list)
            assert len(keywords) > 0
            # All keywords should be lowercase for consistent matching
            for keyword in keywords:
                assert isinstance(keyword, str)
                assert keyword == keyword.lower()

    def test_parse_platform_commands_empty_string(self):
        """Test parsing empty test data."""
        result = self.parser.parse_platform_commands("")

        # Should return empty lists for all platforms
        for platform_commands in result.values():
            assert platform_commands == []

    def test_parse_platform_commands_whitespace_only(self):
        """Test parsing whitespace-only test data."""
        test_data = "   \n\t  \n   "
        result = self.parser.parse_platform_commands(test_data)

        # Should return empty lists for all platforms
        for platform_commands in result.values():
            assert platform_commands == []

    def test_parse_platform_commands_single_platform_colon(self):
        """Test parsing single platform with colon separator."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"{first_keyword.upper()}: test command"
        result = self.parser.parse_platform_commands(test_data)

        # Should detect the platform and extract the command
        assert result[first_platform] == ["test command"]

        # Other platforms should be empty
        for platform, commands in result.items():
            if platform != first_platform:
                assert commands == []

    def test_parse_platform_commands_single_platform_space(self):
        """Test parsing single platform with space separator."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"{first_keyword.upper()} test command"
        result = self.parser.parse_platform_commands(test_data)

        # Should detect the platform and extract the command
        assert result[first_platform] == ["test command"]

    def test_parse_platform_commands_case_insensitive(self):
        """Test parsing with case-insensitive platform keywords."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"{first_keyword.lower()}: test command"
        result = self.parser.parse_platform_commands(test_data)

        # Should detect the platform regardless of case
        assert result[first_platform] == ["test command"]

    def test_parse_platform_commands_with_whitespace_around_commands(self):
        """Test parsing with extra whitespace around commands."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"{first_keyword.upper()}:    test command   "
        result = self.parser.parse_platform_commands(test_data)

        # Should trim whitespace around the command
        assert result[first_platform] == ["test command"]

    def test_parse_platform_commands_multiline_commands(self):
        """Test parsing multiline commands for same platform."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"""{first_keyword.upper()}: first command
    second command
    third command"""
        result = self.parser.parse_platform_commands(test_data)

        # Should group all commands under the same platform
        expected_commands = ["first command", "second command", "third command"]
        assert result[first_platform] == expected_commands

    def test_parse_platform_commands_empty_lines(self):
        """Test parsing with empty lines between commands."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"""{first_keyword.upper()}: first command

second command

third command"""
        result = self.parser.parse_platform_commands(test_data)

        # Should handle empty lines correctly
        expected_commands = ["first command", "second command", "third command"]
        assert result[first_platform] == expected_commands

    def test_parse_platform_commands_complex_command_with_variables(self):
        """Test parsing complex commands with variables."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = (
            f"{first_keyword.upper()}: command with {{variable}} and {{another_var}}"
        )
        result = self.parser.parse_platform_commands(test_data)

        # Should preserve variables in commands
        assert result[first_platform] == ["command with {variable} and {another_var}"]

    def test_parse_platform_commands_duplicate_platforms(self):
        """Test parsing with duplicate platform specifications."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"""{first_keyword.upper()}: first command
{first_keyword.lower()}: second command
{first_keyword.upper()}: third command"""
        result = self.parser.parse_platform_commands(test_data)

        # Should accumulate all commands for the same platform
        expected_commands = ["first command", "second command", "third command"]
        assert result[first_platform] == expected_commands

    def test_parse_platform_commands_unrecognized_platforms(self):
        """Test parsing with unrecognized platform keywords."""
        test_data = """UNKNOWN_PLATFORM: some command
INVALID_PLATFORM: another command"""
        result = self.parser.parse_platform_commands(test_data)

        # Should ignore unrecognized platforms
        for platform_commands in result.values():
            assert platform_commands == []

    def test_parse_platform_commands_no_platform_specified(self):
        """Test parsing with no platform specified."""
        test_data = """random command without platform
another random line"""
        result = self.parser.parse_platform_commands(test_data)

        # Should not parse any commands without platform indicators
        for platform_commands in result.values():
            assert platform_commands == []

    def test_parse_platform_commands_special_characters(self):
        """Test parsing commands with special characters."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"{first_keyword.upper()}: command with | pipe and > redirect"
        result = self.parser.parse_platform_commands(test_data)

        # Should preserve special characters in commands
        assert result[first_platform] == ["command with | pipe and > redirect"]

    def test_parse_platform_commands_edge_case_colon_without_command(self):
        """Test parsing edge case with colon but no command."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"{first_keyword.upper()}:   "
        result = self.parser.parse_platform_commands(test_data)

        # Should handle empty command gracefully
        assert result[first_platform] == []

    def test_parse_platform_commands_continuation_without_platform(self):
        """Test parsing continuation lines without platform specification."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"""{first_keyword.upper()}: first command
    this should be included

    this should be ignored"""
        result = self.parser.parse_platform_commands(test_data)

        # Should include continuation lines only when they follow a platform
        expected_commands = ["first command", "this should be included"]
        assert result[first_platform] == expected_commands

    def test_parse_platform_commands_multiple_platforms_generic(self):
        """Test parsing multiple platforms using available platform keywords."""
        # Get first two available platforms for testing
        platforms = list(self.parser.PLATFORM_KEYWORDS.keys())[:2]

        if len(platforms) >= 2:
            platform1 = platforms[0]
            platform2 = platforms[1]
            keyword1 = self.parser.PLATFORM_KEYWORDS[platform1][0]
            keyword2 = self.parser.PLATFORM_KEYWORDS[platform2][0]

            test_data = f"""{keyword1.upper()}: command1
{keyword2.upper()}: command2"""
            result = self.parser.parse_platform_commands(test_data)

            # Should detect both platforms with their respective commands
            assert result[platform1] == ["command1"]
            assert result[platform2] == ["command2"]

    def test_parse_platform_commands_mixed_separators(self):
        """Test parsing with mixed colon and space separators."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"""{first_keyword.upper()}: command with colon
{first_keyword.lower()} command with space"""
        result = self.parser.parse_platform_commands(test_data)

        # Should handle both separators
        expected_commands = ["command with colon", "command with space"]
        assert result[first_platform] == expected_commands

    def test_parse_platform_commands_with_unicode(self):
        """Test parsing commands with unicode characters."""
        # Get first available platform for testing
        first_platform = next(iter(self.parser.PLATFORM_KEYWORDS.keys()))
        first_keyword = self.parser.PLATFORM_KEYWORDS[first_platform][0]

        test_data = f"{first_keyword.upper()}: command with café and ñiño"
        result = self.parser.parse_platform_commands(test_data)

        # Should preserve unicode characters
        assert result[first_platform] == ["command with café and ñiño"]

    def test_parse_platform_commands_generic_structure(self):
        """Test that the parser maintains the expected generic structure."""
        result = self.parser.parse_platform_commands("")

        # Should return a dictionary with all defined platforms
        assert isinstance(result, dict)
        assert set(result.keys()) == set(self.parser.PLATFORM_KEYWORDS.keys())

        # All values should be lists
        for platform_commands in result.values():
            assert isinstance(platform_commands, list)
