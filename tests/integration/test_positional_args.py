"""Integration tests for enhanced positional arguments functionality."""

import json
import tempfile
from pathlib import Path
from typing import Any

from importobot.cli.handlers import InputType, detect_input_type


class TestPositionalArgsIntegration:
    """Integration tests for positional arguments with real files."""

    def testdetect_input_type_file(self) -> None:
        """Tests file type detection with real file."""
        sample_json_data: dict[str, Any] = {"tests": []}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test file
            test_file = temp_path / "test.json"
            test_file.write_text(json.dumps(sample_json_data))

            input_type, files = detect_input_type(str(test_file))

            assert input_type == InputType.FILE
            assert files == [str(test_file)]

    def testdetect_input_type_directory(self) -> None:
        """Tests directory type detection with real directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_type, files = detect_input_type(temp_dir)

            assert input_type == InputType.DIRECTORY
            assert files == [temp_dir]

    def testdetect_input_type_wildcard_single_match(self) -> None:
        """Tests wildcard detection with single matching file."""
        sample_json_data: dict[str, Any] = {"tests": []}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            test_file = temp_path / "test.json"
            test_file.write_text(json.dumps(sample_json_data))

            # Test wildcard pattern
            wildcard_pattern = str(temp_path / "test*.json")
            input_type, files = detect_input_type(wildcard_pattern)

            assert input_type == InputType.WILDCARD
            assert len(files) == 1
            assert str(test_file) in files

    def testdetect_input_type_wildcard_multiple_matches(self) -> None:
        """Tests wildcard detection with multiple matching files."""
        sample_json_data: dict[str, Any] = {"tests": []}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple test files
            for i in range(3):
                test_file = temp_path / f"test{i}.json"
                test_file.write_text(json.dumps(sample_json_data))

            # Create non-JSON file (should be filtered out)
            non_json_file = temp_path / "test.txt"
            non_json_file.write_text("not json")

            # Test wildcard pattern
            wildcard_pattern = str(temp_path / "test*")
            input_type, files = detect_input_type(wildcard_pattern)

            assert input_type == InputType.WILDCARD
            assert len(files) == 3  # Only JSON files
            for i in range(3):
                assert str(temp_path / f"test{i}.json") in files

    def testdetect_input_type_recursive_wildcard(self) -> None:
        """Tests recursive wildcard detection."""
        sample_json_data: dict[str, Any] = {"tests": []}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory structure
            sub_dir = temp_path / "subdir"
            sub_dir.mkdir()

            # Create files in different directories
            (temp_path / "test1.json").write_text(json.dumps(sample_json_data))
            (sub_dir / "test2.json").write_text(json.dumps(sample_json_data))

            # Test recursive wildcard pattern
            wildcard_pattern = str(temp_path / "**/*.json")
            input_type, files = detect_input_type(wildcard_pattern)

            assert input_type == InputType.WILDCARD
            assert len(files) == 2
            assert str(temp_path / "test1.json") in files
            assert str(sub_dir / "test2.json") in files

    def testdetect_input_type_wildcard_no_matches(self) -> None:
        """Tests wildcard with no matching files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create non-matching file
            (temp_path / "test.txt").write_text("not json")

            # Test wildcard pattern with no matches
            wildcard_pattern = str(temp_path / "*.json")
            input_type, files = detect_input_type(wildcard_pattern)

            assert input_type == InputType.ERROR
            assert not files

    def testdetect_input_type_nonexistent_file(self, tmp_path: Path) -> None:
        """Tests detection of nonexistent file."""
        nonexistent_file = tmp_path / "nonexistent" / "file.json"
        input_type, files = detect_input_type(str(nonexistent_file))

        assert input_type == InputType.ERROR
        assert files == []

    def testdetect_input_type_case_insensitive_json(self) -> None:
        """Tests wildcard detection with case-insensitive JSON extensions."""
        sample_json_data: dict[str, Any] = {"tests": []}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with different case extensions
            (temp_path / "test1.json").write_text(json.dumps(sample_json_data))
            (temp_path / "test2.JSON").write_text(json.dumps(sample_json_data))
            (temp_path / "test3.Json").write_text(json.dumps(sample_json_data))

            # Test wildcard pattern
            wildcard_pattern = str(temp_path / "test*")
            input_type, files = detect_input_type(wildcard_pattern)

            assert input_type == InputType.WILDCARD
            assert len(files) == 3
            for i in range(1, 4):
                assert any(f"test{i}." in f for f in files)

    def testdetect_input_type_mixed_extensions(self) -> None:
        """Tests wildcard with mixed file extensions, only JSON should match."""
        sample_json_data: dict[str, Any] = {"tests": []}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with different extensions
            (temp_path / "test1.json").write_text(json.dumps(sample_json_data))
            (temp_path / "test2.xml").write_text("<root></root>")
            (temp_path / "test3.txt").write_text("plain text")
            (temp_path / "test4.JSON").write_text(json.dumps(sample_json_data))

            # Test wildcard pattern
            wildcard_pattern = str(temp_path / "test*")
            input_type, files = detect_input_type(wildcard_pattern)

            assert input_type == InputType.WILDCARD
            assert len(files) == 2  # Only JSON files
            assert str(temp_path / "test1.json") in files
            assert str(temp_path / "test4.JSON") in files
            assert str(temp_path / "test2.xml") not in files
            assert str(temp_path / "test3.txt") not in files
