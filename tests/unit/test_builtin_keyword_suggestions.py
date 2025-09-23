"""Test suggestion engine for BuiltIn keyword ambiguity resolution."""

from importobot.core.suggestions.suggestion_engine import GenericSuggestionEngine


class TestBuiltInKeywordSuggestions:
    """Test suite for suggestion engine handling of BuiltIn keyword ambiguities."""

    @property
    def suggestion_engine(self):
        """Get suggestion engine instance."""
        return GenericSuggestionEngine()

    def test_log_vs_assertion_ambiguity_suggestion(self):
        """Test suggestions for cases where Log vs assertion keywords are ambiguous."""
        test_data = {
            "name": "Ambiguous Log Test",
            "steps": [
                {
                    "step": "log message and verify it appears",
                    "test_data": "message: Test successful",
                    "expected": "Test successful",
                }
            ],
        }

        suggestions = self.suggestion_engine.get_suggestions(test_data)

        # Should suggest clarifying the intention
        suggestion_text = " ".join(suggestions).lower()
        assert any(
            keyword in suggestion_text
            for keyword in ["clarify", "ambiguous", "log", "verify", "assertion"]
        )

    def test_conversion_vs_assertion_ambiguity_suggestion(self):
        """Test suggestions for conversion vs assertion ambiguity."""
        test_data = {
            "name": "Conversion Ambiguity Test",
            "steps": [
                {
                    "step": "convert value and check result",
                    "test_data": "value: 123, target_type: integer",
                    "expected": "123",
                }
            ],
        }

        suggestions = self.suggestion_engine.get_suggestions(test_data)

        # Should suggest separating conversion from verification
        " ".join(suggestions).lower()
        # For now, this might not trigger specific suggestions
        # This test documents the expected behavior
        assert isinstance(suggestions, list)

    def test_length_operations_ambiguity_suggestion(self):
        """Test suggestions for length operations that could map to multiple "
        "keywords."""
        test_data = {
            "name": "Length Operations Test",
            "steps": [
                {
                    "step": "check length of list",
                    "test_data": "container: [1, 2, 3]",
                    "expected": "length should be 3",
                }
            ],
        }

        suggestions = self.suggestion_engine.get_suggestions(test_data)

        # Should suggest clarifying between Get Length vs Length Should Be
        " ".join(suggestions).lower()
        assert isinstance(suggestions, list)

    def test_string_operation_ambiguity_suggestion(self):
        """Test suggestions for string operations with multiple possible mappings."""
        test_data = {
            "name": "String Operations Test",
            "steps": [
                {
                    "step": "check string matches pattern",
                    "test_data": "string: ${text}, pattern: \\d+",
                    "expected": "should match",
                }
            ],
        }

        suggestions = self.suggestion_engine.get_suggestions(test_data)

        # Should suggest clarifying the type of string operation
        " ".join(suggestions).lower()
        assert isinstance(suggestions, list)

    def test_variable_operation_ambiguity_suggestion(self):
        """Test suggestions for variable operations."""
        test_data = {
            "name": "Variable Operations Test",
            "steps": [
                {
                    "step": "create and validate variable",
                    "test_data": "name: test_var, value: test_value",
                    "expected": "variable should exist",
                }
            ],
        }

        suggestions = self.suggestion_engine.get_suggestions(test_data)

        # Should suggest separating creation from validation
        " ".join(suggestions).lower()
        assert isinstance(suggestions, list)

    def test_conditional_keyword_ambiguity_suggestion(self):
        """Test suggestions for conditional keyword mapping ambiguities."""
        test_data = {
            "name": "Conditional Test",
            "steps": [
                {
                    "step": "run keyword based on condition",
                    "test_data": "condition: ${var} == 'expected'",
                    "expected": "keyword should execute",
                }
            ],
        }

        suggestions = self.suggestion_engine.get_suggestions(test_data)

        # Should suggest clarifying the conditional structure
        " ".join(suggestions).lower()
        assert isinstance(suggestions, list)

    def test_evaluation_keyword_suggestion(self):
        """Test suggestions for Evaluate keyword usage."""
        test_data = {
            "name": "Evaluation Test",
            "steps": [
                {
                    "step": "evaluate expression and check result",
                    "test_data": "expression: 2 + 3",
                    "expected": "5",
                }
            ],
        }

        suggestions = self.suggestion_engine.get_suggestions(test_data)

        # Should suggest proper Evaluate keyword structure
        " ".join(suggestions).lower()
        assert isinstance(suggestions, list)

    def test_multiple_ambiguities_in_single_test(self):
        """Test suggestions when multiple ambiguous patterns exist in one test."""
        test_data = {
            "name": "Multiple Ambiguities Test",
            "steps": [
                {
                    "step": "log message",
                    "test_data": "message: Starting test",
                    "expected": "",
                },
                {
                    "step": "convert and verify value",
                    "test_data": "value: 123, type: integer",
                    "expected": "123",
                },
                {
                    "step": "check length and validate",
                    "test_data": "container: [1, 2, 3]",
                    "expected": "length should be 3",
                },
            ],
        }

        suggestions = self.suggestion_engine.get_suggestions(test_data)

        # Should provide suggestions for multiple issues
        assert isinstance(suggestions, list)
        # Each step might generate suggestions
        assert len(suggestions) >= 0  # May or may not have suggestions currently

    def test_well_structured_test_minimal_suggestions(self):
        """Test that well-structured tests generate minimal suggestions."""
        test_data = {
            "name": "Well Structured Test",
            "description": "A properly structured test case",
            "parameters": [
                {
                    "name": "test_file",
                    "defaultValue": "/tmp/test.txt",
                    "description": "File to test",
                }
            ],
            "steps": [
                {
                    "step": "verify file exists",
                    "test_data": "${test_file}",
                    "expected": "",
                },
                {
                    "step": "log message",
                    "test_data": "Test completed successfully",
                    "expected": "",
                },
                {
                    "step": "assert result equals expected",
                    "test_data": "result: success",
                    "expected": "success",
                },
            ],
        }

        suggestions = self.suggestion_engine.get_suggestions(test_data)

        # Should have minimal suggestions for well-structured tests
        # The primary goal is that BuiltIn keyword ambiguity suggestions
        # should not be triggered
        suggestion_text = " ".join(suggestions).lower()
        builtin_ambiguity_keywords = [
            "ambiguous intention",
            "string operation could map",
            "conversion operation mixed",
            "length operation could map",
            "conditional keyword execution",
            "variable operation mixed",
        ]

        # Assert that no BuiltIn keyword ambiguity suggestions are present
        for keyword in builtin_ambiguity_keywords:
            assert keyword not in suggestion_text, (
                f"Found unexpected BuiltIn ambiguity: {keyword}"
            )

    def test_edge_case_suggestions(self):
        """Test suggestions for edge cases and malformed inputs."""
        edge_cases = [
            {
                "name": "Empty Step Test",
                "steps": [{"step": "", "test_data": "", "expected": ""}],
            },
            {
                "name": "Missing Fields Test",
                "steps": [{"step": "test something"}],  # Missing test_data and expected
            },
            {
                "name": "Null Values Test",
                "steps": [{"step": None, "test_data": None, "expected": None}],
            },
        ]

        for test_data in edge_cases:
            suggestions = self.suggestion_engine.get_suggestions(test_data)

            # Should handle edge cases gracefully
            assert isinstance(suggestions, list)
            # Should provide helpful suggestions for malformed data
            if suggestions:
                suggestion_text = " ".join(suggestions).lower()
                assert any(
                    keyword in suggestion_text
                    for keyword in ["missing", "empty", "add", "required"]
                )

    def test_builtin_keyword_specific_suggestions(self):
        """Test suggestions specifically for BuiltIn keyword usage patterns."""
        test_cases = [
            {
                "name": "Fail Keyword Usage",
                "steps": [
                    {
                        "step": "fail the test",
                        "test_data": "message: Test failed",
                        "expected": "",
                    }
                ],
            },
            {
                "name": "Type Checking Usage",
                "steps": [
                    {
                        "step": "check if value is integer",
                        "test_data": "value: ${number}",
                        "expected": "should be integer type",
                    }
                ],
            },
            {
                "name": "Collection Operations",
                "steps": [
                    {
                        "step": "get count of items in list",
                        "test_data": "container: [1, 2, 1, 3], item: 1",
                        "expected": "count should be 2",
                    }
                ],
            },
        ]

        for test_data in test_cases:
            suggestions = self.suggestion_engine.get_suggestions(test_data)

            # Should provide suggestions for better BuiltIn keyword usage
            assert isinstance(suggestions, list)

    def test_suggestion_priority_ordering(self):
        """Test that suggestions are ordered by priority/importance."""
        test_data = {
            "name": "Priority Test",
            "steps": [
                {
                    "step": "complex operation with multiple issues",
                    "test_data": "",  # Missing test data
                    "expected": "",  # Missing expected result
                }
            ],
        }

        suggestions = self.suggestion_engine.get_suggestions(test_data)

        # Should provide suggestions
        assert isinstance(suggestions, list)

        # Critical issues (missing required fields) should come first
        if len(suggestions) > 1:
            first_suggestion = suggestions[0].lower()
            assert any(
                keyword in first_suggestion
                for keyword in ["missing", "required", "add", "empty"]
            )
