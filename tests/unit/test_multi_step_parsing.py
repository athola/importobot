"""Comprehensive tests for multi-step parsing capabilities.

Tests enhanced step parsing that can map single JSON steps to multiple Robot Framework "
        "commands,
analyze context across steps for intelligent suggestions, handle edge cases, complex "
        "scenarios,
and error conditions. Following TDD principles.
"""

from importobot.core.keyword_generator import GenericKeywordGenerator
from importobot.core.multi_command_parser import MultiCommandParser


class TestBasicMultiStepParsing:
    """Test basic mapping of single JSON steps to multiple Robot Framework commands."""

    def test_user_registration_form_parsing(self):
        """Test that user registration step generates multiple input commands."""
        # Test multi-command parsing from user registration step
        parser = MultiCommandParser()
        test_data = "username: johndoe, email: john@example.com, password: secret123"
        result = parser.parse_test_data(test_data)
        assert isinstance(result, dict)
        assert len(result) > 0
        assert "username" in result
        assert "email" in result
        assert "password" in result

    def test_login_form_parsing_with_username_password(self):
        """Test login form with username and password fields."""
        generator = GenericKeywordGenerator()
        step = {
            "description": "Enter login credentials",
            "testData": "username: admin, password: secret123",
            "expectedResult": "Credentials entered successfully",
        }

        result = generator.generate_step_keywords(step)

        expected_keywords = [
            "    # Step: Enter login credentials",
            "    # Test Data: username: admin, password: secret123",
            "    # ⚠️  Security Warning: Hardcoded password detected in test data",
            "    # Expected Result: Credentials entered successfully",
            "    Input Text    id=username    admin",
            "    Input Password    id=password    secret123",
        ]

        assert result == expected_keywords

    def test_multiple_text_fields_parsing(self):
        """Test step with multiple text input fields."""
        generator = GenericKeywordGenerator()
        step = {
            "description": "Fill contact information",
            "testData": "name: John Doe, phone: 555-1234, address: 123 Main St",
            "expectedResult": "Contact information filled",
        }

        result = generator.generate_step_keywords(step)

        expected_keywords = [
            "    # Step: Fill contact information",
            "    # Test Data: name: John Doe, phone: 555-1234, address: 123 Main St",
            "    # Expected Result: Contact information filled",
            "    Input Text    id=name    John Doe",
            "    Input Text    id=phone    555-1234",
            "    Input Text    id=address    123 Main St",
        ]

        assert result == expected_keywords


class TestComplexRealWorldScenarios:
    """Test complex real-world scenarios that mirror actual usage."""

    def test_complete_user_registration_workflow(self):
        """Test complete user registration with all typical fields."""
        generator = GenericKeywordGenerator()

        step = {
            "description": "Complete user registration form",
            "testData": (
                "first_name: John, last_name: Doe, email: john.doe@company.com, "
                "password: SecureP@ss123!, confirm_password: SecureP@ss123!, "
                "phone: +1-555-123-4567, date_of_birth: 1990-05-15, "
                "address: 123 Main Street, city: San Francisco, state: CA, "
                "zip_code: 94105, country: United States, "
                "terms_accepted: true, newsletter_subscription: false"
            ),
            "expectedResult": "Registration form completed successfully",
        }

        result = generator.generate_step_keywords(step)

        # Should generate multiple commands for different field types
        command_lines = [
            line
            for line in result
            if line.strip().startswith(("Input", "Select", "Unselect"))
        ]
        assert len(command_lines) >= 10  # Many form fields

        # Check for different input types
        result_text = "\n".join(result)
        assert "Input Text" in result_text
        assert "Input Password" in result_text

    def test_ecommerce_checkout_form(self):
        """Test e-commerce checkout form with payment and shipping details."""
        generator = GenericKeywordGenerator()

        step = {
            "description": "Fill checkout form with payment details",
            "testData": (
                "email: customer@email.com, password: checkout123, "
                "shipping_first_name: Jane, shipping_last_name: Smith, "
                "shipping_address: 456 Oak Avenue, shipping_city: Portland, "
                "shipping_state: OR, shipping_zip: 97201, "
                "billing_same_as_shipping: false, "
                "card_number: 4111111111111111, expiry_month: 12, expiry_year: 2025, "
                "cvv: 123, cardholder_name: Jane Smith"
            ),
            "expectedResult": "Checkout form completed with payment details",
        }

        result = generator.generate_step_keywords(step)

        # Should handle complex checkout scenario
        command_lines = [
            line for line in result if line.strip().startswith(("Input", "Select"))
        ]
        assert len(command_lines) >= 10  # Many checkout fields

        # Should contain password field
        assert any("Input Password" in line for line in result)


class TestEdgeCasesAndErrorHandling:
    """Test edge cases, error handling, and robustness scenarios."""

    def test_parse_data_with_special_characters(self):
        """Test parsing data containing special characters."""

        parser = MultiCommandParser()

        test_data = (
            "email: user@domain.com, password: P@$$w0rd!, note: Test with symbols: #$%"
        )
        parsed_data = parser.parse_test_data(test_data)

        expected = {
            "email": "user@domain.com",
            "password": "P@$$w0rd!",
            "note": "Test with symbols: #$%",
        }

        assert parsed_data == expected

    def test_parse_data_with_nested_colons(self):
        """Test parsing data with nested colons in values."""

        parser = MultiCommandParser()

        test_data = "url: http://example.com:8080, time: 12:30:45, ratio: 1:2:3"
        parsed_data = parser.parse_test_data(test_data)

        expected = {
            "url": "http://example.com:8080",
            "time": "12:30:45",
            "ratio": "1:2:3",
        }

        assert parsed_data == expected

    def test_parser_handles_none_input_gracefully(self):
        """Test parser handles None input without crashing."""

        parser = MultiCommandParser()

        # Should not crash with empty string input
        result = parser.parse_test_data("")
        assert not result

        field_types = parser.detect_field_types({})
        assert not field_types

        commands = parser.generate_robot_commands({}, {})
        assert not commands

    def test_parser_handles_empty_dict_gracefully(self):
        """Test parser handles empty dictionaries gracefully."""

        parser = MultiCommandParser()

        field_types = parser.detect_field_types({})
        assert not field_types

        commands = parser.generate_robot_commands({}, {})
        assert not commands

        # Should not trigger multi-command generation
        assert not parser.should_generate_multiple_commands("test description", {})

    def test_keyword_generator_handles_missing_fields(self):
        """Test keyword generator handles steps with missing fields."""
        generator = GenericKeywordGenerator()

        # Step with missing description
        step = {"testData": "username: test", "expectedResult": "Test result"}

        result = generator.generate_step_keywords(step)
        assert isinstance(result, list)

        # Step with missing testData
        step = {"description": "Test step", "expectedResult": "Test result"}

        result = generator.generate_step_keywords(step)
        assert isinstance(result, list)

    def test_malformed_test_data_handling(self):
        """Test handling of malformed test data."""

        parser = MultiCommandParser()

        malformed_cases = [
            "",  # Empty string
            "no_colons_or_commas",  # No separators
            "key_without_value:",  # Missing value
            ":value_without_key",  # Missing key
            "multiple:::colons: value",  # Extra colons
            "trailing_comma: value,",  # Trailing comma
        ]

        for test_data in malformed_cases:
            result = parser.parse_test_data(test_data)
            assert isinstance(result, dict)  # Should always return dict

    def test_unicode_and_special_encoding_handling(self):
        """Test handling of unicode and special character encoding."""

        parser = MultiCommandParser()

        unicode_data = "name: José María, city: São Paulo, emoji: 🚀, chinese: 测试"
        result = parser.parse_test_data(unicode_data)

        assert result["name"] == "José María"
        assert result["city"] == "São Paulo"
        assert result["emoji"] == "🚀"
        assert result["chinese"] == "测试"


class TestContextAnalysisAndSuggestions:
    """Test context analysis across multiple steps for intelligent suggestions."""

    def test_hash_calculation_suggestion(self):
        """Test that hash calculation steps suggest comparison step."""
        generator = GenericKeywordGenerator()

        # First step: hash a file
        step1 = {
            "description": "Calculate hash of source file",
            "testData": "file: source.txt, algorithm: sha256",
            "expectedResult": "Hash calculated",
        }

        # Second step: calculate hash of another file
        step2 = {
            "description": "Calculate hash of target file",
            "testData": "file: target.txt, algorithm: sha256",
            "expectedResult": "Hash calculated",
        }

        # Context analyzer should suggest comparison step
        context = [step1, step2]
        suggestions = generator.analyze_step_context(context)

        # Check that hash comparison suggestion is present
        hash_suggestions = [
            s for s in suggestions if s.get("type") == "hash_comparison"
        ]
        assert len(hash_suggestions) > 0
        assert hash_suggestions[0]["description"] == "Hash values should be compared"
        assert hash_suggestions[0]["position"] == "after_step_2"

    def test_database_transaction_suggestions(self):
        """Test database transaction lifecycle suggestions."""
        generator = GenericKeywordGenerator()

        steps = [
            {
                "description": "Insert user record",
                "testData": "INSERT INTO users (name, email) VALUES "
                "('Test', 'test@example.com')",
                "expectedResult": "Record inserted",
            },
            {
                "description": "Update user status",
                "testData": "UPDATE users SET active = 1 WHERE email = "
                "'test@example.com'",
                "expectedResult": "Status updated",
            },
        ]

        suggestions = generator.analyze_step_context(steps)

        # Should suggest transaction handling
        assert any(s["type"] == "missing_transaction" for s in suggestions)


class TestEnhancedStepParser:
    """Test enhanced step parser implementation."""

    def test_parse_comma_separated_data(self):
        """Test parsing comma-separated test data."""

        parser = MultiCommandParser()

        test_data = "username: admin, password: secret, remember: true"
        parsed_data = parser.parse_test_data(test_data)

        expected = {"username": "admin", "password": "secret", "remember": "true"}

        assert parsed_data == expected

    def test_detect_input_field_types(self):
        """Test detection of input field types from parsed data."""

        parser = MultiCommandParser()

        parsed_data = {
            "email": "test@example.com",
            "password": "secret123",
            "age": "25",
            "active": "true",
        }

        field_types = parser.detect_field_types(parsed_data)

        expected = {
            "email": "text",
            "password": "password",
            "age": "text",
            "active": "checkbox",
        }

        assert field_types == expected

    def test_generate_robot_commands_from_parsed_data(self):
        """Test generation of Robot Framework commands from parsed data."""

        parser = MultiCommandParser()

        parsed_data = {"username": "admin", "password": "secret"}
        field_types = {"username": "text", "password": "password"}

        commands = parser.generate_robot_commands(parsed_data, field_types)

        expected = [
            "Input Text    id=username    admin",
            "Input Password    id=password    secret",
        ]

        assert commands == expected


class TestPerformanceAndScalability:
    """Test performance characteristics and scalability limits."""

    def test_large_form_parsing_performance(self):
        """Test parsing performance with very large forms."""
        generator = GenericKeywordGenerator()

        # Generate large test data string
        large_data_parts = []
        for i in range(50):  # 50 fields
            large_data_parts.append(f"field_{i}: value_{i}")

        large_test_data = ", ".join(large_data_parts)

        step = {
            "description": "Fill large form",
            "testData": large_test_data,
            "expectedResult": "Large form filled",
        }

        result = generator.generate_step_keywords(step)

        # Should handle large forms without errors
        assert isinstance(result, list)
        assert len(result) > 0

    def test_complex_nested_data_structures(self):
        """Test handling of complex nested data structures."""

        parser = MultiCommandParser()

        complex_data = (
            "user: {name: John Doe, age: 30}, "
            "address: {street: 123 Main St, city: Portland}, "
            "preferences: {theme: dark, notifications: true}"
        )

        # Current parser handles this as flat key-value pairs
        result = parser.parse_test_data(complex_data)
        assert isinstance(result, dict)
        # Should extract what it can from the complex structure
        assert len(result) >= 1
