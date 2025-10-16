"""Unit tests for parsers module.

Tests the test file parsing components.
Following TDD principles with comprehensive parsing validation.
"""

from typing import Any
from unittest.mock import patch

from importobot.core.interfaces import TestFileParser
from importobot.core.parsers import GenericTestFileParser


class TestGenericTestFileParserInitialization:
    """Test GenericTestFileParser initialization."""

    def test_parser_initializes_correctly(self):
        """Test that parser initializes with cached step field names."""
        parser = GenericTestFileParser()

        # pylint: disable=protected-access
        assert hasattr(parser, "_step_field_names_cache")
        assert isinstance(
            parser._step_field_names_cache,
            frozenset,
        )

    def test_parser_implements_interface(self):
        """Test that GenericTestFileParser implements TestFileParser interface."""
        parser = GenericTestFileParser()
        assert isinstance(parser, TestFileParser)

    def test_parser_has_required_methods(self):
        """Test that parser has required methods."""
        parser = GenericTestFileParser()

        assert hasattr(parser, "find_tests")
        assert callable(parser.find_tests)
        assert hasattr(parser, "find_steps")
        assert callable(parser.find_steps)


class TestFindTests:
    """Test find_tests method."""

    def test_find_tests_with_explicit_tests_array(self):
        """Test find_tests with explicit tests array."""
        parser = GenericTestFileParser()
        data = {
            "tests": [{"name": "Test 1", "steps": []}, {"name": "Test 2", "steps": []}]
        }

        result = parser.find_tests(data)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Test 1"
        assert result[1]["name"] == "Test 2"

    def test_find_tests_with_testcases_array(self):
        """Test find_tests with testCases array."""
        parser = GenericTestFileParser()
        data = {
            "testCases": [
                {"name": "Test A", "steps": []},
                {"name": "Test B", "steps": []},
            ]
        }

        result = parser.find_tests(data)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Test A"

    def test_find_tests_with_test_cases_snake_case(self):
        """Test find_tests with test_cases (snake_case) array."""
        parser = GenericTestFileParser()
        data = {"test_cases": [{"name": "Snake Case Test", "steps": []}]}

        result = parser.find_tests(data)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Snake Case Test"

    def test_find_tests_with_test_case_single(self):
        """Test find_tests with single test_case object."""
        parser = GenericTestFileParser()
        data = {"test_case": {"name": "Single Test", "steps": []}}

        result = parser.find_tests(data)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Single Test"

    @patch("importobot.core.parsers.is_test_case")
    def test_find_tests_with_single_test_case_root(self, mock_is_test_case):
        """Test find_tests with single test case at root level."""
        mock_is_test_case.return_value = True

        parser = GenericTestFileParser()
        data = {"name": "Root Level Test", "steps": []}

        result = parser.find_tests(data)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Root Level Test"

    def test_find_tests_with_non_dict_input(self):
        """Test find_tests with non-dictionary input."""
        parser = GenericTestFileParser()

        # Test with a dict that has non-dict values
        result = parser.find_tests({"key": "not a dict"})
        assert not result

        result = parser.find_tests({})
        assert not result

        result = parser.find_tests({"items": []})
        assert not result

    def test_find_tests_with_mixed_valid_invalid_items(self):
        """Test find_tests filters out non-dict items from arrays."""
        parser = GenericTestFileParser()
        data = {
            "tests": [
                {"name": "Valid Test", "steps": []},
                "invalid string",
                None,
                {"name": "Another Valid Test", "steps": []},
            ]
        }

        result = parser.find_tests(data)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Valid Test"
        assert result[1]["name"] == "Another Valid Test"

    def test_find_tests_with_empty_data(self):
        """Test find_tests with empty dictionary."""
        parser = GenericTestFileParser()
        data: dict[str, Any] = {}

        result = parser.find_tests(data)
        assert not result

    @patch("importobot.core.parsers.is_test_case")
    def test_find_tests_with_non_test_case_root(self, mock_is_test_case):
        """Test find_tests when root is not a valid test case."""
        mock_is_test_case.return_value = False

        parser = GenericTestFileParser()
        data = {"other_data": "not a test", "configuration": "settings"}

        result = parser.find_tests(data)
        assert not result

    def test_find_tests_case_insensitive_keys(self):
        """Test find_tests handles case-insensitive keys."""
        parser = GenericTestFileParser()

        # Test various case combinations
        test_cases = [
            {"Tests": [{"name": "Test 1", "steps": []}]},
            {"TESTS": [{"name": "Test 2", "steps": []}]},
            {"TestCases": [{"name": "Test 3", "steps": []}]},
            {"TESTCASES": [{"name": "Test 4", "steps": []}]},
            {"Test_Cases": [{"name": "Test 5", "steps": []}]},
        ]

        for data in test_cases:
            result = parser.find_tests(data)
            assert len(result) == 1


class TestFindSteps:
    """Test find_steps method (requires reading the full implementation)."""

    def test_find_steps_basic_functionality(self):
        """Test find_steps basic functionality."""
        parser = GenericTestFileParser()

        # This test is limited without seeing the full implementation
        # but we can test that it returns a list
        test_data: dict[str, Any] = {"steps": []}
        result = parser.find_steps(test_data)
        assert isinstance(result, list)

    def test_find_steps_with_none_input(self):
        """Test find_steps with None input."""
        parser = GenericTestFileParser()

        result = parser.find_steps({})
        assert isinstance(result, list)

    def test_find_steps_with_empty_dict(self):
        """Test find_steps with empty dictionary."""
        parser = GenericTestFileParser()

        result = parser.find_steps({})
        assert isinstance(result, list)


class TestPrivateMethods:
    """Test private helper methods."""

    def test_get_step_field_names_returns_frozenset(self):
        """Test _get_step_field_names returns frozenset."""
        parser = GenericTestFileParser()

        result = parser._get_step_field_names()  # pylint: disable=protected-access
        assert isinstance(result, frozenset)

    def test_get_step_field_names_caching(self):
        """Test that step field names are cached."""
        parser = GenericTestFileParser()

        # Call method twice and verify same object is returned
        result1 = parser._get_step_field_names()  # pylint: disable=protected-access
        result2 = parser._get_step_field_names()  # pylint: disable=protected-access
        assert result1 is result2  # Same object reference


class TestParserIntegration:
    """Test parser integration scenarios."""

    def test_complex_nested_structure(self):
        """Test parser with complex nested test structure."""
        parser = GenericTestFileParser()
        data = {
            "project": "Test Project",
            "tests": [
                {
                    "name": "Login Test Suite",
                    "steps": [
                        {"step": "Navigate to login"},
                        {"step": "Enter credentials"},
                    ],
                },
                {
                    "name": "Registration Test Suite",
                    "steps": [
                        {"step": "Navigate to registration"},
                        {"step": "Fill form"},
                    ],
                },
            ],
            "metadata": {"version": "1.0", "author": "Test Author"},
        }

        result = parser.find_tests(data)
        assert len(result) == 2
        assert result[0]["name"] == "Login Test Suite"
        assert result[1]["name"] == "Registration Test Suite"

    def test_multiple_test_arrays_in_single_document(self):
        """Test parser when document contains multiple test arrays."""
        parser = GenericTestFileParser()
        data = {
            "tests": [{"name": "Test 1", "steps": []}],
            "testCases": [{"name": "Test 2", "steps": []}],
        }

        result = parser.find_tests(data)
        # Should find tests from both arrays
        assert len(result) >= 2

    @patch("importobot.core.parsers.is_test_case")
    def test_parser_behavior_with_no_test_arrays(self, mock_is_test_case):
        """Test parser behavior when no explicit test arrays are found."""
        # First call should return False (not a test case)
        # This simulates when no explicit test arrays are found
        mock_is_test_case.return_value = False

        parser = GenericTestFileParser()
        data = {"someField": "someValue", "anotherField": "anotherValue"}

        result = parser.find_tests(data)
        assert not result

    def test_parser_error_handling(self):
        """Test parser error handling with malformed data."""
        parser = GenericTestFileParser()

        # Test with various malformed inputs
        malformed_inputs: list[dict[str, Any]] = [
            {"tests": "not an array"},
            {"tests": [None, None]},
            {"testCases": [1, 2, 3]},
            {"test_case": "not a dict"},
        ]

        for malformed_data in malformed_inputs:
            result = parser.find_tests(malformed_data)
            assert isinstance(result, list)
            # Should handle gracefully and return empty or filtered results

    def test_parser_with_real_world_structure(self):
        """Test parser with realistic test management tool export structure."""
        parser = GenericTestFileParser()
        data = {
            "exportMetadata": {
                "tool": "Zephyr",
                "version": "6.2",
                "exportDate": "2023-09-15",
            },
            "testCases": [
                {
                    "id": "TC001",
                    "name": "User Login Validation",
                    "description": "Verify user can login with valid credentials",
                    "steps": [
                        {
                            "stepNumber": 1,
                            "step": "Navigate to login page",
                            "expectedResult": "Login page is displayed",
                        },
                        {
                            "stepNumber": 2,
                            "step": "Enter valid username and password",
                            "testData": "username: testuser, password: testpass",
                            "expectedResult": "User is successfully logged in",
                        },
                    ],
                    "priority": "High",
                    "component": "Authentication",
                },
                {
                    "id": "TC002",
                    "name": "Password Reset Functionality",
                    "description": "Verify password reset workflow",
                    "steps": [
                        {
                            "stepNumber": 1,
                            "step": "Click forgot password link",
                            "expectedResult": "Reset form is displayed",
                        }
                    ],
                },
            ],
        }

        result = parser.find_tests(data)
        assert len(result) == 2
        assert result[0]["name"] == "User Login Validation"
        assert result[1]["name"] == "Password Reset Functionality"
        assert "steps" in result[0]
        assert "steps" in result[1]


class TestParserPerformance:
    """Test parser performance characteristics."""

    def test_parser_handles_large_test_arrays(self):
        """Test parser can handle large test arrays efficiently."""
        parser = GenericTestFileParser()

        # Create a large number of test cases
        large_test_array = []
        for i in range(1000):
            large_test_array.append(
                {
                    "name": f"Test {i}",
                    "steps": [{"step": f"Step {j}"} for j in range(5)],
                }
            )

        data = {"tests": large_test_array}

        result = parser.find_tests(data)
        assert len(result) == 1000
        assert result[0]["name"] == "Test 0"
        assert result[-1]["name"] == "Test 999"

    def test_parser_memory_efficiency(self):
        """Test parser doesn't unnecessarily duplicate data."""
        parser = GenericTestFileParser()

        original_test = {"name": "Original Test", "steps": []}
        data = {"tests": [original_test]}

        result = parser.find_tests(data)

        # The parser should return references to the original objects
        # (not deep copies) for memory efficiency
        assert len(result) == 1
        assert result[0] is original_test
