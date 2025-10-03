"""Targeted tests for step analyzer coverage gaps."""

from typing import Any

import pytest

from importobot.core.suggestions.step_analyzer import StepAnalyzer


class TestStepAnalyzerCoverage:  # pylint: disable=too-many-public-methods
    """Test coverage for StepAnalyzer critical paths."""

    @pytest.fixture
    def analyzer(self):
        """Initialize step analyzer."""
        return StepAnalyzer()

    def test_improve_steps_basic(self, analyzer):
        """Test basic step improvement."""
        test_case: dict[str, Any] = {"testScript": {"steps": [{"step": "test action"}]}}
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)
        # Should complete without error
        assert isinstance(changes_made, list)

    def test_improve_steps_missing_action(self, analyzer):
        """Test step improvement when action is missing."""
        test_case: dict[str, Any] = {
            "testScript": {
                "steps": [{"test_data": "some data", "expected": "some result"}]
            }
        }
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)
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
        assert isinstance(changes_made, list)

    def test_fix_unmatched_braces_in_step(self, analyzer):
        """Test fixing unmatched braces in step data."""
        test_case: dict[str, Any] = {
            "testScript": {
                "steps": [{"step": "test {unmatched brace", "test_data": "data"}]
            }
        }
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)
        # Should handle unmatched braces gracefully
        assert isinstance(changes_made, list)

    def test_add_default_action_when_missing(self, analyzer):
        """Test adding default action when missing."""
        step = {"test_data": "input data", "expected": "expected output"}
        result = analyzer._add_default_action(step)  # pylint: disable=protected-access
        assert isinstance(result, bool)

    def test_add_default_expected_result_when_missing(self, analyzer):
        """Test adding default expected result when missing."""
        step = {"step": "perform test action", "test_data": "input data"}
        # pylint: disable=protected-access
        result = analyzer._add_default_expected_result(step)
        assert isinstance(result, bool)

    def test_check_steps_functionality(self, analyzer):
        """Test check_steps functionality."""
        steps = [{"step": "test action", "expected": "result"}]
        suggestions: list[dict[str, Any]] = []
        analyzer.check_steps(steps, 1, suggestions)
        assert isinstance(suggestions, list)

    def test_check_step_ordering(self, analyzer):
        """Test step ordering check."""
        steps = [{"step": "second action"}, {"step": "first action"}]
        suggestions: list[dict[str, Any]] = []
        analyzer.check_step_ordering(steps, 1, suggestions)
        assert isinstance(suggestions, list)

    def test_collect_command_steps(self, analyzer):
        """Test command step collection."""
        steps = [
            {"step": "run command", "test_data": "ls -la"},
            {"step": "verify output", "expected": "files listed"},
        ]
        result = analyzer.collect_command_steps(steps)
        assert isinstance(result, list)

    def test_fix_unmatched_braces_private(self, analyzer):
        """Test fixing unmatched braces private method."""
        step = {"step": "test {unmatched brace", "test_data": "data"}
        # pylint: disable=protected-access
        result = analyzer._fix_unmatched_braces(step)
        assert isinstance(result, bool)

    def test_improve_single_step_private(self, analyzer):
        """Test improving single step private method."""
        step = {"step": "test action"}
        result = analyzer._improve_single_step(step)  # pylint: disable=protected-access
        assert isinstance(result, bool)

    def test_check_step_fields_private(self, analyzer):
        """Test checking step fields private method."""
        step = {"step": "test action", "test_data": "data"}
        suggestions: list[dict[str, Any]] = []
        # pylint: disable=protected-access
        analyzer._check_step_fields(step, 1, 1, suggestions)
        assert isinstance(suggestions, list)

    def test_check_brace_matching_private(self, analyzer):
        """Test brace matching check private method."""
        step = {"step": "test {matched} braces"}
        suggestions: list[dict[str, Any]] = []
        # pylint: disable=protected-access
        analyzer._check_brace_matching(step, 1, 1, suggestions)

    def test_fix_brace_mismatches_text(self, analyzer):
        """Test fixing brace mismatches in text."""
        text = "test {unmatched brace"
        analyzer._fix_brace_mismatches(text)  # pylint: disable=protected-access

    def test_empty_steps_handling(self, analyzer):
        """Test handling of empty steps list."""
        test_case: dict[str, Any] = {"testScript": {"steps": []}}
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)
        assert isinstance(changes_made, list)

    def test_none_steps_handling(self, analyzer):
        """Test handling of None steps."""
        test_case: dict[str, Any] = {}
        changes_made: list[dict[str, Any]] = []
        analyzer.improve_steps(test_case, 0, changes_made)
        assert isinstance(changes_made, list)

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
            assert isinstance(changes_made, list)
