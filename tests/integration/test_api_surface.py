"""Integration tests for the public API surface."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

# Test the public API surface as it would be used by external users
import importobot
from importobot.api import converters, suggestions, validation


class TestPublicAPIIntegration:
    """Test complete API workflows as external users would use them."""

    def test_core_conversion_workflow(self):
        """Test the primary bulk conversion workflow."""
        # Test that the main converter is accessible
        converter = importobot.JsonToRobotConverter()
        assert converter is not None
        assert hasattr(converter, 'convert_file')
        assert hasattr(converter, 'convert_directory')

    def test_enterprise_validation_workflow(self):
        """Test enterprise validation features."""
        # Test validation functions are accessible
        assert hasattr(validation, 'validate_json_dict')
        assert hasattr(validation, 'validate_safe_path')
        assert hasattr(validation, 'ValidationError')

        # Test basic validation
        valid_data = {"testCase": {"name": "Test", "steps": []}}
        result = validation.validate_json_dict(valid_data)
        assert result is True

        # Test path validation
        safe_path = "/tmp/test.json"
        result = validation.validate_safe_path(safe_path)
        assert result is True

    def test_converter_api_workflow(self):
        """Test converter API functionality."""
        # Test converters module is accessible
        assert hasattr(converters, 'JsonToRobotConverter')

        # Test converter instantiation
        converter = converters.JsonToRobotConverter()
        assert converter is not None

    def test_suggestions_api_workflow(self):
        """Test suggestions API functionality."""
        # Test suggestions module is accessible
        assert hasattr(suggestions, 'GenericSuggestionEngine')

        # Test suggestion engine instantiation
        engine = suggestions.GenericSuggestionEngine()
        assert engine is not None
        assert hasattr(engine, 'suggest_improvements')

    def test_api_error_handling(self):
        """Test API error handling and exceptions."""
        # Test that exceptions are accessible
        assert hasattr(importobot.exceptions, 'ValidationError')
        assert hasattr(importobot.exceptions, 'ConversionError')
        assert hasattr(importobot.exceptions, 'ParseError')

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
                            "expectedResult": "Login page displays"
                        },
                        {
                            "stepDescription": "Enter valid credentials",
                            "expectedResult": "User logged in successfully"
                        }
                    ]
                }
            }

            input_file = temp_path / "test_input.json"
            with open(input_file, 'w') as f:
                import json
                json.dump(test_data, f)

            output_file = temp_path / "test_output.robot"

            # Use public API for conversion
            converter = importobot.JsonToRobotConverter()

            # Test file conversion
            result = converter.convert_file(str(input_file), str(output_file))
            assert result is not None
            assert output_file.exists()

            # Verify output content
            content = output_file.read_text()
            assert "Login Test" in content
            assert "Test Cases" in content

    def test_api_configuration_access(self):
        """Test configuration access through public API."""
        # Test config is accessible
        assert hasattr(importobot, 'config')

        # Test basic config functionality
        config = importobot.config
        assert config is not None

    def test_version_stability(self):
        """Test that version information is accessible."""
        # Test version is accessible
        assert hasattr(importobot, '__version__')
        assert isinstance(importobot.__version__, str)

    def test_api_namespace_cleanliness(self):
        """Test that internal modules are not exposed in public namespace."""
        # Test that internal modules are not directly accessible
        with pytest.raises(AttributeError):
            _ = importobot.core

        with pytest.raises(AttributeError):
            _ = importobot.utils

        # Test that public API is clean
        public_attrs = dir(importobot)
        expected_public = ['JsonToRobotConverter', 'api', 'config', 'exceptions']

        for attr in expected_public:
            assert attr in public_attrs

    def test_enterprise_ci_cd_workflow(self):
        """Test typical CI/CD integration workflow."""
        # Simulate CI/CD validation workflow
        test_data = {"testCase": {"name": "CI Test", "steps": []}}

        # Step 1: Validate input
        is_valid = validation.validate_json_dict(test_data)
        assert is_valid

        # Step 2: Create converter
        converter = importobot.JsonToRobotConverter()

        # Step 3: Get suggestions for improvements
        engine = suggestions.GenericSuggestionEngine()
        improvements = engine.suggest_improvements([test_data])
        assert isinstance(improvements, list)

    def test_pandas_style_api_patterns(self):
        """Test that API follows pandas-style patterns."""
        # Test main module structure
        assert hasattr(importobot, 'api')
        assert hasattr(importobot.api, 'validation')
        assert hasattr(importobot.api, 'converters')
        assert hasattr(importobot.api, 'suggestions')

        # Test that submodules have clean interfaces
        assert hasattr(importobot.api.validation, '__all__')
        assert hasattr(importobot.api.converters, '__all__')
        assert hasattr(importobot.api.suggestions, '__all__')


class TestAPIBackwardCompatibility:
    """Test API backward compatibility and version stability."""

    def test_core_api_stability(self):
        """Test that core API remains stable."""
        # Test JsonToRobotConverter interface
        converter = importobot.JsonToRobotConverter()

        # Core methods must exist
        assert hasattr(converter, 'convert_file')
        assert hasattr(converter, 'convert_directory')

        # Methods should be callable
        assert callable(getattr(converter, 'convert_file'))
        assert callable(getattr(converter, 'convert_directory'))

    def test_exception_interface_stability(self):
        """Test that exception interfaces remain stable."""
        # Test exception classes exist
        assert hasattr(importobot.exceptions, 'ValidationError')
        assert hasattr(importobot.exceptions, 'ConversionError')
        assert hasattr(importobot.exceptions, 'ParseError')

        # Test exceptions are proper exception classes
        ValidationError = importobot.exceptions.ValidationError
        assert issubclass(ValidationError, Exception)