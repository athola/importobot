"""Integration tests for the converter."""

import json
import tempfile
from pathlib import Path

from importobot.core.converter import convert_to_robot


class TestIntegration:
    """Integration tests for the complete conversion process."""

    def test_end_to_end_conversion(self):
        """Test complete conversion from JSON to Robot Framework."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as input_file:
            sample_data = {
                "tests": [
                    {
                        "name": "Login Test",
                        "description": "Test user login functionality",
                        "steps": [
                            {
                                "action": "Open browser to login page",
                                "expectedResult": "Login page is displayed",
                            },
                            {
                                "action": "Enter valid credentials",
                                "expectedResult": "User is logged in",
                            },
                        ],
                    }
                ]
            }
            json.dump(sample_data, input_file)
            input_filename = input_file.name

        with tempfile.NamedTemporaryFile(delete=False) as output_file:
            output_filename = output_file.name

        try:
            # Perform conversion
            convert_to_robot(input_filename, output_filename)

            # Verify output
            with open(output_filename, "r", encoding="utf-8") as f:
                content = f.read()
                assert "*** Test Cases ***" in content
                assert "Login Test" in content
                assert "Test user login functionality" in content
                assert "Open browser to login page" in content
                assert "Login page is displayed" in content
        finally:
            # Cleanup
            Path(input_filename).unlink(missing_ok=True)
            Path(output_filename).unlink(missing_ok=True)

    def test_conversion_with_empty_input(self):
        """Test conversion with minimal JSON input."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as input_file:
            sample_data = {}
            json.dump(sample_data, input_file)
            input_filename = input_file.name

        with tempfile.NamedTemporaryFile(delete=False) as output_file:
            output_filename = output_file.name

        try:
            # Perform conversion
            convert_to_robot(input_filename, output_filename)

            # Verify output contains at least the basic structure
            with open(output_filename, "r", encoding="utf-8") as f:
                content = f.read()
                assert "*** Test Cases ***" in content
        finally:
            # Cleanup
            Path(input_filename).unlink(missing_ok=True)
            Path(output_filename).unlink(missing_ok=True)
