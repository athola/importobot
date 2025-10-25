"""Tests for public API structure and contracts."""

import json
from typing import Any

import pytest

import importobot
from importobot import JsonToRobotConverter, api, config, exceptions
from importobot.api import converters, suggestions, validation
from tests.test_helpers import EXPECTED_PUBLIC_EXPORTS, assert_module_exports


def _sample_test_data() -> dict[str, Any]:
    """Provide a reusable test payload for converter assertions."""
    return {
        "tests": [
            {
                "name": "Enterprise Test",
                "description": "Automation happy path",
                "testScript": {
                    "steps": [
                        {
                            "action": "Execute enterprise workflow",
                            "expectedResult": "Workflow completes",
                            "testData": "dataset=enterprise",
                        }
                    ]
                },
            }
        ]
    }


class TestMainPublicInterface:
    """Test the main public interface."""

    def test_main_module_has_required_exports(self):
        """__all__ matches the documented public surface."""
        assert_module_exports(importobot, EXPECTED_PUBLIC_EXPORTS)

    def test_version_information_available(self):
        """Version metadata is exposed as a non-empty string."""
        assert isinstance(importobot.__version__, str)
        assert importobot.__version__

    def test_main_converter_instantiation(self):
        """Converter performs real conversion via public import."""
        converter = JsonToRobotConverter()

        output = converter.convert_json_data(_sample_test_data())

        assert "Enterprise Test" in output
        assert "*** Test Cases ***" in output


class TestEnterpriseAPIToolkit:
    """Test the enterprise API toolkit (importobot.api)."""

    def test_api_module_structure(self):
        """Submodules are exported and produce behavioural results."""
        expected_modules = {"converters", "suggestions", "validation"}
        assert set(api.__all__) == expected_modules
        assert hasattr(api, "converters")
        assert hasattr(api, "suggestions")
        assert hasattr(api, "validation")

    def test_api_converters_module(self):
        """Converter accessed via api.converters works identically."""
        expected_exports = {"JsonToRobotConverter", "GenericConversionEngine"}
        assert set(converters.__all__) == expected_exports

        converter = converters.JsonToRobotConverter()
        output = converter.convert_json_data(_sample_test_data())

        assert output.count("Enterprise Test") == 1

    def test_api_validation_module(self):
        """Validation helpers react to good and bad inputs."""
        assert set(validation.__all__) == {
            "validate_json_dict",
            "validate_safe_path",
            "ValidationError",
        }

        empty_payload: dict[str, object] = {}
        validated_payload = validation.validate_json_dict(empty_payload)
        assert validated_payload is empty_payload
        with pytest.raises(validation.ValidationError):
            validation.validate_json_dict("not-a-dict")

        assert validation.validate_safe_path("/tmp/suite.robot").endswith("suite.robot")

    def test_api_suggestions_module(self):
        """Suggestion engine from the API namespace returns actionable text."""
        assert suggestions.__all__ == ["GenericSuggestionEngine"]

        engine = suggestions.GenericSuggestionEngine()
        guidance = engine.get_suggestions(
            {"name": "Missing", "testScript": {"steps": [{}]}}
        )

        assert any("Add test case description" in item for item in guidance)


class TestConfigurationAccess:
    """Test configuration access and enterprise settings."""

    def test_config_module_accessibility(self):
        """Configuration exposes the documented knobs with sensible values."""
        assert config.DEFAULT_TEST_SERVER_URL.startswith("http")
        assert 1000 <= config.TEST_SERVER_PORT <= 65535
        assert config.MAX_JSON_SIZE_MB >= 1
        required_flags = {"--headless", "--no-sandbox"}
        assert required_flags.issubset(config.CHROME_OPTIONS)


class TestExceptionHierarchy:
    """Test exception hierarchy and error handling."""

    def test_exceptions_can_be_raised_and_caught(self):
        """Public exceptions remain part of the ImportobotError hierarchy."""
        with pytest.raises(exceptions.ValidationError):
            raise exceptions.ValidationError("Test validation error")

        with pytest.raises(exceptions.ImportobotError):
            raise exceptions.SuggestionError("Suggestion failure")


class TestAPICompatibility:
    """Test API compatibility and business use cases."""

    def test_bulk_conversion_interface(self):
        """convert_json_string handles enterprise payloads and returns Robot text."""
        converter = JsonToRobotConverter()
        payload = json.dumps(_sample_test_data()["tests"][0])

        robot_output = converter.convert_json_string(payload)

        assert "*** Test Cases ***" in robot_output
        assert "Enterprise Test" in robot_output

    def test_cicd_integration_interface(self):
        """Validation helpers protect CI/CD scenarios with real errors."""
        validation.validate_json_dict({})
        with pytest.raises(validation.ValidationError):
            validation.validate_json_dict([])

        assert validation.validate_safe_path("/tmp/test.robot").endswith("test.robot")

    def test_qa_suggestion_interface(self):
        """Suggestion engine produces guidance for incomplete tests."""
        engine = suggestions.GenericSuggestionEngine()
        guidance = engine.get_suggestions({"name": "QA", "testScript": {"steps": [{}]}})

        assert any("Add test case description" in item for item in guidance)


class TestVersionStability:
    """Test version stability promises."""

    def test_public_api_imports_work(self):
        """Direct imports execute behaviour end-to-end."""
        converter = importobot.JsonToRobotConverter()
        output = converter.convert_json_data(_sample_test_data())

        assert "Enterprise Test" in output

    def test_no_accidental_internal_exposure(self):
        """Internal modules stay out of the exported namespace."""
        for internal_module in ("core", "utils", "cli"):
            assert internal_module not in importobot.__all__

    def test_enterprise_business_logic_alignment(self):
        """Key enterprise hooks remain present and functional."""
        assert config.MAX_JSON_SIZE_MB >= 10
        assert hasattr(exceptions, "ValidationError")
        assert hasattr(exceptions, "ConversionError")

        guidance = suggestions.GenericSuggestionEngine().get_suggestions(
            {"name": "Enterprise", "testScript": {"steps": [{}]}}
        )
        assert guidance
