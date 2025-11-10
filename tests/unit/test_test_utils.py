"""Unit tests for test utility functions."""

import pytest

from tests.utils import validate_test_script_structure


class TestValidateTestScriptStructure:
    """Tests for validate_test_script_structure helper function."""

    def test_validates_correct_structure(self) -> None:
        """Test validation of correctly structured test script."""
        test_script = {
            "type": "STEP_BY_STEP",
            "steps": [
                {"step": "First step", "testData": "data1"},
                {"step": "Second step", "testData": "data2"},
            ],
        }

        # Should not raise any assertion errors
        validate_test_script_structure(test_script)

    def test_validates_empty_steps_list(self) -> None:
        """Test that empty steps list fails validation."""
        test_script = {"type": "STEP_BY_STEP", "steps": []}

        with pytest.raises(AssertionError):
            validate_test_script_structure(test_script)

    def test_fails_on_missing_type(self) -> None:
        """Test validation failure when type field is missing."""
        test_script = {"steps": [{"step": "Test step"}]}

        with pytest.raises(AssertionError):
            validate_test_script_structure(test_script)

    def test_fails_on_wrong_type_value(self) -> None:
        """Test validation failure when type is not STEP_BY_STEP."""
        test_script = {"type": "WRONG_TYPE", "steps": [{"step": "Test step"}]}

        with pytest.raises(AssertionError):
            validate_test_script_structure(test_script)

    def test_fails_on_missing_steps(self) -> None:
        """Test validation failure when steps field is missing."""
        test_script = {"type": "STEP_BY_STEP"}

        with pytest.raises(AssertionError):
            validate_test_script_structure(test_script)

    def test_fails_on_steps_not_list(self) -> None:
        """Test validation failure when steps is not a list."""
        test_script = {"type": "STEP_BY_STEP", "steps": "not a list"}

        with pytest.raises(AssertionError):
            validate_test_script_structure(test_script)

    def test_fails_on_steps_none(self) -> None:
        """Test validation failure when steps is None."""
        test_script = {"type": "STEP_BY_STEP", "steps": None}

        with pytest.raises(AssertionError):
            validate_test_script_structure(test_script)

    def test_validates_with_multiple_steps(self) -> None:
        """Test validation with multiple steps of different formats."""
        test_script = {
            "type": "STEP_BY_STEP",
            "steps": [
                {
                    "step": "Login to system",
                    "testData": "Username: admin, Password: secret",
                    "expectedResult": "Successfully logged in",
                },
                {
                    "description": "Navigate to dashboard",  # Different field name
                    "data": "URL: /dashboard",
                },
                {"action": "Click button", "verification": "Button is clicked"},
            ],
        }

        # Should validate successfully regardless of step content structure
        validate_test_script_structure(test_script)

    def test_validates_with_nested_step_data(self) -> None:
        """Test validation with complex nested step data."""
        test_script = {
            "type": "STEP_BY_STEP",
            "steps": [
                {
                    "step": "Complex operation",
                    "testData": {
                        "inputs": ["value1", "value2"],
                        "config": {"option": "enabled"},
                    },
                    "expectedResult": {"status": "success", "code": 200},
                }
            ],
        }

        validate_test_script_structure(test_script)

    def test_handles_unicode_content(self) -> None:
        """Test validation with unicode content in steps."""
        test_script = {
            "type": "STEP_BY_STEP",
            "steps": [
                {
                    "step": "Test with unicode: ñáéíóú 中文 ",
                    "testData": "Data with special chars: ♠♣♥♦",
                }
            ],
        }

        validate_test_script_structure(test_script)

    def test_validates_large_steps_list(self) -> None:
        """Test validation with a large number of steps."""
        steps = [
            {"step": f"Step {i + 1}", "testData": f"Test data for step {i + 1}"}
            for i in range(100)
        ]

        test_script = {"type": "STEP_BY_STEP", "steps": steps}

        validate_test_script_structure(test_script)
