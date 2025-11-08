"""Unit tests for intent-driven parser functionality."""

from importobot.core.parsers import GenericTestFileParser


class TestIntentDrivenParser:
    """Tests for the intent-driven parser functionality."""

    def test_find_tests_in_standard_format(self) -> None:
        """Test finding tests in standard format."""
        parser = GenericTestFileParser()

        # Test with standard format
        data = {"tests": [{"name": "Test 1", "steps": []}]}
        tests = parser.find_tests(data)
        assert len(tests) == 1
        assert tests[0]["name"] == "Test 1"

    def test_find_tests_in_single_test_format(self) -> None:
        """Test finding tests in single test case format."""
        parser = GenericTestFileParser()

        # Test with single test case format
        data = {"name": "Single Test", "description": "A single test case", "steps": []}
        tests = parser.find_tests(data)
        assert len(tests) == 1
        assert tests[0]["name"] == "Single Test"

    def test_find_tests_in_zephyr_format(self) -> None:
        """Test finding tests in Zephyr format."""
        parser = GenericTestFileParser()

        # Test with Zephyr-style format
        data = {
            "name": "Zephyr Test",
            "testScript": {
                "type": "STEP_BY_STEP",
                "steps": [{"action": "Do something"}],
            },
        }
        tests = parser.find_tests(data)
        assert len(tests) == 1
        assert tests[0]["name"] == "Zephyr Test"
        assert len(tests[0]["testScript"]["steps"]) == 1

    def test_find_steps_in_standard_format(self) -> None:
        """Test finding steps in standard format."""
        parser = GenericTestFileParser()

        test_data = {
            "name": "Test Case",
            "steps": [
                {"action": "Step 1", "expectedResult": "Result 1"},
                {"action": "Step 2", "expectedResult": "Result 2"},
            ],
        }

        steps = parser.find_steps(test_data)
        assert len(steps) == 2
        assert steps[0]["action"] == "Step 1"
        assert steps[1]["action"] == "Step 2"

    def test_find_steps_in_zephyr_format(self) -> None:
        """Test finding steps in Zephyr format."""
        parser = GenericTestFileParser()

        test_data = {
            "name": "Zephyr Test",
            "testScript": {
                "type": "STEP_BY_STEP",
                "steps": [
                    {"step": "Step 1", "expectedResult": "Result 1"},
                    {"step": "Step 2", "expectedResult": "Result 2"},
                ],
            },
        }

        steps = parser.find_steps(test_data)
        assert len(steps) == 2
        assert steps[0]["step"] == "Step 1"
        assert steps[1]["step"] == "Step 2"

    def test_find_steps_in_nested_structure(self) -> None:
        """Test finding steps in nested structures."""
        parser = GenericTestFileParser()

        test_data = {
            "name": "Nested Test",
            "testCase": {
                "steps": [
                    {"description": "Nested step 1"},
                    {"description": "Nested step 2"},
                ]
            },
        }

        steps = parser.find_steps(test_data)
        assert len(steps) == 2
        assert steps[0]["description"] == "Nested step 1"
        assert steps[1]["description"] == "Nested step 2"

    def test_find_tests_in_complex_structure(self) -> None:
        """Test finding tests in complex nested structures."""
        parser = GenericTestFileParser()

        data = {
            "projectInfo": {"name": "Project Name"},
            "testCases": [
                {
                    "name": "Complex Test 1",
                    "description": "First complex test",
                    "steps": [{"action": "Action 1"}],
                },
                {"name": "Complex Test 2", "steps": [{"action": "Action 2"}]},
            ],
        }

        tests = parser.find_tests(data)
        assert len(tests) == 2
        assert tests[0]["name"] == "Complex Test 1"
        assert tests[1]["name"] == "Complex Test 2"
