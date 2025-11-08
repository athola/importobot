"""Tests for keyword loader functionality."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from importobot.core.keyword_loader import KeywordLibraryLoader


@pytest.fixture
def sample_builtin_library_data():
    """Sample BuiltIn library data for testing."""
    return {
        "library_name": "BuiltIn",
        "keywords": {
            "Log": {
                "description": "Logs the given message with the given level",
                "args": ["message", "level=INFO"],
            },
            "Set Variable": {
                "description": (
                    "Returns the given values which can then be assigned to a variables"
                ),
                "args": ["*values"],
            },
        },
    }


@pytest.fixture
def sample_ssh_library_data():
    """Sample SSHLibrary data for testing."""
    return {
        "library_name": "SSHLibrary",
        "keywords": {
            "Execute Command": {
                "description": "Execute command on remote",
                "args": ["command"],
                "security_warning": "Command execution can be dangerous",
                "security_note": "Validate all inputs",
            },
            "Safe Keyword": {"description": "A safe keyword", "args": []},
        },
    }


@pytest.fixture
def invalid_library_data():
    """Invalid library data for testing validation."""
    return {
        "keywords": {
            "Invalid Keyword": "not a dict",
            "Missing Args": {"description": "Missing args field"},
        }
    }


@pytest.fixture
def keyword_loader_fixture(tmp_path):
    """Create a KeywordLibraryLoader with test data."""
    loader = KeywordLibraryLoader()
    loader.data_dir = tmp_path

    # Create test library files
    builtin_data = {
        "library_name": "BuiltIn",
        "keywords": {
            "Log": {
                "description": "Logs the given message with the given level",
                "args": ["message", "level=INFO"],
            },
            "Set Variable": {
                "description": (
                    "Returns the given values which can then be assigned to a variables"
                ),
                "args": ["*values"],
            },
        },
    }
    ssh_data = {
        "library_name": "SSHLibrary",
        "keywords": {
            "Execute Command": {
                "description": "Execute command on remote",
                "args": ["command"],
                "security_warning": "Command execution can be dangerous",
                "security_note": "Validate all inputs",
            },
            "Safe Keyword": {"description": "A safe keyword", "args": []},
        },
    }

    builtin_file = tmp_path / "builtin.json"
    builtin_file.write_text(json.dumps(builtin_data, indent=2))

    ssh_file = tmp_path / "ssh.json"
    ssh_file.write_text(json.dumps(ssh_data, indent=2))

    return loader


class TestKeywordLibraryLoader:
    """Test KeywordLibraryLoader functionality."""

    def test_initialization(self) -> None:
        """Test KeywordLibraryLoader initialization."""
        loader = KeywordLibraryLoader()
        assert hasattr(loader, "data_dir")
        assert hasattr(loader, "_cache")
        assert not loader._cache  # pylint: disable=protected-access

    def test_load_library_unknown_library(self) -> None:
        """Test loading unknown library returns empty dict with enhanced error."""
        loader = KeywordLibraryLoader()

        with patch.object(loader.logger, "warning") as mock_warning:
            result = loader.load_library("UnknownLibrary")

            assert not result
            # Verify enhanced error message contains available libraries
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0]
            warning_template = call_args[0]
            warning_args = call_args[1:]

            assert "UnknownLibrary" in warning_args
            assert "Available libraries:" in warning_template
            assert any("BuiltIn" in str(arg) for arg in warning_args)

    def test_load_library_file_not_found(self, tmp_path) -> None:
        """Test loading library when file doesn't exist."""
        loader = KeywordLibraryLoader()

        # Mock data_dir to point to non-existent location
        loader.data_dir = tmp_path / "nonexistent"

        with patch.object(loader.logger, "warning") as mock_warning:
            result = loader.load_library("BuiltIn")

            assert not result
            # Verify enhanced error message with context
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0]
            warning_template = call_args[0]
            warning_args = call_args[1:] if len(call_args) > 1 else []

            assert "Configuration file not found" in warning_template
            assert "Expected library config for" in warning_template
            assert "Please ensure data directory exists" in warning_template
            if warning_args:
                assert any("BuiltIn" in str(arg) for arg in warning_args)

    def test_load_library_json_decode_error(self, tmp_path) -> None:
        """Test enhanced error messages for JSON decode errors."""
        loader = KeywordLibraryLoader()
        loader.data_dir = tmp_path

        # Create invalid JSON file
        invalid_json_file = loader.data_dir / "builtin.json"
        invalid_json_file.write_text('{"invalid": json syntax missing quote}')

        with patch.object(loader.logger, "error") as mock_error:
            result = loader.load_library("BuiltIn")

            assert not result
            # Verify enhanced error message with line/column info
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0]
            error_template = call_args[0]
            error_args = call_args[1:] if len(call_args) > 1 else []

            assert "Failed to parse JSON for keyword library" in error_template
            assert "Line" in error_template
            assert "Column" in error_template
            assert "Please check the JSON syntax" in error_template
            if error_args:
                assert any("BuiltIn" in str(arg) for arg in error_args)

    def test_load_library_io_error(self, tmp_path) -> None:
        """Test enhanced error messages for IO errors."""
        loader = KeywordLibraryLoader()
        loader.data_dir = tmp_path

        # Create file and then make it unreadable
        test_file = loader.data_dir / "builtin.json"
        test_file.write_text('{"test": "data"}')

        # Mock open to raise IOError
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with patch.object(loader.logger, "error") as mock_error:
                result = loader.load_library("BuiltIn")

                assert not result
                # Verify enhanced error message with file path and context
                mock_error.assert_called_once()
                call_args = mock_error.call_args[0]
                error_template = call_args[0]
                error_args = call_args[1:] if len(call_args) > 1 else []

                assert "Failed to read keyword library" in error_template
                assert "Check file permissions" in error_template
                if error_args:
                    assert any("BuiltIn" in str(arg) for arg in error_args)
                    assert any(
                        "Permission denied" in str(arg) for arg in error_args
                    )

    def test_load_all_libraries_directory_not_found(self) -> None:
        """Test enhanced error message when data directory doesn't exist."""
        loader = KeywordLibraryLoader()

        # Set data_dir to non-existent path
        loader.data_dir = Path("/nonexistent/path")

        with patch.object(loader.logger, "warning") as mock_warning:
            result = loader.load_all_libraries()

            assert not result
            # Verify enhanced error message with helpful context
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0]
            warning_template = call_args[0]

            assert "Keywords data directory not found" in warning_template
            assert "No keyword libraries will be available" in warning_template
            assert "Please create directory" in warning_template

    def test_load_all_libraries_json_decode_error(self, tmp_path) -> None:
        """Test enhanced error messages when loading all libraries with JSON errors."""
        loader = KeywordLibraryLoader()
        loader.data_dir = tmp_path

        # Create invalid JSON file
        invalid_file = loader.data_dir / "broken.json"
        invalid_file.write_text('{"broken": json}')

        with patch.object(loader.logger, "error") as mock_error:
            result = loader.load_all_libraries()

            assert not result
            # Verify enhanced error message includes line/column and skipping info
            mock_error.assert_called_once()
            call_args = mock_error.call_args[0]
            error_template = call_args[0]

            assert "Failed to parse JSON" in error_template
            assert "Line" in error_template
            assert "Column" in error_template
            assert "Skipping this library configuration" in error_template

    def test_load_all_libraries_io_error(self, tmp_path) -> None:
        """Test enhanced error messages for IO errors when loading all libraries."""
        loader = KeywordLibraryLoader()
        loader.data_dir = tmp_path

        # Create a file
        test_file = loader.data_dir / "test.json"
        test_file.write_text('{"test": "data"}')

        # Mock open to raise IOError for this specific file
        original_open = open

        def mock_open(*args, **kwargs):
            if "test.json" in str(args[0]):
                raise OSError("Permission denied")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            with patch.object(loader.logger, "error") as mock_error:
                loader.load_all_libraries()

                # Verify enhanced error message with accessibility context
                mock_error.assert_called_once()
                call_args = mock_error.call_args[0]
                error_template = call_args[0]
                error_args = call_args[1:] if len(call_args) > 1 else []

                assert "Failed to read" in error_template
                assert "Check permissions and accessibility" in error_template
                assert "Skipping this config" in error_template
                if error_args:
                    assert any(
                        "Permission denied" in str(arg) for arg in error_args
                    )

    def test_load_library_success_with_caching(
        self,
        keyword_loader_fixture,  # pylint: disable=redefined-outer-name
    ) -> None:
        """Test successful library loading with caching."""
        loader = keyword_loader_fixture

        # First load
        result1 = loader.load_library("BuiltIn")
        assert result1["library_name"] == "BuiltIn"
        assert "Log" in result1["keywords"]
        assert "BuiltIn" in loader._cache  # pylint: disable=protected-access

        # Second load should use cache
        result2 = loader.load_library("BuiltIn")
        assert result2["library_name"] == "BuiltIn"
        assert result1 is result2  # Same object from cache

    def test_get_keywords_for_library(
        self,
        keyword_loader_fixture,  # pylint: disable=redefined-outer-name
    ) -> None:
        """Test get_keywords_for_library method."""
        loader = keyword_loader_fixture

        keywords = loader.get_keywords_for_library("BuiltIn")
        assert len(keywords) == 2
        assert "Log" in keywords
        assert "Set Variable" in keywords

    def test_get_available_libraries(
        self,
        keyword_loader_fixture,  # pylint: disable=redefined-outer-name
    ) -> None:
        """Test getting list of available libraries."""
        loader = keyword_loader_fixture

        libraries = loader.get_available_libraries()
        assert len(libraries) == 2
        assert "BuiltIn" in libraries
        assert "SSHLibrary" in libraries

    def test_get_security_warnings_for_keyword(
        self,
        keyword_loader_fixture,  # pylint: disable=redefined-outer-name
    ) -> None:
        """Test getting security warnings for specific keywords."""
        loader = keyword_loader_fixture

        # Test keyword with warnings
        warnings = loader.get_security_warnings_for_keyword("ssh", "Execute Command")
        assert len(warnings) == 2
        assert "Command execution can be dangerous" in warnings
        assert "Validate all inputs" in warnings

        # Test keyword without warnings
        warnings = loader.get_security_warnings_for_keyword("ssh", "Safe Keyword")
        assert len(warnings) == 0

    def test_refresh_cache(self) -> None:
        """Test cache refresh functionality."""
        loader = KeywordLibraryLoader()

        # Add something to cache
        loader._cache["test"] = {"data": "test"}  # pylint: disable=protected-access
        assert len(loader._cache) == 1  # pylint: disable=protected-access

        with patch.object(loader.logger, "info") as mock_info:
            loader.refresh_cache()

            assert len(loader._cache) == 0  # pylint: disable=protected-access
            mock_info.assert_called_once_with("Keyword library cache cleared")

    def test_validate_configurations(self, tmp_path) -> None:
        """Test configuration validation functionality."""
        loader = KeywordLibraryLoader()
        loader.data_dir = tmp_path

        # Create valid configuration
        valid_config = {
            "library_name": "ValidLibrary",
            "keywords": {
                "Valid Keyword": {
                    "description": "A valid keyword",
                    "args": ["arg1", "arg2"],
                }
            },
        }
        valid_file = loader.data_dir / "valid.json"
        valid_file.write_text(json.dumps(valid_config))

        # Create invalid configuration
        invalid_config = {
            "keywords": {
                "Invalid Keyword": "not a dict",
                "Missing Args": {"description": "Missing args field"},
            }
        }
        invalid_file = loader.data_dir / "invalid.json"
        invalid_file.write_text(json.dumps(invalid_config))

        # Create broken JSON
        broken_file = loader.data_dir / "broken.json"
        broken_file.write_text('{"broken": json}')

        validation_results = loader.validate_configurations()

        assert len(validation_results) == 3
        assert not validation_results["valid.json"]  # No errors
        assert len(validation_results["invalid.json"]) > 0  # Has errors
        assert len(validation_results["broken.json"]) > 0  # JSON parse error

        # Check specific validation errors
        invalid_errors = validation_results["invalid.json"]
        assert any(
            "Missing required field: library_name" in error
            for error in invalid_errors
        )
        assert any("not a dictionary" in error for error in invalid_errors)
        assert any("missing args" in error for error in invalid_errors)


class TestKeywordLoaderErrorHandling:
    """Test specific error handling scenarios with enhanced messages."""

    def test_enhanced_json_error_with_line_column_info(self, tmp_path) -> None:
        """Test that JSON errors include detailed line and column information."""
        loader = KeywordLibraryLoader()
        loader.data_dir = tmp_path

        # Create JSON with specific syntax error on line 3
        invalid_json = """
{
    "library_name": "Test",
    "keywords": {
        "test": missing_quotes_and_colon
    }
}
"""
        json_file = loader.data_dir / "builtin.json"
        json_file.write_text(invalid_json)

        with patch.object(loader.logger, "error") as mock_error:
            result = loader.load_library("BuiltIn")

            assert not result
            call_args = mock_error.call_args[0]
            error_template = call_args[0]
            error_args = call_args[1:] if len(call_args) > 1 else []

            # Should include specific line and column information
            assert "Line" in error_template
            assert "Column" in error_template
            assert "Please check the JSON syntax" in error_template
            if error_args:
                assert any("BuiltIn" in str(arg) for arg in error_args)

    def test_contextual_file_path_in_error_messages(self, tmp_path) -> None:
        """Test that error messages include full file paths for debugging."""
        loader = KeywordLibraryLoader()
        loader.data_dir = tmp_path
        json_file = loader.data_dir / "builtin.json"

        # Create the file first so the existence check passes
        json_file.write_text('{"test": "data"}')

        # Test with permission error
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with patch.object(loader.logger, "error") as mock_error:
                loader.load_library("BuiltIn")

                call_args = mock_error.call_args[0]
                error_template = call_args[0]
                error_args = call_args[1:] if len(call_args) > 1 else []

                # Check template and arguments separately
                assert "Failed to read keyword library" in error_template
                if error_args:
                    assert any("BuiltIn" in str(arg) for arg in error_args)
                    assert any("Access denied" in str(arg) for arg in error_args)
                    assert any(str(json_file) in str(arg) for arg in error_args)

    def test_available_libraries_in_unknown_library_error(self) -> None:
        """Test that unknown library errors list available options."""
        loader = KeywordLibraryLoader()

        with patch.object(loader.logger, "warning") as mock_warning:
            loader.load_library("NonExistentLibrary")

            call_args = mock_warning.call_args[0]
            warning_template = call_args[0]
            warning_args = call_args[1:] if len(call_args) > 1 else []

            assert "Available libraries:" in warning_template
            if warning_args:
                assert any("NonExistentLibrary" in str(arg) for arg in warning_args)
                # Should list actual available library names in the available
                # libraries string
                assert any("BuiltIn" in str(arg) for arg in warning_args)
                assert any("SeleniumLibrary" in str(arg) for arg in warning_args)
                assert any("SSHLibrary" in str(arg) for arg in warning_args)
