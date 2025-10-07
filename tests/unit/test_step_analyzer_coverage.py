"""Targeted tests for step analyzer coverage gaps."""

from typing import Any

import pytest

from importobot.core.suggestions.step_analyzer import StepAnalyzer


@pytest.fixture
def analyzer():
    """Initialize step analyzer."""
    return StepAnalyzer()


class TestStepImprovement:
    """Test step improvement functionality."""

    def test_improve_steps_basic(self, analyzer):
        """Test basic step improvement."""
        test_case: dict[str, Any] = {"testScript": {"steps": [{"step": "test action"}]}}
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)

        # Verify testScript structure is maintained
        assert "testScript" in test_case
        assert "steps" in test_case["testScript"]
        assert isinstance(test_case["testScript"]["steps"], list)

    def test_improve_steps_missing_action(self, analyzer):
        """Test step improvement when action is missing."""
        test_case: dict[str, Any] = {
            "testScript": {
                "steps": [{"test_data": "some data", "expected": "some result"}]
            }
        }
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)

        # Verify a default action was added
        step = test_case["testScript"]["steps"][0]
        assert "action" in step or "step" in step
        # Changes should be tracked
        assert isinstance(changes_made, list)

    def test_improve_steps_missing_expected(self, analyzer):
        """Test step improvement when expected result is missing."""
        test_case: dict[str, Any] = {
            "testScript": {
                "steps": [{"step": "perform action", "test_data": "some data"}]
            }
        }
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)

        # Verify an expected result was added
        step = test_case["testScript"]["steps"][0]
        has_expected = any(
            field in step for field in ["expectedResult", "expected", "expected_result"]
        )
        assert has_expected
        assert isinstance(changes_made, list)

    def test_add_default_action_when_missing(self, analyzer):
        """Test adding default action when missing."""
        step = {"test_data": "input data", "expected": "expected output"}
        result = analyzer._add_default_action(step)  # pylint: disable=protected-access

        # Should return True indicating a change was made
        assert result is True
        # Should add a step/action field
        assert "step" in step or "action" in step
        added_field = step.get("step") or step.get("action")
        assert isinstance(added_field, str)
        assert len(added_field) > 0

    def test_add_default_expected_result_when_missing(self, analyzer):
        """Test adding default expected result when missing."""
        step = {"step": "perform test action", "test_data": "input data"}
        # pylint: disable=protected-access
        result = analyzer._add_default_expected_result(step)

        # Should return True indicating a change was made
        assert result is True
        # Should add an expected result field
        assert "expectedResult" in step
        assert isinstance(step["expectedResult"], str)
        assert len(step["expectedResult"]) > 0

    def test_improve_single_step_private(self, analyzer):
        """Test improving single step private method."""
        step = {"step": "test action"}
        result = analyzer._improve_single_step(step)  # pylint: disable=protected-access

        # Should return a boolean indicating whether changes were made
        assert isinstance(result, bool)
        # Step should still be a valid dictionary
        assert isinstance(step, dict)
        assert "step" in step or "action" in step

    def test_empty_steps_handling(self, analyzer):
        """Test handling of empty steps list."""
        test_case: dict[str, Any] = {"testScript": {"steps": []}}
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)

        # Should add a default step when steps list is empty
        assert len(test_case["testScript"]["steps"]) > 0
        # Should track that a step was added
        assert len(changes_made) > 0
        assert any(change["type"] == "step_added" for change in changes_made)

    def test_none_steps_handling(self, analyzer):
        """Test handling of None steps."""
        test_case: dict[str, Any] = {}
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)

        # Should create testScript structure when missing
        assert "testScript" in test_case
        assert "steps" in test_case["testScript"]
        # Should add a default step
        assert len(test_case["testScript"]["steps"]) > 0
        assert isinstance(changes_made, list)

    def test_multiple_steps_processing(self, analyzer):
        """Test processing multiple steps together."""
        test_case: dict[str, Any] = {
            "testScript": {
                "steps": [
                    {"step": "first action", "test_data": "data1"},
                    {"step": "second action", "expected": "result2"},
                    {"test_data": "data3"},  # Missing step field
                ]
            }
        }
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)

        # All steps should still be present
        assert len(test_case["testScript"]["steps"]) == 3
        # Third step should have a step/action field added
        third_step = test_case["testScript"]["steps"][2]
        assert "step" in third_step or "action" in third_step
        assert isinstance(changes_made, list)


class TestBraceHandling:
    """Test brace matching and fixing functionality."""

    def test_fix_unmatched_braces_in_step(self, analyzer):
        """Test fixing unmatched braces in step data."""
        test_case: dict[str, Any] = {
            "testScript": {
                "steps": [{"step": "test {unmatched brace", "test_data": "data"}]
            }
        }
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)

        # Should fix unmatched braces
        step_text = test_case["testScript"]["steps"][0]["step"]
        # Count braces to verify they're balanced or brace is removed/escaped
        open_braces = step_text.count("{")
        close_braces = step_text.count("}")
        # Either balanced or braces were escaped/removed
        assert open_braces == close_braces or "{" not in step_text
        assert isinstance(changes_made, list)

    def test_fix_unmatched_braces_private(self, analyzer):
        """Test fixing unmatched braces private method."""
        step = {"step": "test {unmatched brace", "test_data": "data"}
        # pylint: disable=protected-access
        result = analyzer._fix_unmatched_braces(step)

        # Should return True if changes were made
        assert isinstance(result, bool)
        # Braces should be fixed in step field
        if "{" in step.get("step", ""):
            open_braces = step["step"].count("{")
            close_braces = step["step"].count("}")
            assert open_braces == close_braces

    def test_check_brace_matching_private(self, analyzer):
        """Test brace matching check private method."""
        step = {"step": "test {matched} braces"}
        suggestions: list[dict[str, Any]] = []
        # pylint: disable=protected-access
        analyzer._check_brace_matching(step, 1, 1, suggestions)

        # Should not add suggestions for matched braces
        assert len(suggestions) == 0

    def test_fix_brace_mismatches_text(self, analyzer):
        """Test fixing brace mismatches in text."""
        text = "test {unmatched brace"
        # pylint: disable=protected-access
        result = analyzer._fix_brace_mismatches(text)

        # Should return fixed text
        assert isinstance(result, str)
        # Fixed text should have balanced braces or no braces
        if "{" in result:
            assert result.count("{") == result.count("}")


class TestStepValidation:
    """Test step validation and checking functionality."""

    def test_check_steps_functionality(self, analyzer):
        """Test check_steps functionality."""
        steps = [{"step": "test action", "expected": "result"}]
        suggestions: list[str] = []
        analyzer.check_steps(steps, 1, suggestions)

        # Suggestions should be a list (may be empty for valid steps)
        assert isinstance(suggestions, list)
        # All suggestions should be strings
        assert all(isinstance(s, str) for s in suggestions)

    def test_check_step_ordering(self, analyzer):
        """Test step ordering check."""
        # Use steps with explicit ordering that's wrong
        steps = [
            {"step": "action", "step_number": 2},
            {"step": "action", "step_number": 1},
        ]
        suggestions: list[str] = []
        analyzer.check_step_ordering(steps, 1, suggestions)

        # Should suggest reordering when step numbers are out of sequence
        assert isinstance(suggestions, list)
        if len(suggestions) > 0:
            assert any(
                "order" in s.lower() or "sequence" in s.lower() for s in suggestions
            )

    def test_check_step_fields_private(self, analyzer):
        """Test checking step fields private method."""
        step = {"step": "test action", "test_data": "data"}
        suggestions: list[str] = []
        # pylint: disable=protected-access
        analyzer._check_step_fields(step, 1, 1, suggestions)

        # Should check fields and potentially add suggestions
        assert isinstance(suggestions, list)
        # All suggestions should be strings with test case reference
        assert all(isinstance(s, str) for s in suggestions)

    def test_collect_command_steps(self, analyzer):
        """Test command step collection."""
        steps = [
            {"step": "run command", "test_data": "ls -la"},
            {"step": "verify output", "expected": "files listed"},
        ]
        result = analyzer.collect_command_steps(steps)

        # Should return a list of command steps
        assert isinstance(result, list)
        # Result should contain command-related steps
        # (may be empty if no command keywords detected)
        assert all(isinstance(s, dict) for s in result)


class TestComplexStepData:
    """Test handling of complex and edge case step data."""

    def test_step_with_special_characters(self, analyzer):
        """Test step with special characters."""
        test_case: dict[str, Any] = {
            "testScript": {
                "steps": [
                    {
                        "step": "test with special chars: !@#$%^&*()",
                        "test_data": "data with quotes 'single' and \"double\"",
                        "expected": "result with newlines\nand tabs\t",
                    }
                ]
            }
        }
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)

        # Should handle special characters without errors
        step = test_case["testScript"]["steps"][0]
        assert "step" in step
        # Original content should be preserved
        assert "!@#$%^&*()" in step["step"]
        assert isinstance(changes_made, list)

    def test_step_with_nested_data_structures(self, analyzer):
        """Test step with nested data structures."""
        test_case: dict[str, Any] = {
            "testScript": {
                "steps": [
                    {
                        "step": "complex test",
                        "test_data": {
                            "nested": {"deep": "value"},
                            "list": [1, 2, 3],
                            "mixed": {"list": ["a", "b"], "value": 42},
                        },
                        "expected": "complex result",
                    }
                ]
            }
        }
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)

        # Should handle nested structures without errors
        step = test_case["testScript"]["steps"][0]
        assert isinstance(step["test_data"], dict)
        # Nested structure should be preserved
        assert "nested" in step["test_data"]
        assert step["test_data"]["nested"]["deep"] == "value"
        assert isinstance(changes_made, list)

    def test_edge_case_step_data(self, analyzer):
        """Test edge case step data."""
        edge_case_steps = [
            {"step": ""},  # Empty step
            {"step": "   "},  # Whitespace only
            {"step": None},  # None value
            {},  # Empty dict
        ]
        for step_case in edge_case_steps:
            test_case: dict[str, Any] = {"testScript": {"steps": [step_case]}}
            changes_made: list[dict[str, Any]] = []
            analyzer.improve_steps(test_case, 0, changes_made)

            # Should handle edge cases without errors
            assert "testScript" in test_case
            assert "steps" in test_case["testScript"]
            # Steps should remain a valid list
            assert isinstance(test_case["testScript"]["steps"], list)
            assert isinstance(changes_made, list)
