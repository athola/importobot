"""Core system-wide invariant tests using Hypothesis.
# pylint: disable=missing-function-docstring,no-member  # Invariant tests

Tests fundamental properties that should always hold true across the system:
- JSON parsing is safe and reversible
- File operations handle invalid inputs gracefully
- Error handling is consistent
- Configuration validation is comprehensive
"""

import contextlib
import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from importobot.core.converter import JsonToRobotConverter
from importobot.core.parsers import GenericTestFileParser
from importobot.exceptions import ImportobotError, ValidationError
from importobot.medallion.storage.config import StorageConfig
from importobot.utils.validation import validate_safe_path


class TestCoreInvariants:
    """Core system invariant tests."""

    @given(st.text(min_size=0, max_size=1000))
    @settings(max_examples=50)
    def test_safe_path_validation_invariant(self, path_str: str) -> None:
        """Invariant: Path validation should never raise unexpected exceptions."""
        try:
            result = validate_safe_path(path_str)
            # If no exception, result should be a valid path string
            assert result is None or isinstance(result, str)
        except (ValidationError, ValueError, OSError) as e:
            # Expected exceptions are fine
            assert isinstance(e, ValidationError | ValueError | OSError)
        except Exception as e:
            # Unexpected exceptions should not occur
            pytest.fail(
                f"Unexpected exception in path validation: {type(e).__name__}: {e}"
            )

    @given(
        st.dictionaries(
            st.text(),
            st.recursive(
                st.one_of(
                    st.none(),
                    st.booleans(),
                    st.integers(),
                    st.floats(allow_nan=False, allow_infinity=False),
                    st.text(),
                ),
                lambda children: st.one_of(
                    st.lists(children), st.dictionaries(st.text(), children)
                ),
                max_leaves=20,
            ),
        )
    )
    @settings(max_examples=50)
    def test_json_roundtrip_invariant(self, data: dict[str, Any]) -> None:
        """Invariant: Valid JSON data should round-trip through serialization."""
        try:
            # Serialize to JSON string
            json_str = json.dumps(data)

            # Deserialize back to Python object
            roundtrip_data = json.loads(json_str)

            # Data should be equivalent after round-trip
            assert roundtrip_data == data

        except (TypeError, ValueError, OverflowError):
            # Some data types can't be JSON serialized
            # This is expected and acceptable
            pass

    @given(st.text(min_size=0, max_size=1000))
    @settings(max_examples=50)
    def test_json_parsing_safety_invariant(self, json_str: str) -> None:
        """Invariant: JSON parsing should handle invalid input safely."""
        try:
            json.loads(json_str)
            # If parsing succeeds, we should have a valid Python object (including None)
            # No need to assert anything specific - successful parsing is enough
        except (json.JSONDecodeError, TypeError):
            # Expected for invalid JSON - this is safe failure
            pass
        except Exception as e:
            # Unexpected exceptions indicate potential security issues
            pytest.fail(
                f"Unexpected exception in JSON parsing: {type(e).__name__}: {e}"
            )

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=50), st.text(min_size=0, max_size=100)
        )
    )
    @settings(max_examples=30)
    def test_converter_initialization_invariant(
        self, _config_data: dict[str, str]
    ) -> None:
        """Invariant: Converter should initialize safely with various configurations."""
        try:
            converter = JsonToRobotConverter()

            # Converter should always have required attributes after initialization
            assert hasattr(converter, "conversion_engine")
            assert hasattr(converter, "suggestion_engine")
            assert converter.conversion_engine is not None
            assert converter.suggestion_engine is not None

        except ImportobotError:
            # Expected application errors are fine
            pass
        except Exception as e:
            # Unexpected system errors should not occur during initialization
            pytest.fail(
                f"Unexpected exception in converter initialization: "
                f"{type(e).__name__}: {e}"
            )

    @given(st.text(min_size=1, max_size=500).filter(lambda x: not x.isspace()))
    @settings(max_examples=30)
    def test_file_operation_safety_invariant(self, content: str) -> None:
        """Invariant: File operations should handle various content safely."""
        # Use temporary files to avoid affecting the system
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_file:
            try:
                # Write content to temporary file
                tmp_file.write(content)
                tmp_file.flush()

                # Read it back
                with open(tmp_file.name, encoding="utf-8", newline="") as read_file:
                    read_content = read_file.read()

                # Content should match what we wrote (or be platform-normalized)
                assert read_content == content or read_content == content.replace(
                    "\r", "\n"
                )

            except (OSError, UnicodeError):
                # Expected file system errors
                pass
            finally:
                # Clean up
                with contextlib.suppress(OSError):
                    Path(tmp_file.name).unlink()

    @given(
        st.one_of(
            st.none(),
            st.text(),
            st.integers(),
            st.floats(),
            st.lists(st.text()),
            st.dictionaries(st.text(), st.text()),
        )
    )
    @settings(max_examples=50)
    def test_error_handling_consistency_invariant(self, invalid_input):
        """Invariant: Error handling should be consistent across the system."""
        parser = GenericTestFileParser()

        try:
            # Try to parse invalid input
            if isinstance(invalid_input, str):
                # String input - should handle gracefully
                try:
                    if invalid_input.strip():
                        data = json.loads(invalid_input)
                        result = parser.find_tests(data)
                        # Parser should return a list
                        assert isinstance(result, list)
                except json.JSONDecodeError:
                    # Expected for invalid JSON
                    pass
            else:
                # Non-string input should be handled gracefully
                # Most parsers expect string input
                pass

        except (
            ImportobotError,
            ValidationError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            # Expected application and parsing errors
            pass
        except Exception as e:
            # Unexpected system errors indicate inconsistent error handling
            pytest.fail(f"Inconsistent error handling: {type(e).__name__}: {e}")

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(), st.integers(min_value=0), st.booleans()),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=30)
    def test_configuration_structure_invariant(
        self, config_dict: dict[str, Any]
    ) -> None:
        """Test that configuration structures are handled properly."""

        try:
            # Try to create configuration from arbitrary data
            config = StorageConfig.from_dict(config_dict)

            # Configuration should always be valid after creation
            validation_issues = config.validate()

            # If there are validation issues, they should be proper strings
            for issue in validation_issues:
                assert isinstance(issue, str)
                assert len(issue) > 0

            # Configuration should be serializable
            config_dict_output = config.to_dict()
            assert isinstance(config_dict_output, dict)

        except (TypeError, ValueError, AttributeError):
            # Expected for invalid configuration data
            pass
