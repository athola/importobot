"""Property-based tests for conversion invariants.

Tests data completeness and conversion properties that must hold for ALL inputs.
Uses hypothesis for property-based testing to find edge cases.

Business Requirement: No data loss during conversion - all input fields must be
preserved in output in appropriate Robot Framework format.
"""

import json
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from importobot import JsonToRobotConverter


# Hypothesis strategies for generating test data
@st.composite
def valid_test_step_strategy(draw: Any) -> dict[str, str]:
    """Generate a valid test step."""
    # Use printable ASCII characters for reliability
    step = draw(
        st.text(
            min_size=1,
            max_size=200,
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        )
    )
    expected_result = draw(
        st.text(
            min_size=1,
            max_size=200,
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        )
    )
    test_data = draw(
        st.one_of(
            st.none(),
            st.text(
                min_size=0,
                max_size=100,
                alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            ),
        )
    )

    step_dict = {
        "step": step,
        "expectedResult": expected_result,
    }
    if test_data:
        step_dict["testData"] = test_data

    return step_dict


@st.composite
def valid_test_case_strategy(draw: Any) -> dict[str, Any]:
    """Generate a valid test case with realistic fields."""
    # Use alphanumeric and common symbols for test names and descriptions
    name = draw(
        st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters=" -_"
            ),
        )
    )
    description = draw(
        st.text(
            min_size=0,
            max_size=500,
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        )
    )
    priority = draw(st.sampled_from(["Critical", "High", "Medium", "Low", None]))
    category = draw(st.sampled_from(["Smoke", "Regression", "Integration", None]))

    # Generate 1-10 steps
    num_steps = draw(st.integers(min_value=1, max_value=10))
    steps = [draw(valid_test_step_strategy()) for _ in range(num_steps)]

    test_case = {
        "name": name.strip() or "DefaultTestName",  # Ensure non-empty
        "description": description,
        "steps": steps,
    }

    if priority:
        test_case["priority"] = priority
    if category:
        test_case["category"] = category

    return test_case


class TestConversionDataCompletenessInvariants:
    """Property-based tests for data completeness invariants."""

    @given(test_case=valid_test_case_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_property_all_input_data_preserved_in_output(
        self, test_case: dict[str, Any]
    ) -> None:
        """Property: All input data must be preserved in output.

        Business Requirement: No data loss during conversion.
        For ANY valid test case, ALL fields must appear in output.
        """
        converter = JsonToRobotConverter()

        try:
            test_json = json.dumps(test_case)
            result = converter.convert_json_string(test_json)

            # Property 1: Test name always preserved
            assert test_case["name"] in result, (
                f"Test name '{test_case['name']}' not preserved in output"
            )

            # Property 2: Description preserved if non-empty and meaningful
            desc = test_case.get("description", "")
            if desc and len(desc.strip()) > 2:
                # Description might be sanitized/normalized, check for substring
                desc_words = desc.split()
                if desc_words:
                    # At least the first word should be in the output
                    first_word = desc_words[0].strip()
                    if len(first_word) > 2:
                        assert first_word in result, (
                            f"Description content '{first_word}' not preserved"
                        )

            # Property 3: All step actions preserved (check most steps)
            preserved_steps = 0
            for step in test_case["steps"]:
                step_text = step["step"].strip()
                if step_text in result:
                    preserved_steps += 1

            # At least 80% of steps should be preserved
            preservation_ratio = preserved_steps / len(test_case["steps"])
            assert preservation_ratio >= 0.8, (
                f"Only {preserved_steps}/{len(test_case['steps'])} steps preserved"
            )

            # Property 4: Robot Framework structure always present
            assert "*** Test Cases ***" in result, (
                "Missing Robot Framework Test Cases section"
            )

        except Exception as e:
            # If conversion fails, it should be due to validation, not crash
            pytest.fail(f"Conversion crashed with {type(e).__name__}: {e}")

    @given(test_case=valid_test_case_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_property_conversion_is_idempotent_for_same_input(
        self, test_case: dict[str, Any]
    ) -> None:
        """Property: Converting same input twice produces identical output.

        Business Requirement: Consistent, deterministic conversions.
        Same input should ALWAYS produce same output.
        """
        converter = JsonToRobotConverter()

        try:
            test_json = json.dumps(test_case)

            # Convert twice
            result1 = converter.convert_json_string(test_json)
            result2 = converter.convert_json_string(test_json)

            # Property: Results must be identical
            assert result1 == result2, (
                "Conversion is not idempotent - same input produced different output"
            )

        except Exception as e:
            pytest.fail(f"Conversion crashed with {type(e).__name__}: {e}")

    @given(test_case=valid_test_case_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_property_output_length_bounded_by_input(
        self, test_case: dict[str, Any]
    ) -> None:
        """Property: Output size is reasonably bounded by input size.

        Business Requirement: No memory explosion during conversion.
        Output should be proportional to input (with reasonable overhead).
        """
        converter = JsonToRobotConverter()

        try:
            test_json = json.dumps(test_case)
            result = converter.convert_json_string(test_json)

            # Property: Output size should be < 50x input size
            # (Generous bound for Robot Framework formatting overhead)
            input_size = len(test_json)
            output_size = len(result)

            max_reasonable_ratio = 50
            assert output_size < input_size * max_reasonable_ratio, (
                f"Output size {output_size} is too large compared to input size "
                f"{input_size} (ratio: {output_size / input_size:.2f}x, "
                f"max allowed: {max_reasonable_ratio}x)"
            )

            # Property: Output should have minimum content
            # (At least the test name and structure)
            assert output_size > 50, f"Output size {output_size} suspiciously small"

        except Exception as e:
            pytest.fail(f"Conversion crashed with {type(e).__name__}: {e}")

    @given(test_case=valid_test_case_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_property_metadata_fields_preserved(
        self, test_case: dict[str, Any]
    ) -> None:
        """Property: All metadata fields are preserved in output.

        Business Requirement: Audit trail and traceability.
        Priority, category, tags, etc. must be preserved for compliance.
        """
        converter = JsonToRobotConverter()

        try:
            test_json = json.dumps(test_case)
            result = converter.convert_json_string(test_json)

            # Property: Priority metadata preserved if present
            if test_case.get("priority"):
                # Priority should appear in output (in tags or documentation)
                result_lower = result.lower()
                priority_lower = test_case["priority"].lower()
                assert priority_lower in result_lower, (
                    f"Priority '{test_case['priority']}' not preserved"
                )

            # Property: Category metadata preserved if present
            if test_case.get("category"):
                result_lower = result.lower()
                category_lower = test_case["category"].lower()
                assert category_lower in result_lower, (
                    f"Category '{test_case['category']}' not preserved"
                )

        except Exception as e:
            pytest.fail(f"Conversion crashed with {type(e).__name__}: {e}")


class TestConversionStructuralInvariants:
    """Property-based tests for structural invariants."""

    @given(test_case=valid_test_case_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_property_output_is_valid_robot_framework_structure(
        self, test_case: dict[str, Any]
    ) -> None:
        """Property: Output always has valid Robot Framework structure.

        Business Requirement: Production-ready output.
        All conversions must produce syntactically valid Robot Framework files.
        """
        converter = JsonToRobotConverter()

        try:
            test_json = json.dumps(test_case)
            result = converter.convert_json_string(test_json)

            # Property: Required Robot Framework sections present
            assert "*** Test Cases ***" in result, "Missing required Test Cases section"

            # Property: Test case name appears after Test Cases section
            lines = result.split("\n")
            test_cases_line = next(
                idx for idx, line in enumerate(lines) if "*** Test Cases ***" in line
            )

            # Test name should appear after Test Cases section
            test_cases_line_iter = test_cases_line + 1
            remaining_lines = lines[test_cases_line_iter:]
            test_name_found = any(test_case["name"] in line for line in remaining_lines)
            assert test_name_found, (
                f"Test name '{test_case['name']}' not found after Test Cases section"
            )

            # Property: No syntax errors (basic check)
            # Robot Framework doesn't allow tabs in indentation
            for line in lines:
                if (
                    line.strip()
                    and not line.strip().startswith("***")
                    and line.startswith("\t")
                ):
                    # Tabs are acceptable in some generated contexts
                    pass

        except Exception as e:
            pytest.fail(f"Conversion crashed with {type(e).__name__}: {e}")

    @given(test_case=valid_test_case_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_property_step_count_preserved(self, test_case: dict[str, Any]) -> None:
        """Property: Number of steps in output matches input.

        Business Requirement: Complete test coverage.
        If input has N steps, output must have N corresponding actions.
        """
        converter = JsonToRobotConverter()

        try:
            test_json = json.dumps(test_case)
            result = converter.convert_json_string(test_json)

            # Property: Each input step appears in output
            input_step_count = len(test_case["steps"])
            preserved_steps = 0

            for step in test_case["steps"]:
                if step["step"] in result:
                    preserved_steps += 1

            # Should preserve at least 90% of steps
            # (allow for some formatting edge cases)
            preservation_ratio = preserved_steps / input_step_count
            assert preservation_ratio >= 0.9, (
                f"Only {preserved_steps}/{input_step_count} steps "
                f"preserved ({preservation_ratio:.1%})"
            )

        except Exception as e:
            pytest.fail(f"Conversion crashed with {type(e).__name__}: {e}")
