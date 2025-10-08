"""Integration tests for the public API surface."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# Test the public API surface as it would be used by external users
import importobot
from importobot.api import converters, suggestions, validation
from tests.test_helpers import EXPECTED_PUBLIC_EXPORTS, assert_module_exports


def _make_test_payload() -> dict:
    """Create a representative test case for conversion assertions."""
    return {
        "tests": [
            {
                "name": "Login Test",
                "description": "Test user login functionality",
                "testScript": {
                    "steps": [
                        {
                            "action": "Navigate to login page",
                            "expectedResult": "Login page displays",
                            "testData": "url=/login",
                        },
                        {
                            "action": "Enter valid credentials",
                            "expectedResult": "User logged in successfully",
                            "testData": "username=demo, password=secret",
                        },
                    ]
                },
            }
        ]
    }


class TestPublicAPIIntegration:
    """Test complete API workflows as external users would use them."""

    def test_core_conversion_workflow(self):
        """Exercise the primary conversion workflow end to end."""
        converter = importobot.JsonToRobotConverter()

        robot_output = converter.convert_json_data(_make_test_payload())

        assert "*** Test Cases ***" in robot_output
        assert "Login Test" in robot_output
        assert "Navigate to login page" in robot_output

    def test_enterprise_validation_workflow(self):
        """Validation helpers return data and reject unsafe inputs."""
        valid_data = {"testCase": {"name": "Test", "steps": []}}
        dict_result = validation.validate_json_dict(valid_data)
        assert dict_result is valid_data

        with pytest.raises(validation.ValidationError):
            validation.validate_json_dict(["not", "a", "dict"])

        safe_path = validation.validate_safe_path("/tmp/test.json")
        assert safe_path.endswith("test.json")

        with pytest.raises(validation.ValidationError):
            validation.validate_safe_path("../etc/passwd")

    def test_converter_api_workflow(self):
        """Public converters expose behaviourally equivalent classes."""
        converter = converters.JsonToRobotConverter()

        output = converter.convert_json_data(_make_test_payload())

        assert "Force Tags" in output or "*** Test Cases ***" in output
        assert "Login Test" in output

    def test_suggestions_api_workflow(self):
        """Suggestion engine surfaces actionable improvements."""
        engine = suggestions.GenericSuggestionEngine()

        incomplete_payload = {"name": "Broken", "testScript": {"steps": [{}]}}

        suggestions_list = engine.get_suggestions(incomplete_payload)

        assert any("Add action description" in item for item in suggestions_list)

    def test_api_error_handling(self):
        """API surfaces raise documented exceptions for bad input."""
        converter = importobot.JsonToRobotConverter()

        with pytest.raises(importobot.exceptions.ValidationError):
            converter.convert_json_string("")

        with pytest.raises(importobot.exceptions.ParseError):
            converter.convert_json_string("not json")

    def test_full_conversion_pipeline(self):
        """Test a complete conversion pipeline using public API."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test input file
            test_data = {
                "testCase": {
                    "name": "Login Test",
                    "description": "Test user login functionality",
                    "steps": [
                        {
                            "stepDescription": "Navigate to login page",
                            "expectedResult": "Login page displays",
                        },
                        {
                            "stepDescription": "Enter valid credentials",
                            "expectedResult": "User logged in successfully",
                        },
                    ],
                }
            }

            input_file = temp_path / "test_input.json"
            with open(input_file, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            output_file = temp_path / "test_output.robot"

            # Use public API for conversion
            converter = importobot.JsonToRobotConverter()

            # Test file conversion
            # pylint: disable=no-member
            result = converter.convert_file(str(input_file), str(output_file))
            assert result is not None
            assert output_file.exists()

            content = output_file.read_text(encoding="utf-8")
            assert "*** Test Cases ***" in content
            assert "Login Test" in content
            assert "# Expected Result: Login page displays" in content

    def test_api_configuration_access(self):
        """Test configuration access through public API."""
        # Test config is accessible
        assert hasattr(importobot, "config")

        config = importobot.config
        assert config.DEFAULT_TEST_SERVER_URL.startswith("http")
        assert isinstance(config.TEST_SERVER_PORT, int)
        assert config.TEST_SERVER_PORT > 0
        assert "--headless" in config.CHROME_OPTIONS

    def test_version_stability(self):
        """Test that version information is accessible."""
        # Test version is accessible
        assert hasattr(importobot, "__version__")
        assert isinstance(importobot.__version__, str)

    def test_api_namespace_cleanliness(self):
        """Test that internal modules are not exposed in public namespace."""
        # __all__ should match documented exports
        assert_module_exports(importobot, EXPECTED_PUBLIC_EXPORTS)

        # Internal modules must not leak via __all__
        for internal_name in ("core", "utils"):
            assert internal_name not in importobot.__all__

    def test_enterprise_ci_cd_workflow(self):
        """Test typical CI/CD integration workflow."""
        # Simulate CI/CD validation workflow
        test_data = {
            "testCase": {
                "name": "CI Test",
                "testScript": {"steps": [{}]},
            }
        }

        validation.validate_json_dict(test_data)

        engine = suggestions.GenericSuggestionEngine()
        improvements = engine.suggest_improvements([test_data])

        assert any("Add test case description" in item for item in improvements)

    def test_pandas_style_api_patterns(self):
        """Test that API follows pandas-style patterns."""
        # Test main module structure
        assert hasattr(importobot, "api")
        assert hasattr(importobot.api, "validation")
        assert hasattr(importobot.api, "converters")
        assert hasattr(importobot.api, "suggestions")

        # Test that submodules have clean interfaces
        assert set(importobot.api.validation.__all__) == {
            "validate_json_dict",
            "validate_safe_path",
            "ValidationError",
        }
        assert "JsonToRobotConverter" in importobot.api.converters.__all__
        assert "GenericSuggestionEngine" in importobot.api.suggestions.__all__


class TestAPIBackwardCompatibility:
    """Test API backward compatibility and version stability."""

    def test_core_api_stability(self):
        """Test that core API remains stable."""
        # Test JsonToRobotConverter interface
        converter = importobot.JsonToRobotConverter()

        output = converter.convert_json_data(_make_test_payload())

        assert "*** Test Cases ***" in output
        assert "Login Test" in output

    def test_exception_interface_stability(self):
        """Test that exception interfaces remain stable."""
        with pytest.raises(importobot.exceptions.ValidationError):
            raise importobot.exceptions.ValidationError("Test validation error")

        with pytest.raises(importobot.exceptions.ImportobotError):
            raise importobot.exceptions.ConversionError("Test conversion error")
