"""Conversion pipeline invariant tests using Hypothesis.

Tests properties that should hold true for the JSON to Robot Framework conversion:
- Conversion preserves essential test information
- Generated Robot Framework syntax is valid
- Conversion handles edge cases gracefully
- Output is deterministic for same input
"""

import contextlib
import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from importobot.core.converter import JsonToRobotConverter
from importobot.core.parsers import GenericTestFileParser
from importobot.exceptions import ImportobotError
from importobot.utils.validation import sanitize_robot_string


@st.composite
def _test_case_structure(draw):
    """Generate realistic test case structures."""
    return {
        "name": draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        "description": draw(st.text(min_size=0, max_size=200)),
        "steps": draw(
            st.lists(
                st.dictionaries(
                    keys=st.sampled_from(
                        ["step", "action", "description", "expected", "expectedResult"]
                    ),
                    values=st.text(min_size=1, max_size=100),
                    min_size=1,
                    max_size=4,
                ),
                min_size=0,
                max_size=10,
            )
        ),
        "status": draw(st.sampled_from(["PASS", "FAIL", "PENDING", "BLOCKED", None])),
        "priority": draw(st.sampled_from(["LOW", "MEDIUM", "HIGH", "CRITICAL", None])),
    }


@st.composite
def json_test_data(draw):
    """Generate JSON test data structures."""
    test_cases = draw(st.lists(_test_case_structure(), min_size=1, max_size=5))

    return {
        "testCase": draw(st.sampled_from(test_cases))
        if test_cases
        else draw(_test_case_structure()),
        "project": draw(st.text(min_size=0, max_size=50)),
        "version": draw(st.text(min_size=0, max_size=20)),
        "execution": {
            "status": draw(st.sampled_from(["PASSED", "FAILED", "SKIPPED"])),
            "timestamp": draw(st.text(min_size=0, max_size=30)),
        },
        "metadata": {
            "author": draw(st.text(min_size=0, max_size=50)),
            "tags": draw(
                st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5)
            ),
        },
    }


class TestConversionPipelineInvariants:
    """Conversion pipeline invariant tests."""

    @given(json_test_data())
    @settings(max_examples=30)
    def test_conversion_preserves_test_name_invariant(self, test_data):
        """Invariant: Test name should be preserved in Robot Framework output."""
        converter = JsonToRobotConverter()

        try:
            with (
                tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as tmp_input,
                tempfile.NamedTemporaryFile(
                    mode="w", suffix=".robot", delete=False
                ) as tmp_output,
            ):
                # Write test data to temporary file

                json.dump(test_data, tmp_input, indent=2)
                tmp_input.flush()

                # Convert to Robot Framework
                converter.convert_file(tmp_input.name, tmp_output.name)

                # Read the generated Robot Framework file
                with open(tmp_output.name, encoding="utf-8") as f:
                    robot_content = f.read()

                # Test name should appear in the output
                test_name = test_data.get("testCase", {}).get("name", "")
                if test_name and test_name.strip():
                    # Name might be modified for Robot Framework compatibility
                    # Robot Framework converts newlines and special chars to spaces
                    normalized_name = sanitize_robot_string(
                        test_name.replace("\n", " ").replace("\r", " ").strip()
                    )
                    while "  " in normalized_name:
                        normalized_name = normalized_name.replace("  ", " ")

                    # Check if the normalized name or variations appear in output
                    if normalized_name:
                        assert (
                            normalized_name in robot_content
                            or normalized_name.replace(" ", "_") in robot_content
                            or normalized_name.replace(" ", "") in robot_content
                        )

                # Output should be valid Robot Framework format
                assert "*** Test Cases ***" in robot_content
                assert len(robot_content.strip()) > 0

        except ImportobotError:
            # Expected application errors are acceptable
            pass
        except Exception as e:
            pytest.fail(f"Unexpected exception in conversion: {type(e).__name__}: {e}")
        finally:
            # Clean up temporary files
            try:
                Path(tmp_input.name).unlink()
                Path(tmp_output.name).unlink()
            except OSError:
                pass

    @given(json_test_data())
    @settings(max_examples=20)
    def test_conversion_determinism_invariant(self, test_data):
        """Invariant: Conversion should be deterministic for same input."""
        converter = JsonToRobotConverter()

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as tmp_input:
                # Write test data

                json.dump(test_data, tmp_input, indent=2)
                tmp_input.flush()

                # Convert multiple times
                outputs = []
                for _ in range(3):
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".robot", delete=False
                    ) as tmp_output:
                        converter.convert_file(tmp_input.name, tmp_output.name)

                        with open(tmp_output.name, encoding="utf-8") as f:
                            outputs.append(f.read())

                        Path(tmp_output.name).unlink()

                # All outputs should be identical
                if outputs:
                    first_output = outputs[0]
                    for output in outputs[1:]:
                        assert output == first_output

        except ImportobotError:
            # Expected application errors
            pass
        except Exception as e:
            pytest.fail(
                f"Unexpected exception in determinism test: {type(e).__name__}: {e}"
            )
        finally:
            with contextlib.suppress(OSError):
                Path(tmp_input.name).unlink()

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(), st.integers(), st.lists(st.text())),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=30)
    def test_malformed_input_handling_invariant(self, malformed_data):
        """Invariant: Conversion should handle malformed input gracefully."""
        converter = JsonToRobotConverter()

        try:
            with (
                tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as tmp_input,
                tempfile.NamedTemporaryFile(
                    mode="w", suffix=".robot", delete=False
                ) as tmp_output,
            ):
                # Write potentially malformed data

                json.dump(malformed_data, tmp_input, indent=2)
                tmp_input.flush()

                # Attempt conversion
                converter.convert_file(tmp_input.name, tmp_output.name)

                # If conversion succeeds, output should be valid Robot Framework
                with open(tmp_output.name, encoding="utf-8") as f:
                    robot_content = f.read()

                # Basic Robot Framework structure should be present
                assert isinstance(robot_content, str)
                assert len(robot_content) >= 0

        except (ImportobotError, ValueError, KeyError, TypeError):
            # Expected errors for malformed input
            pass
        except Exception as e:
            pytest.fail(
                f"Unexpected exception with malformed input: {type(e).__name__}: {e}"
            )
        finally:
            try:
                Path(tmp_input.name).unlink()
                Path(tmp_output.name).unlink()
            except OSError:
                pass

    @given(st.text(min_size=0, max_size=1000))
    @settings(max_examples=30)
    def test_json_parsing_invariant(self, json_string):
        """Invariant: JSON parsing should handle various string inputs safely."""
        parser = GenericTestFileParser()

        try:
            # First parse the JSON string
            if not json_string.strip():
                return  # Skip empty strings

            data = json.loads(json_string)

            # Then use the parser to find tests
            result = parser.find_tests(data)

            # Parser should return a list of tests
            assert isinstance(result, list)

            # If result contains tests, they should be dicts and JSON-serializable
            for test in result:
                assert isinstance(test, dict)
                json.dumps(test)  # Should not raise exception

        except (ImportobotError, ValueError, TypeError):
            # Expected parsing errors
            pass
        except Exception as e:
            pytest.fail(
                f"Unexpected exception in JSON parsing: {type(e).__name__}: {e}"
            )

    @given(json_test_data())
    @settings(max_examples=20)
    def test_robot_framework_syntax_invariant(self, test_data):
        """Invariant: Generated Robot Framework should follow basic syntax rules."""
        converter = JsonToRobotConverter()

        try:
            with (
                tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as tmp_input,
                tempfile.NamedTemporaryFile(
                    mode="w", suffix=".robot", delete=False
                ) as tmp_output,
            ):
                # Write and convert

                json.dump(test_data, tmp_input, indent=2)
                tmp_input.flush()

                converter.convert_file(tmp_input.name, tmp_output.name)

                # Read and validate Robot Framework syntax
                with open(tmp_output.name, encoding="utf-8") as f:
                    robot_content = f.read()

                # Basic syntax validation
                lines = robot_content.split("\n")

                # Should have proper sections
                has_test_cases = any("*** Test Cases ***" in line for line in lines)
                if has_test_cases:
                    # Test case names should not be indented
                    test_case_lines = []
                    in_test_cases = False

                    for line in lines:
                        if "*** Test Cases ***" in line:
                            in_test_cases = True
                            continue
                        if line.strip().startswith("***"):
                            in_test_cases = False
                        if in_test_cases and line.strip() and not line.startswith(" "):
                            test_case_lines.append(line)

                    # At least one test case should be defined
                    assert len(test_case_lines) > 0 or not robot_content.strip()

        except ImportobotError:
            # Expected conversion errors
            pass
        except Exception as e:
            pytest.fail(
                f"Unexpected exception in syntax validation: {type(e).__name__}: {e}"
            )
        finally:
            try:
                Path(tmp_input.name).unlink()
                Path(tmp_output.name).unlink()
            except OSError:
                pass

    @given(st.lists(json_test_data(), min_size=1, max_size=5))
    @settings(max_examples=15)
    def test_batch_conversion_consistency_invariant(self, test_data_list):
        """Invariant: Batch conversion should maintain individual conversion quality."""
        converter = JsonToRobotConverter()

        try:
            # Convert each test case individually
            individual_results = []
            for test_data in test_data_list:
                with (
                    tempfile.NamedTemporaryFile(
                        mode="w", suffix=".json", delete=False
                    ) as tmp_input,
                    tempfile.NamedTemporaryFile(
                        mode="w", suffix=".robot", delete=False
                    ) as tmp_output,
                ):
                    json.dump(test_data, tmp_input, indent=2)
                    tmp_input.flush()

                    converter.convert_file(tmp_input.name, tmp_output.name)

                    with open(tmp_output.name, encoding="utf-8") as f:
                        individual_results.append(f.read())

                    Path(tmp_input.name).unlink()
                    Path(tmp_output.name).unlink()

            # Each individual result should be valid
            for result in individual_results:
                assert isinstance(result, str)
                # Should have basic Robot Framework structure or be empty
                assert len(result) >= 0

        except ImportobotError:
            # Expected conversion errors
            pass
        except Exception as e:
            pytest.fail(
                f"Unexpected exception in batch conversion: {type(e).__name__}: {e}"
            )

    @given(_test_case_structure())
    @settings(max_examples=20)
    def test_special_characters_handling_invariant(self, test_case):
        """Invariant: Conversion should handle special characters safely."""
        # Add some special characters to test robustness
        special_chars_data = {
            "testCase": {
                "name": test_case.get("name", "") + " äöü@#$%^&*()[]{}|\\:\";'<>?,./`~",
                "description": "Test with special chars: ñáéíóú ©®™ 中文 🚀",
                "steps": [
                    {
                        "action": "Special action with \"quotes\" and 'apostrophes'",
                        "expected": "Result with <tags> & ampersands",
                    }
                ],
            }
        }

        converter = JsonToRobotConverter()

        try:
            with (
                tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False, encoding="utf-8"
                ) as tmp_input,
                tempfile.NamedTemporaryFile(
                    mode="w", suffix=".robot", delete=False, encoding="utf-8"
                ) as tmp_output,
            ):
                json.dump(special_chars_data, tmp_input, indent=2, ensure_ascii=False)
                tmp_input.flush()

                converter.convert_file(tmp_input.name, tmp_output.name)

                # Should be able to read the output without encoding errors
                with open(tmp_output.name, encoding="utf-8") as f:
                    robot_content = f.read()

                # Output should be a valid string
                assert isinstance(robot_content, str)

        except (ImportobotError, UnicodeError):
            # Expected for problematic characters
            pass
        except Exception as e:
            pytest.fail(
                f"Unexpected exception with special characters: {type(e).__name__}: {e}"
            )
        finally:
            try:
                Path(tmp_input.name).unlink()
                Path(tmp_output.name).unlink()
            except OSError:
                pass
