"""Integration tests for bulk conversion functionality."""

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from importobot import exceptions
from importobot.core.converter import (
    convert_directory,
    convert_multiple_files,
)


class TestBulkConversionIntegration:
    """Integration tests for bulk file conversion."""

    def test_convert_multiple_files_integration(self) -> None:
        """Tests end-to-end conversion of multiple JSON files."""
        sample_json_data = {
            "tests": [
                {
                    "name": "Test Login",
                    "steps": [
                        {
                            "step": "Navigate to login page",
                            "data": "",
                            "expectedResult": "Login page is displayed",
                        }
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple input files
            input_files = []
            for i in range(3):
                input_file = temp_path / f"test_{i}.json"
                input_file.write_text(json.dumps(sample_json_data))
                input_files.append(str(input_file))

            # Create output directory
            output_dir = temp_path / "output"

            # Perform conversion
            convert_multiple_files(input_files, str(output_dir))

            # Verify output files were created
            for i in range(3):
                output_file = output_dir / f"test_{i}.robot"
                assert output_file.exists()
                assert output_file.stat().st_size > 0

                # Verify content structure
                content = output_file.read_text()
                assert "*** Test Cases ***" in content
                assert "Test Login" in content

    def test_convert_directory_integration(self) -> None:
        """Tests end-to-end conversion of entire directory."""
        sample_json_data = {
            "tests": [
                {
                    "name": "Test Registration",
                    "steps": [
                        {
                            "step": "Fill registration form",
                            "data": "user@example.com",
                            "expectedResult": "Form accepts valid email",
                        }
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create input directory with JSON files
            input_dir = temp_path / "input"
            input_dir.mkdir()

            # Create JSON files and non-JSON files
            for i in range(2):
                json_file = input_dir / f"test_{i}.json"
                json_file.write_text(json.dumps(sample_json_data))

            # Create non-JSON file (should be ignored)
            non_json_file = input_dir / "readme.txt"
            non_json_file.write_text("This should be ignored")

            # Create output directory
            output_dir = temp_path / "output"

            # Perform conversion
            convert_directory(str(input_dir), str(output_dir))

            # Verify only JSON files were converted
            output_files = list(output_dir.glob("*.robot"))
            assert len(output_files) == 2

            for output_file in output_files:
                assert output_file.stat().st_size > 0
                content = output_file.read_text()
                assert "*** Test Cases ***" in content
                assert "Test Registration" in content

    def test_convert_directory_with_subdirectories(self) -> None:
        """Tests directory conversion ignores subdirectories."""
        sample_json_data: dict[str, Any] = {
            "tests": [
                {
                    "name": "Sample Test",
                    "steps": [
                        {
                            "step": "Sample step",
                            "expectedResult": "Sample result",
                        }
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create input directory structure
            input_dir = temp_path / "input"
            input_dir.mkdir()
            sub_dir = input_dir / "subdir"
            sub_dir.mkdir()

            # Create JSON file in main directory
            main_json = input_dir / "main_test.json"
            main_json.write_text(json.dumps(sample_json_data))

            # Create JSON file in subdirectory (should be ignored)
            sub_json = sub_dir / "sub_test.json"
            sub_json.write_text(json.dumps(sample_json_data))

            output_dir = temp_path / "output"

            convert_directory(str(input_dir), str(output_dir))

            # All JSON files (including those in subdirectories) should be converted
            output_files = list(output_dir.rglob("*.robot"))
            assert len(output_files) == 2
            assert any(f.name == "main_test.robot" for f in output_files)
            assert any(f.name == "sub_test.robot" for f in output_files)

    def test_convert_multiple_files_with_errors(self) -> None:
        """Tests bulk conversion handling of individual file errors."""
        valid_json_data: dict[str, Any] = {"testCases": []}
        invalid_json_data = '{"invalid": json'

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create valid and invalid JSON files
            valid_file = temp_path / "valid.json"
            valid_file.write_text(json.dumps(valid_json_data))

            invalid_file = temp_path / "invalid.json"
            invalid_file.write_text(invalid_json_data)

            output_dir = temp_path / "output"

            # Conversion should fail on invalid file
            with pytest.raises(exceptions.ConversionError):
                convert_multiple_files(
                    [str(valid_file), str(invalid_file)], str(output_dir)
                )

    def test_convert_directory_empty_directory(self) -> None:
        """Tests directory conversion with empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            input_dir = temp_path / "empty_input"
            input_dir.mkdir()
            output_dir = temp_path / "output"

            with pytest.raises(exceptions.ValidationError, match="No JSON files found"):
                convert_directory(str(input_dir), str(output_dir))

    def test_convert_multiple_files_creates_nested_output_structure(self) -> None:
        """Tests that output directory structure is created as needed."""
        sample_json_data: dict[str, Any] = {
            "tests": [
                {
                    "name": "Structure Test",
                    "steps": [
                        {
                            "step": "Test step",
                            "expectedResult": "Test result",
                        }
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            input_file = temp_path / "test.json"
            input_file.write_text(json.dumps(sample_json_data))

            # Use nested output directory that doesn't exist
            output_dir = temp_path / "nested" / "output" / "dir"

            convert_multiple_files([str(input_file)], str(output_dir))

            # Verify nested directory was created
            assert output_dir.exists()
            assert (output_dir / "test.robot").exists()

    def test_convert_directory_case_insensitive_json_extension(self) -> None:
        """Tests that JSON files with different case extensions are handled."""
        sample_json_data: dict[str, Any] = {
            "tests": [
                {
                    "name": "Extension Test",
                    "steps": [
                        {
                            "step": "Case insensitive step",
                            "expectedResult": "Extension result",
                        }
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            input_dir = temp_path / "input"
            input_dir.mkdir()

            # Create files with different case extensions
            (input_dir / "test1.json").write_text(json.dumps(sample_json_data))
            (input_dir / "test2.JSON").write_text(json.dumps(sample_json_data))
            (input_dir / "test3.Json").write_text(json.dumps(sample_json_data))

            output_dir = temp_path / "output"

            convert_directory(str(input_dir), str(output_dir))

            # All JSON files should be converted
            output_files = list(output_dir.glob("*.robot"))
            assert len(output_files) == 3
