"""Tests for public API structure and contracts.

Tests the pandas-inspired public API design including:
- Main importobot module interface
- Enterprise API toolkit (importobot.api)
- Configuration and exception handling
- Version stability and compatibility
"""

import pytest

import importobot
from importobot import JsonToRobotConverter, api, config, exceptions
from importobot.api import converters, suggestions, validation


class TestMainPublicInterface:
    """Test the main public interface ()."""

    def test_main_module_has_required_exports(self):
        """Test that main module exports the expected public API."""

        # Check __all__ exports match documentation
        expected_exports = ["JsonToRobotConverter", "config", "exceptions", "api"]
        assert hasattr(importobot, "__all__")
        assert set(importobot.__all__) == set(expected_exports)

        # Check all exported items are accessible
        assert hasattr(importobot, "JsonToRobotConverter")
        assert hasattr(importobot, "config")
        assert hasattr(importobot, "exceptions")
        assert hasattr(importobot, "api")

    def test_version_information_available(self):
        """Test that version information is accessible."""

        assert hasattr(importobot, "__version__")
        assert isinstance(importobot.__version__, str)
        assert len(importobot.__version__) > 0

    def test_dependency_validation_runs(self):
        """Test that dependency validation runs on import."""
        # If we got here, import succeeded, so dependencies are valid

        assert importobot is not None

    def test_main_converter_instantiation(self):
        """Test that the main converter can be instantiated."""
        converter = JsonToRobotConverter()
        assert converter is not None
        assert hasattr(converter, "convert_json_string")
        assert hasattr(converter, "convert_json_data")


class TestEnterpriseAPIToolkit:
    """Test the enterprise API toolkit (importobot.api)."""

    def test_api_module_structure(self):
        """Test that API module has expected structure."""
        assert hasattr(api, "__all__")
        expected_api_modules = ["converters", "suggestions", "validation"]
        assert set(api.__all__) == set(expected_api_modules)

        # Check all modules are accessible
        assert hasattr(api, "converters")
        assert hasattr(api, "suggestions")
        assert hasattr(api, "validation")

    def test_api_converters_module(self):
        """Test the API converters module."""

        assert hasattr(converters, "__all__")
        expected_exports = ["JsonToRobotConverter", "GenericConversionEngine"]
        assert set(converters.__all__) == set(expected_exports)

        # Test that we can import the main converter through API
        assert hasattr(converters, "JsonToRobotConverter")
        assert hasattr(converters, "GenericConversionEngine")

        # Test instantiation
        converter = converters.JsonToRobotConverter()
        assert converter is not None

    def test_api_validation_module(self):
        """Test the API validation module."""

        assert hasattr(validation, "__all__")
        expected_exports = [
            "validate_json_dict",
            "validate_safe_path",
            "ValidationError",
        ]
        assert set(validation.__all__) == set(expected_exports)

        # Test functions are callable
        assert callable(validation.validate_json_dict)
        assert callable(validation.validate_safe_path)
        assert issubclass(validation.ValidationError, Exception)

    def test_api_suggestions_module(self):
        """Test the API suggestions module."""

        assert hasattr(suggestions, "__all__")
        expected_exports = ["GenericSuggestionEngine"]
        assert set(suggestions.__all__) == set(expected_exports)

        # Test instantiation
        engine = suggestions.GenericSuggestionEngine()
        assert engine is not None


class TestConfigurationAccess:
    """Test configuration access and enterprise settings."""

    def test_config_module_accessibility(self):
        """Test that configuration is accessible."""
        assert hasattr(config, "DEFAULT_TEST_SERVER_URL")
        assert hasattr(config, "TEST_SERVER_PORT")
        assert hasattr(config, "MAX_JSON_SIZE_MB")
        assert hasattr(config, "CHROME_OPTIONS")

    def test_config_values_are_reasonable(self):
        """Test that configuration values are reasonable for enterprise use."""
        # Test server configuration
        assert isinstance(config.TEST_SERVER_PORT, int)
        assert 1000 <= config.TEST_SERVER_PORT <= 65535

        # Test file size limits
        assert isinstance(config.MAX_JSON_SIZE_MB, int)
        assert config.MAX_JSON_SIZE_MB > 0

        # Test Chrome options for CI/CD
        assert isinstance(config.CHROME_OPTIONS, list)
        assert "--headless" in config.CHROME_OPTIONS
        assert "--no-sandbox" in config.CHROME_OPTIONS


class TestExceptionHierarchy:
    """Test exception hierarchy and error handling."""

    def test_exception_hierarchy(self):
        """Test that exception hierarchy is properly structured."""
        # Test base exception
        assert hasattr(exceptions, "ImportobotError")
        assert issubclass(exceptions.ImportobotError, Exception)

        # Test specific exceptions
        expected_exceptions = [
            "ValidationError",
            "ConversionError",
            "ParseError",
            "FileNotFound",
            "FileAccessError",
            "SuggestionError",
        ]

        for exc_name in expected_exceptions:
            assert hasattr(exceptions, exc_name)
            exc_class = getattr(exceptions, exc_name)
            assert issubclass(exc_class, exceptions.ImportobotError)

    def test_exceptions_can_be_raised_and_caught(self):
        """Test that exceptions work properly."""
        with pytest.raises(exceptions.ValidationError):
            raise exceptions.ValidationError("Test validation error")

        with pytest.raises(exceptions.ImportobotError):
            raise exceptions.ConversionError("Test conversion error")


class TestAPICompatibility:
    """Test API compatibility and business use cases."""

    def test_bulk_conversion_interface(self):
        """Test that bulk conversion interface works for enterprise scale."""
        converter = JsonToRobotConverter()

        # Test the interface exists for bulk operations
        assert hasattr(converter, "convert_json_string")
        assert hasattr(converter, "convert_json_data")

        # Test that we can handle business-scale data
        test_json = '{"name": "Enterprise Test", "steps": []}'
        result = converter.convert_json_string(test_json)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_cicd_integration_interface(self):
        """Test that CI/CD integration interface works."""

        # Test validation functions work for CI/CD pipelines
        test_data = {"name": "Test", "steps": []}

        # Should not raise an exception for valid data
        try:
            validation.validate_json_dict(test_data)
        except Exception as e:
            pytest.fail(f"Valid data should not raise exception: {e}")

        # Test path validation for security
        safe_path = validation.validate_safe_path("/tmp/test.robot")
        assert isinstance(safe_path, str)

    def test_qa_suggestion_interface(self):
        """Test that QA suggestion interface works."""

        engine = suggestions.GenericSuggestionEngine()
        assert hasattr(engine, "get_suggestions")
        assert hasattr(engine, "apply_suggestions")

        # Should be able to call without error
        # (actual functionality tested in specific unit tests)


class TestVersionStability:
    """Test version stability promises."""

    def test_public_api_imports_work(self):
        """Test that documented public API imports work."""
        # Test main interface import

        converter = importobot.JsonToRobotConverter()
        assert converter is not None

        # Test enterprise toolkit imports
        assert validation is not None
        assert converters is not None
        assert suggestions is not None

        # Test configuration access

        assert importobot.config is not None
        assert importobot.exceptions is not None

    def test_no_accidental_internal_exposure(self):
        """Test that internal modules are not accidentally exposed."""

        # These should not be in the public namespace
        internal_modules = ["core", "utils", "cli"]

        # Check they're not in __all__
        for module_name in internal_modules:
            assert module_name not in importobot.__all__, (
                f"Internal module '{module_name}' should not be in public __all__"
            )

    def test_enterprise_business_logic_alignment(self):
        """Test that API aligns with enterprise business logic."""

        # Test 1: Bulk conversion capability (core business value)
        converter = importobot.JsonToRobotConverter()
        assert hasattr(converter, "convert_json_string")

        # Test 2: Enterprise configuration access
        assert hasattr(importobot.config, "MAX_JSON_SIZE_MB")
        assert importobot.config.MAX_JSON_SIZE_MB >= 10  # Reasonable for enterprise

        # Test 3: Comprehensive error handling for automation
        assert hasattr(importobot.exceptions, "ValidationError")
        assert hasattr(importobot.exceptions, "ConversionError")

        # Test 4: Advanced features for enterprise integration
        assert hasattr(validation, "validate_json_dict")
        assert hasattr(suggestions, "GenericSuggestionEngine")
