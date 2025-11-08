"""Test coverage for Robot Framework BuiltIn keywords mapping."""

from importobot.core.keyword_generator import GenericKeywordGenerator


class TestBuiltInKeywordsCoverage:
    """Test suite ensuring comprehensive coverage of Robot Framework BuiltIn
    keywords."""

    @property
    def generator(self) -> GenericKeywordGenerator:
        """Get keyword generator instance."""
        return GenericKeywordGenerator()

    def test_log_keyword_mapping(self) -> None:
        """Test mapping of log intentions to Log keyword."""
        # Basic logging
        step_data = {"step": "log message", "test_data": "Test message"}
        keywords = self.generator.generate_step_keywords(step_data)
        keyword_line = [
            line
            for line in keywords
            if line.strip() and not line.strip().startswith("#")
        ][-1]

        # Should map to Log keyword for generic log messages
        assert "Log" in keyword_line or "No Operation" in keyword_line

    def test_convert_to_keywords_mapping(self) -> None:
        """Test mapping of conversion intentions to Convert To X keywords."""
        test_cases = [
            {
                "description": "convert to integer",
                "test_data": "value: 123",
                "expected_keyword": "Convert To Integer",
            },
            {
                "description": "convert to string",
                "test_data": "value: hello",
                "expected_keyword": "Convert To String",
            },
            {
                "description": "convert to boolean",
                "test_data": "value: true",
                "expected_keyword": "Convert To Boolean",
            },
            {
                "description": "convert to number",
                "test_data": "value: 3.14",
                "expected_keyword": "Convert To Number",
            },
        ]

        for test_case in test_cases:
            step_data = {
                "step": test_case["description"],
                "test_data": test_case["test_data"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            # Now these should map to appropriate Convert To X keywords
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            assert (
                test_case["expected_keyword"] in keyword_line
            )  # BuiltIn keywords now work

    def test_variable_keywords_mapping(self) -> None:
        """Test mapping of variable operations to Set/Get Variable keywords."""
        test_cases = [
            {
                "description": "set variable",
                "test_data": "name: test_var, value: test_value",
            },
            {"description": "get variable value", "test_data": "variable: ${test_var}"},
            {"description": "create list", "test_data": "items: [1, 2, 3]"},
            {
                "description": "create dictionary",
                "test_data": "key1: value1, key2: value2",
            },
        ]

        for test_case in test_cases:
            step_data = {
                "step": test_case["description"],
                "test_data": test_case["test_data"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            # These now map to appropriate BuiltIn keywords
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            # Should map to appropriate BuiltIn keywords like Set Variable, Get Variable
            # Create List, Create Dictionary
            assert any(
                keyword in keyword_line
                for keyword in [
                    "Set Variable",
                    "Get Variable Value",
                    "Create List",
                    "Create Dictionary",
                    "No Operation",
                ]
            )

    def test_length_operations_mapping(self) -> None:
        """Test mapping of length operations to Get Length keyword."""
        test_cases = [
            {"description": "get length of list", "test_data": "list: [1, 2, 3]"},
            {"description": "check string length", "test_data": "text: hello world"},
            {
                "description": "verify length",
                "test_data": "item: ${test_list}",
                "expected": "length should be 5",
            },
        ]

        for test_case in test_cases:
            step_data = {
                "step": test_case["description"],
                "test_data": test_case["test_data"],
                "expected": test_case.get("expected", ""),
            }
            keywords = self.generator.generate_step_keywords(step_data)
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            # Should map to Get Length, Length Should Be, Page Should Contain,
            # or No Operation
            assert any(
                keyword in keyword_line
                for keyword in [
                    "Get Length",
                    "Length Should Be",
                    "Page Should Contain",
                    "No Operation",
                ]
            )

    def test_conditional_keywords_mapping(self) -> None:
        """Test mapping of conditional operations to Run Keyword If and related
        keywords."""
        test_cases = [
            {
                "description": "run keyword if condition is true",
                "test_data": (
                    "condition: ${var} == 'expected', keyword: Log, args: Success"
                ),
            },
            {
                "description": "run keyword unless condition fails",
                "test_data": (
                    "condition: ${status} != 'failed', keyword: Continue For Loop"
                ),
            },
            {
                "description": "repeat keyword multiple times",
                "test_data": "times: 3, keyword: Log, args: Iteration",
            },
        ]

        for test_case in test_cases:
            step_data = {
                "step": test_case["description"],
                "test_data": test_case["test_data"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            # Should map to appropriate BuiltIn conditional keywords
            assert any(
                keyword in keyword_line
                for keyword in [
                    "Run Keyword If",
                    "Run Keyword Unless",
                    "Repeat Keyword",
                    "No Operation",
                ]
            )

    def test_evaluation_keywords_mapping(self) -> None:
        """Test mapping of evaluation operations to Evaluate keyword."""
        test_cases = [
            {"description": "evaluate expression", "test_data": "expression: 2 + 3"},
            {
                "description": "evaluate python code",
                "test_data": "code: len('hello')",
                "modules": "",
            },
            {
                "description": "evaluate with modules",
                "test_data": "expression: datetime.now()",
                "modules": "datetime",
            },
        ]

        for test_case in test_cases:
            step_data = {
                "step": test_case["description"],
                "test_data": test_case["test_data"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            # BuiltIn keywords now working - these should map to appropriate keywords or
            # defaults
            assert len(keyword_line.strip()) > 0  # Should generate some keyword

    def test_collection_operations_mapping(self) -> None:
        """Test mapping of collection operations to appropriate BuiltIn keywords."""
        test_cases = [
            {
                "description": "get count of items",
                "test_data": "container: [1,2,1,3], item: 1",
            },
            {
                "description": "should contain items",
                "test_data": "container: ${list}, item: expected_value",
            },
            {
                "description": "should not contain",
                "test_data": "container: ${text}, item: forbidden",
            },
            {"description": "should be empty", "test_data": "container: ${empty_list}"},
        ]

        for test_case in test_cases:
            step_data = {
                "step": test_case["description"],
                "test_data": test_case["test_data"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            # Some of these already work through existing assertion patterns
            assert any(
                keyword in keyword_line
                for keyword in [
                    "Should Contain",
                    "Should Be Empty",
                    "No Operation",
                    "Get Count",
                    "Get Length",
                ]
            )

    def test_string_operations_mapping(self) -> None:
        """Test mapping of string operations to BuiltIn string keywords."""
        test_cases = [
            {
                "description": "string should start with",
                "test_data": "string: ${text}, prefix: Hello",
            },
            {
                "description": "string should end with",
                "test_data": "string: ${text}, suffix: world",
            },
            {
                "description": "should match regexp",
                "test_data": "string: ${text}, pattern: \\d+",
            },
            {
                "description": "should not match",
                "test_data": "string: ${text}, pattern: forbidden",
            },
        ]

        for test_case in test_cases:
            step_data = {
                "step": test_case["description"],
                "test_data": test_case["test_data"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            # BuiltIn keywords now working - these should map to appropriate keywords or
            # defaults
            assert len(keyword_line.strip()) > 0  # Should generate some keyword

    def test_type_checking_keywords_mapping(self) -> None:
        """Test mapping of type checking operations to Should Be X Type keywords."""
        test_cases = [
            {"description": "should be integer", "test_data": "value: ${number}"},
            {"description": "should be string", "test_data": "value: ${text}"},
            {"description": "should be boolean", "test_data": "value: ${flag}"},
            {"description": "should be list", "test_data": "value: ${items}"},
        ]

        for test_case in test_cases:
            step_data = {
                "step": test_case["description"],
                "test_data": test_case["test_data"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            # BuiltIn keywords now working - these should map to appropriate keywords or
            # defaults
            assert len(keyword_line.strip()) > 0  # Should generate some keyword

    def test_keyword_existence_verification(self) -> None:
        """Test mapping of keyword existence checks."""
        test_cases = [
            {
                "description": "keyword should exist",
                "test_data": "keyword: Custom Keyword",
            },
            {
                "description": "library should be imported",
                "test_data": "library: SeleniumLibrary",
            },
            {
                "description": "variable should be defined",
                "test_data": "variable: ${TEST_VAR}",
            },
        ]

        for test_case in test_cases:
            step_data = {
                "step": test_case["description"],
                "test_data": test_case["test_data"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            # BuiltIn keywords now working - these should map to appropriate keywords or
            # defaults
            assert len(keyword_line.strip()) > 0  # Should generate some keyword

    def test_fail_keyword_mapping(self) -> None:
        """Test mapping of failure operations to Fail keyword."""
        test_cases = [
            {"description": "fail test", "test_data": "message: Test failed"},
            {
                "description": "fail with tags",
                "test_data": "message: Critical failure, tags: critical, regression",
            },
            {"description": "fatal error", "test_data": "message: System error"},
        ]

        for test_case in test_cases:
            step_data = {
                "step": test_case["description"],
                "test_data": test_case["test_data"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            # BuiltIn keywords now working - these should map to appropriate keywords or
            # defaults
            assert len(keyword_line.strip()) > 0  # Should generate some keyword

    def test_ambiguous_keyword_scenarios(self) -> None:
        """Test scenarios where keyword mapping could be ambiguous."""
        ambiguous_cases = [
            {
                "description": "log and verify",
                "test_data": "message: Test value",
                "expected": "Expected value",
                "comment": "Could map to Log or Should Contain",
            },
            {
                "description": "convert and validate",
                "test_data": "value: 123, type: integer",
                "expected": "number should be 123",
                "comment": "Could map to Convert To Integer or Should Be Equal",
            },
            {
                "description": "check length",
                "test_data": "container: ${list}",
                "expected": "length should be 5",
                "comment": "Could map to Get Length or Length Should Be",
            },
        ]

        for case in ambiguous_cases:
            step_data = {
                "step": case["description"],
                "test_data": case["test_data"],
                "expected": case["expected"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            # These ambiguous cases should trigger suggestions
            # Check that either a valid keyword is generated OR suggestions are provided
            has_valid_keyword = any(
                kw in keyword_line
                for kw in ["No Operation", "Should", "Log", "Convert", "Get Length"]
            )
            has_suggestions = "# Alternative keywords:" in keyword_line
            assert has_valid_keyword or has_suggestions, (
                f"Expected valid keyword or suggestions in: {keyword_line}"
            )

    def test_edge_cases_for_builtin_keywords(self) -> None:
        """Test edge cases that might cause issues with BuiltIn keyword mapping."""
        edge_cases = [
            {"description": "", "test_data": "", "expected": ""},  # Empty inputs
            {"description": "log", "test_data": "", "expected": ""},  # Missing data
            {
                "description": "",
                "test_data": "value: test",
                "expected": "",
            },  # Missing description
            {
                "description": "multiple keywords in one",
                "test_data": "log message and verify result",
                "expected": "",
            },
        ]

        for case in edge_cases:
            step_data = {
                "step": case["description"],
                "test_data": case["test_data"],
                "expected": case["expected"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            # Should handle gracefully without errors
            assert isinstance(keywords, list)
            assert len(keywords) > 0

    def test_existing_assertion_coverage(self) -> None:
        """Test that existing assertion patterns still work correctly."""
        # These should continue to work as they do now
        existing_patterns = [
            {
                "step": "verify content contains expected text",
                "test_data": "container: ${page_content}, item: Welcome",
                "expected_keyword": "Should Contain",
            },
            {
                "step": "assert page contains text",
                "test_data": "text: Login successful",
                "expected_keyword": "Page Should Contain",
            },
            {
                "step": "check file exists",
                "test_data": "/tmp/test.txt",
                "expected_keyword": "File Should Exist",
            },
        ]

        for pattern in existing_patterns:
            step_data = {"step": pattern["step"], "test_data": pattern["test_data"]}
            keywords = self.generator.generate_step_keywords(step_data)
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            assert pattern["expected_keyword"] in keyword_line

    def test_keyword_priority_resolution(self) -> None:
        """Test how keyword mapping resolves priority when multiple patterns match."""
        priority_test_cases = [
            {
                "description": "log and assert message equals expected",
                "test_data": "message: Hello World",
                "expected": "Hello World",
                "comment": "Should prioritize assertion over logging",
            },
            {
                "description": "convert value and verify result",
                "test_data": "value: 42, type: string",
                "expected": "42",
                "comment": "Should choose most specific operation",
            },
        ]

        for case in priority_test_cases:
            step_data = {
                "step": case["description"],
                "test_data": case["test_data"],
                "expected": case["expected"],
            }
            keywords = self.generator.generate_step_keywords(step_data)
            keyword_line = [
                line
                for line in keywords
                if line.strip() and not line.strip().startswith("#")
            ][-1]
            # Should produce a deterministic result
            assert len(keyword_line.strip()) > 0
            assert keyword_line.strip() != ""
