"""Comprehensive TDD tests for ZephyrPreconditionAnalyzer."""

from importobot.core.zephyr_parsers import ZephyrPreconditionAnalyzer


# pylint: disable=too-many-public-methods
class TestZephyrPreconditionAnalyzer:
    """Test ZephyrPreconditionAnalyzer class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reinitialize for each test to ensure clean state
        self.analyzer = ZephyrPreconditionAnalyzer()

    def test_standard_preconditions_structure(self):
        """Test STANDARD_PRECONDITIONS contains expected values."""
        expected_preconditions = [
            "YJ Installed",
            "Communication Prepared",
            "Socket(s) Open",
            "Agent Stamped",
            "Agent Deployed",
            "CLI Connected to Active Agent",
        ]

        assert expected_preconditions == self.analyzer.STANDARD_PRECONDITIONS

    def test_analyze_preconditions_empty_string(self):
        """Test analyzing empty precondition text."""
        result = self.analyzer.analyze_preconditions("")
        assert not result

    def test_analyze_preconditions_whitespace_only(self):
        """Test analyzing whitespace-only precondition text."""
        test_data = "   \n\t  \n   "
        result = self.analyzer.analyze_preconditions(test_data)
        assert not result

    def test_analyze_preconditions_single_line(self):
        """Test analyzing single line precondition."""
        test_data = "System should be running"
        result = self.analyzer.analyze_preconditions(test_data)

        expected = [{"description": "System should be running"}]
        assert result == expected

    def test_analyze_preconditions_numbered_list(self):
        """Test analyzing numbered list preconditions."""
        test_data = """1. First precondition step
2. Second precondition step
3. Third precondition step"""

        result = self.analyzer.analyze_preconditions(test_data)

        expected = [
            {"description": "First precondition step"},
            {"description": "Second precondition step"},
            {"description": "Third precondition step"},
        ]
        assert result == expected

    def test_analyze_preconditions_numbered_with_parentheses(self):
        """Test analyzing numbered list with parentheses."""
        test_data = """1) First precondition step
2) Second precondition step
3) Third precondition step"""

        result = self.analyzer.analyze_preconditions(test_data)

        expected = [
            {"description": "First precondition step"},
            {"description": "Second precondition step"},
            {"description": "Third precondition step"},
        ]
        assert result == expected

    def test_analyze_preconditions_bulleted_list(self):
        """Test analyzing bulleted list preconditions."""
        test_data = """- First precondition step
- Second precondition step
- Third precondition step"""

        result = self.analyzer.analyze_preconditions(test_data)

        expected = [
            {"description": "First precondition step"},
            {"description": "Second precondition step"},
            {"description": "Third precondition step"},
        ]
        assert result == expected

    def test_analyze_preconditions_asterisk_bullets(self):
        """Test analyzing asterisk-bulleted list preconditions."""
        test_data = """* First precondition step
* Second precondition step
* Third precondition step"""

        result = self.analyzer.analyze_preconditions(test_data)

        expected = [
            {"description": "First precondition step"},
            {"description": "Second precondition step"},
            {"description": "Third precondition step"},
        ]
        assert result == expected

    def test_analyze_preconditions_mixed_formatting(self):
        """Test analyzing mixed formatting preconditions."""
        test_data = """1. First numbered step
- First bulleted step
2. Second numbered step
* Second bulleted step"""

        result = self.analyzer.analyze_preconditions(test_data)

        expected = [
            {"description": "First numbered step"},
            {"description": "First bulleted step"},
            {"description": "Second numbered step"},
            {"description": "Second bulleted step"},
        ]
        assert result == expected

    def test_analyze_preconditions_multiline_descriptions(self):
        """Test analyzing preconditions with multiline descriptions."""
        test_data = """1. First precondition step with
   additional description on next line
2. Second precondition step

3. Third precondition step with
    multiple lines of description"""

        result = self.analyzer.analyze_preconditions(test_data)

        expected = [
            {
                "description": (
                    "First precondition step with additional description on next line"
                )
            },
            {"description": "Second precondition step"},
            {
                "description": (
                    "Third precondition step with multiple lines of description"
                )
            },
        ]
        assert result == expected

    def test_analyze_preconditions_with_empty_lines(self):
        """Test analyzing preconditions with empty lines."""
        test_data = """1. First precondition step

2. Second precondition step

3. Third precondition step"""

        result = self.analyzer.analyze_preconditions(test_data)

        expected = [
            {"description": "First precondition step"},
            {"description": "Second precondition step"},
            {"description": "Third precondition step"},
        ]
        assert result == expected

    def test_analyze_preconditions_unformatted_text(self):
        """Test analyzing unformatted precondition text."""
        test_data = """This is a simple precondition without any formatting.
It contains multiple lines but no numbering or bullets.
Each line should be treated as a continuation."""

        result = self.analyzer.analyze_preconditions(test_data)

        expected = [
            {
                "description": (
                    "This is a simple precondition without any formatting. "
                    "Each line should be treated as a continuation."
                )
            }
        ]
        assert result == expected

    def test_analyze_preconditions_complex_formatting(self):
        """Test analyzing complex precondition formatting."""
        test_data = """
        1. System Setup:
           - Database should be running
           - All services should be started

        2. User Preparation:
           * Test user should be created
           * Permissions should be assigned

        3. Environment Configuration:
        Ensure all environment variables are set correctly
        """

        result = self.analyzer.analyze_preconditions(test_data)

        # Should handle complex nested formatting
        assert len(result) >= 3
        assert any("System Setup" in step["description"] for step in result)
        assert any("User Preparation" in step["description"] for step in result)
        assert any(
            "Environment Configuration" in step["description"] for step in result
        )

    def test_analyze_preconditions_with_special_characters(self):
        """Test analyzing preconditions with special characters."""
        test_data = """1. Ensure configuration file exists at /etc/app/config.ini
2. Set environment variable: APP_HOME="/opt/app"
3. Verify database connection string: "Server=localhost;Database=test" """

        result = self.analyzer.analyze_preconditions(test_data)

        expected = [
            {"description": "Ensure configuration file exists at /etc/app/config.ini"},
            {"description": 'Set environment variable: APP_HOME="/opt/app"'},
            {
                "description": (
                    "Verify database connection string: "
                    '"Server=localhost;Database=test"'
                )
            },
        ]
        assert result == expected

    def test_analyze_preconditions_with_unicode(self):
        """Test analyzing preconditions with unicode characters."""
        test_data = """1. El sistema debe estar configurado correctamente
2. La base de datos debe estar funcionando
3. Verificar la conexión con café y ñiño"""

        result = self.analyzer.analyze_preconditions(test_data)

        expected = [
            {"description": "El sistema debe estar configurado correctamente"},
            {"description": "La base de datos debe estar funcionando"},
            {"description": "Verificar la conexión con café y ñiño"},
        ]
        assert result == expected

    def test_detect_hyperlinked_test_cases_empty(self):
        """Test detecting hyperlinked test cases in empty text."""
        result = self.analyzer.detect_hyperlinked_test_cases("")
        assert not result

    def test_detect_hyperlinked_test_cases_with_keys(self):
        """Test detecting test case keys in preconditions."""
        test_data = """See test case PROJ-123 for detailed setup.
Refer to AUTH-456 for authentication steps.
Test LINK-789 should be executed first."""

        result = self.analyzer.detect_hyperlinked_test_cases(test_data)

        expected = ["PROJ-123", "AUTH-456", "LINK-789"]
        assert sorted(result) == sorted(expected)

    def test_detect_hyperlinked_test_cases_with_quoted_names(self):
        """Test detecting quoted test case names."""
        test_data = """See "User Login Test" for authentication details.
Refer to "Database Connection Validation" for setup steps.
Execute "File Upload Functionality" first."""

        result = self.analyzer.detect_hyperlinked_test_cases(test_data)

        expected = [
            "User Login Test",
            "Database Connection Validation",
            "File Upload Functionality",
        ]
        assert sorted(result) == sorted(expected)

    def test_detect_hyperlinked_test_cases_mixed_format(self):
        """Test detecting mixed format test case references."""
        test_data = """Refer to PROJ-123 and "User Management Test".
See AUTH-456, "API Authentication Test", and DATA-789.
Execute "System Setup" first."""

        result = self.analyzer.detect_hyperlinked_test_cases(test_data)

        expected_keys = ["PROJ-123", "AUTH-456", "DATA-789"]
        expected_names = [
            "User Management Test",
            "API Authentication Test",
            "System Setup",
        ]
        expected = expected_keys + expected_names

        assert sorted(result) == sorted(expected)

    def test_detect_hyperlinked_test_cases_edge_cases(self):
        """Test edge cases in hyperlinked test case detection."""
        test_data = """No test case references here.
Just regular text with numbers like 123-456.
Not a valid key: PROJ123 (missing dash).
Valid: PROJ-123.
Quoted: "Test Case" with extra text after."""

        result = self.analyzer.detect_hyperlinked_test_cases(test_data)

        expected = ["PROJ-123", "Test Case"]
        assert sorted(result) == sorted(expected)

    def test_detect_hyperlinked_test_cases_with_special_characters(self):
        """Test detecting test cases with special characters around them."""
        test_data = """See (PROJ-123) for details.
Refer to [AUTH-456] in documentation.
Execute "Data-Test-001" (note: quotes handle special chars)."""

        result = self.analyzer.detect_hyperlinked_test_cases(test_data)

        expected = ["PROJ-123", "AUTH-456", "Data-Test-001"]
        assert sorted(result) == sorted(expected)

    def test_analyze_prestructures_return_format(self):
        """Test that analyze_preconditions returns expected format."""
        test_data = "1. Simple precondition"

        result = self.analyzer.analyze_preconditions(test_data)

        # Should return a list of dictionaries
        assert isinstance(result, list)
        assert len(result) == 1

        # Each item should be a dictionary with 'description' key
        assert isinstance(result[0], dict)
        assert "description" in result[0]
        assert isinstance(result[0]["description"], str)

    def test_detect_hyperlinked_test_cases_return_format(self):
        """Test that detect_hyperlinked_test_cases returns expected format."""
        test_data = "Refer to PROJ-123 and 'Test Case'"

        result = self.analyzer.detect_hyperlinked_test_cases(test_data)

        # Should return a list of strings
        assert isinstance(result, list)
        assert len(result) == 2

        # All items should be strings
        for item in result:
            assert isinstance(item, str)
            assert len(item) > 0

    def test_integration_with_real_world_example(self):
        """Test integration with real-world precondition example."""
        test_data = """
        1. Application Server Setup:
           - Tomcat should be running on port 8080
           - Database connection pool should be configured

        2. Test Data Preparation:
           * Test user TEST-001 should exist
           * Sample data should be loaded via PROJ-123

        3. Environment Verification:
        Refer to "System Health Check Test" for environment validation.
        Ensure all services are responding correctly.
        """

        # Analyze preconditions
        precondition_steps = self.analyzer.analyze_preconditions(test_data)

        # Should extract structured steps
        assert len(precondition_steps) >= 3
        assert all(
            isinstance(step, dict) and "description" in step
            for step in precondition_steps
        )

        # Detect hyperlinked test cases
        test_case_refs = self.analyzer.detect_hyperlinked_test_cases(test_data)

        # Should find both key and name references
        expected_refs = ["PROJ-123", "System Health Check Test"]
        assert sorted(test_case_refs) == sorted(expected_refs)

    def test_performance_large_precondition_text(self):
        """Test performance with large precondition text."""
        # Create a large precondition text
        large_text = "\n".join(
            [
                f"{i}. Large precondition step number {i} with detailed description"
                for i in range(1, 1000)
            ]
        )

        # Should handle large text efficiently
        result = self.analyzer.analyze_preconditions(large_text)
        assert len(result) == 999  # All steps should be parsed

        # Test case detection should also be efficient
        test_refs = self.analyzer.detect_hyperlinked_test_cases(
            large_text + "\nRefer to PROJ-123 for details."
        )
        assert "PROJ-123" in test_refs

    def test_edge_case_malformed_formatting(self):
        """Test handling of malformed precondition formatting."""
        test_data = """1. Valid step
Invalid line without numbering
2. Another valid step
3.Incomplete numbering (no space)
- Bullet without space after dash
* Proper bullet"""

        result = self.analyzer.analyze_preconditions(test_data)

        # Should handle malformed formatting gracefully
        assert len(result) >= 3  # At least the valid steps

        # Check that valid steps are captured
        step_descriptions = [step["description"] for step in result]
        assert any("Valid step" in desc for desc in step_descriptions)
        assert any("Another valid step" in desc for desc in step_descriptions)
        assert any("Proper bullet" in desc for desc in step_descriptions)
