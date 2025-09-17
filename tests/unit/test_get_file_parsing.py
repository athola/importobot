"""Unit tests for get_file.json parsing and conversion."""

import json
from pathlib import Path

from importobot.core.converter import JsonToRobotConverter
from tests.utils import validate_test_script_structure


class TestGetFileJsonParsing:
    """Tests for parsing get_file.json example."""

    def test_get_file_json_structure_validation(self):
        """Tests that get_file.json has expected structure."""
        get_file_path = (
            Path(__file__).parent.parent.parent / "examples" / "json" / "get_file.json"
        )

        with open(get_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate top-level structure
        assert "projectKey" in data
        assert "name" in data
        assert "description" in data
        assert "priority" in data
        assert "labels" in data
        assert "testScript" in data

        # Validate test script structure
        test_script = data["testScript"]
        validate_test_script_structure(test_script)

        # Validate get_file steps structure
        for test_step in test_script["steps"]:
            assert "step" in test_step
            assert "testData" in test_step
            assert "expectedResult" in test_step

    def test_get_file_json_parsing_generates_robot_content(self):
        """Tests that get_file.json generates valid Robot Framework content."""
        get_file_path = (
            Path(__file__).parent.parent.parent / "examples" / "json" / "get_file.json"
        )

        with open(get_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        converter = JsonToRobotConverter()
        result = converter.convert_json_data(data)

        # Validate Robot Framework structure
        assert "*** Settings ***" in result
        assert "*** Test Cases ***" in result
        assert "Documentation" in result
        assert "Library    OperatingSystem" in result
        assert "Library    Process" in result

        # Validate specific content from get_file.json
        assert "Verify Remote File Download" in result
        assert "# Step: Identify the remote file URL and destination path." in result
        assert (
            "Run Process    curl    -o    /tmp/downloaded_file.txt    "
            "https://example.com/path/to/remote_file.txt" in result
        )
        assert "File Should Exist    /tmp/downloaded_file.txt" in result
        assert "Remove File    /tmp/downloaded_file.txt" in result

    def test_get_file_json_parsing_error_handling(self):
        """Tests error handling for malformed get_file.json-style data."""
        # Test missing testScript
        invalid_data1 = {
            "projectKey": "PROJ",
            "name": "Test",
            "description": "Test description",
        }

        converter = JsonToRobotConverter()
        result1 = converter.convert_json_data(invalid_data1)
        assert "No Operation  # Placeholder for missing steps" in result1
