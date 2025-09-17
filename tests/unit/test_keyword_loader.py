"""Tests for keyword loader functionality."""

# pylint: disable=protected-access

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from importobot.core.keyword_loader import KeywordLibraryLoader


class TestKeywordLibraryLoader:
    """Test KeywordLibraryLoader functionality."""

    def test_initialization(self):
        """Test KeywordLibraryLoader initialization."""
        loader = KeywordLibraryLoader()
        assert hasattr(loader, "data_dir")
        assert hasattr(loader, "_cache")
        assert not loader._cache

    def test_load_library_unknown_library(self):
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

    def test_load_library_file_not_found(self):
        """Test loading library when file doesn't exist."""
        loader = KeywordLibraryLoader()

        # Mock data_dir to point to non-existent location
        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir) / "nonexistent"

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

    def test_load_library_json_decode_error(self):
        """Test enhanced error messages for JSON decode errors."""
        loader = KeywordLibraryLoader()

        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir)

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

    def test_load_library_io_error(self):
        """Test enhanced error messages for IO errors."""
        loader = KeywordLibraryLoader()

        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir)

            # Create file and then make it unreadable
            test_file = loader.data_dir / "builtin.json"
            test_file.write_text('{"test": "data"}')

            # Mock open to raise IOError
            with patch("builtins.open", side_effect=IOError("Permission denied")):
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

    def test_load_all_libraries_directory_not_found(self):
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

    def test_load_all_libraries_json_decode_error(self):
        """Test enhanced error messages when loading all libraries with JSON errors."""
        loader = KeywordLibraryLoader()

        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir)

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

    def test_load_all_libraries_io_error(self):
        """Test enhanced error messages for IO errors when loading all libraries."""
        loader = KeywordLibraryLoader()

        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir)

            # Create a file
            test_file = loader.data_dir / "test.json"
            test_file.write_text('{"test": "data"}')

            # Mock open to raise IOError for this specific file
            original_open = open

            def mock_open(*args, **kwargs):
                if "test.json" in str(args[0]):
                    raise IOError("Permission denied")
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

    def test_load_library_success_with_caching(self):
        """Test successful library loading with caching."""
        loader = KeywordLibraryLoader()

        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir)

            # Create valid JSON file
            valid_data = {
                "library_name": "TestLibrary",
                "keywords": {
                    "Test Keyword": {
                        "description": "A test keyword",
                        "args": ["arg1", "arg2"],
                    }
                },
            }
            json_file = loader.data_dir / "builtin.json"
            json_file.write_text(json.dumps(valid_data))

            # First load
            result1 = loader.load_library("BuiltIn")
            assert result1 == valid_data
            assert "BuiltIn" in loader._cache

            # Second load should use cache
            result2 = loader.load_library("BuiltIn")
            assert result2 == valid_data
            assert result1 is result2  # Same object from cache

    def test_get_keywords_for_library(self):
        """Test getting keywords for specific library."""
        loader = KeywordLibraryLoader()

        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir)

            valid_data = {
                "library_name": "TestLibrary",
                "keywords": {
                    "Keyword1": {"description": "Test", "args": []},
                    "Keyword2": {"description": "Test2", "args": ["arg1"]},
                },
            }
            json_file = loader.data_dir / "builtin.json"
            json_file.write_text(json.dumps(valid_data))

            keywords = loader.get_keywords_for_library("BuiltIn")
            assert len(keywords) == 2
            assert "Keyword1" in keywords
            assert "Keyword2" in keywords

    def test_get_available_libraries(self):
        """Test getting list of available libraries."""
        loader = KeywordLibraryLoader()

        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir)

            # Create multiple library files
            for lib_name in ["lib1", "lib2", "lib3"]:
                lib_data = {"library_name": lib_name, "keywords": {}}
                json_file = loader.data_dir / f"{lib_name}.json"
                json_file.write_text(json.dumps(lib_data))

            libraries = loader.get_available_libraries()
            assert len(libraries) == 3
            assert all(lib in libraries for lib in ["lib1", "lib2", "lib3"])

    def test_get_security_warnings_for_keyword(self):
        """Test getting security warnings for specific keywords."""
        loader = KeywordLibraryLoader()

        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir)

            lib_data = {
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
            json_file = loader.data_dir / "ssh.json"
            json_file.write_text(json.dumps(lib_data))

            # Test keyword with warnings
            warnings = loader.get_security_warnings_for_keyword(
                "ssh", "Execute Command"
            )
            assert len(warnings) == 2
            assert "Command execution can be dangerous" in warnings
            assert "Validate all inputs" in warnings

            # Test keyword without warnings
            warnings = loader.get_security_warnings_for_keyword("ssh", "Safe Keyword")
            assert len(warnings) == 0

    def test_refresh_cache(self):
        """Test cache refresh functionality."""
        loader = KeywordLibraryLoader()

        # Add something to cache
        loader._cache["test"] = {"data": "test"}
        assert len(loader._cache) == 1

        with patch.object(loader.logger, "info") as mock_info:
            loader.refresh_cache()

            assert len(loader._cache) == 0
            mock_info.assert_called_once_with("Keyword library cache cleared")

    def test_validate_configurations(self):
        """Test configuration validation functionality."""
        loader = KeywordLibraryLoader()

        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir)

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
            assert validation_results["valid.json"] == []  # No errors
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

    def test_enhanced_json_error_with_line_column_info(self):
        """Test that JSON errors include detailed line and column information."""
        loader = KeywordLibraryLoader()

        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir)

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

    def test_contextual_file_path_in_error_messages(self):
        """Test that error messages include full file paths for debugging."""
        loader = KeywordLibraryLoader()

        with tempfile.TemporaryDirectory() as temp_dir:
            loader.data_dir = Path(temp_dir)
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

    def test_available_libraries_in_unknown_library_error(self):
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
