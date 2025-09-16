"""Unit tests for numeric ordering in conversion suggestions."""

from importobot.core.converter import get_conversion_suggestions


class TestNumericOrderingInSuggestions:
    """Tests that numeric values in conversion suggestions are ordered correctly."""

    def test_step_numbers_ordered_correctly_with_double_digits(self):
        """Tests that step numbers are ordered correctly even with 10+ steps.

        This specifically verifies that step 10 comes after step 9, not after step 1.
        """
        # Create test data with exactly 12 steps to ensure we have double-digit numbers
        test_data: dict = {
            "name": "Numeric Ordering Test",
            "description": "Test to verify correct numeric ordering of steps",
            "steps": [],
        }

        # Add 12 steps, each with test data that will trigger a suggestion
        for i in range(1, 13):
            step = {
                "step": f"Step {i}: Perform action",
                "testData": f"Configuration data {i} with missing {{braces",
                # Triggers suggestion
                "expectedResult": f"Action {i} completed successfully",
            }
            test_data["steps"].append(step)

        # Get conversion suggestions
        suggestions = get_conversion_suggestions(test_data)

        # Find step-related suggestions
        ordered_step_suggestions = []
        import re  # pylint: disable=import-outside-toplevel

        for suggestion_text in suggestions:
            step_match = re.search(r"[Ss]tep\s+(\d+)", suggestion_text)
            if step_match:
                step_num = int(step_match.group(1))
                ordered_step_suggestions.append((step_num, suggestion_text))

        # Should have 12 step suggestions
        assert len(ordered_step_suggestions) == 12

        # Extract just the step numbers
        step_numbers = [num for num, _ in ordered_step_suggestions]

        # Verify they're in correct numerical order (1, 2, 3, ..., 9, 10, 11, 12)
        expected_order = list(range(1, 13))  # [1, 2, 3, ..., 12]
        assert step_numbers == expected_order, (
            f"Step numbers should be in order 1,2,3,...,12 but got {step_numbers}"
        )

        # Specifically verify that step 9 comes before step 10
        nine_index = step_numbers.index(9)
        ten_index = step_numbers.index(10)
        assert nine_index < ten_index, (
            "Step 9 should come before step 10 in the ordering"
        )

        # Verify that the ordering handles numeric values correctly
        # (i.e., 9 < 10, not "9" < "10" which would be lexicographic ordering)
        for i in range(len(step_numbers) - 1):
            assert step_numbers[i] < step_numbers[i + 1], (
                f"Step numbers should be in ascending numeric order: {step_numbers}"
            )
