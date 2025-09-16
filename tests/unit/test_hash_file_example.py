"""Test for parsing and converting the hash_file.json example."""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from importobot.core.converter import convert_file, get_conversion_suggestions
from tests.utils import validate_test_script_structure


class TestHashFileExample:
    """Tests for parsing and converting the hash_file.json example."""

    def test_hash_file_json_structure_validation(self):
        """Tests that hash_file.json has expected structure."""
        hash_file_path = (
            Path(__file__).parent.parent.parent / "examples" / "json" / "hash_file.json"
        )

        with open(hash_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate top-level structure (it's an array with one test case)
        assert isinstance(data, list)
        assert len(data) == 1
        test_case = data[0]

        # Validate test case structure
        assert "projectKey" in test_case
        assert "name" in test_case
        assert "objective" in test_case
        assert "priority" in test_case
        assert "labels" in test_case
        assert "testScript" in test_case

        # Validate test script structure
        test_script = test_case["testScript"]
        validate_test_script_structure(test_script)

        # Validate steps structure
        for step in test_script["steps"]:
            assert "description" in step
            assert "testData" in step
            assert "expectedResult" in step

    def test_hash_file_json_conversion_generates_valid_robot_content(self):
        """Tests that hash_file.json generates valid Robot Framework content."""
        hash_file_path = (
            Path(__file__).parent.parent.parent / "examples" / "json" / "hash_file.json"
        )

        # Create a temporary directory for conversion
        with tempfile.TemporaryDirectory() as tmpdir:
            # Read the JSON file and extract the first test case
            with open(hash_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # The file contains an array, extract the first test case
            assert isinstance(data, list), (
                "Expected JSON to contain an array of test cases"
            )
            assert len(data) > 0, "Expected at least one test case"
            test_case = data[0]

            # Write the test case as a single object to a temporary file
            temp_json_file = Path(tmpdir) / "single_test_case.json"
            with open(temp_json_file, "w", encoding="utf-8") as f:
                json.dump(test_case, f, indent=2)

            output_robot_file = Path(tmpdir) / "hash_file_test.robot"

            # Convert the JSON file to Robot Framework
            convert_file(str(temp_json_file), str(output_robot_file))

            # Verify the Robot Framework file was created
            assert output_robot_file.exists(), "Output robot file was not created"

            # Read the generated content
            with open(output_robot_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Validate Robot Framework structure
            assert "*** Settings ***" in content
            assert "*** Test Cases ***" in content
            assert "Documentation" in content

            # Validate specific content from hash_file.json
            assert "hash" in content  # Test case name
            assert "Verify hashes match" in content  # Objective
            assert "# Step: In the target machine's terminal, create a file" in content
            assert (
                "# Step: In the target machine's terminal, get the sha of the new file"
                in content
            )
            assert "# Step: Use the hash command on the CLI" in content

            # Validate that Process library is imported (for echo command)
            assert "Library    Process" in content

    def test_hash_file_robot_content_executes_without_syntax_errors(self):
        """Tests that the generated Robot Framework file executes without
        syntax errors."""
        hash_file_path = (
            Path(__file__).parent.parent.parent / "examples" / "json" / "hash_file.json"
        )

        # Create a temporary directory for conversion and execution
        with tempfile.TemporaryDirectory() as tmpdir:
            # Read the JSON file and extract the first test case
            with open(hash_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # The file contains an array, extract the first test case
            assert isinstance(data, list), (
                "Expected JSON to contain an array of test cases"
            )
            assert len(data) > 0, "Expected at least one test case"
            test_case = data[0]

            # Write the test case as a single object to a temporary file
            temp_json_file = Path(tmpdir) / "single_test_case.json"
            with open(temp_json_file, "w", encoding="utf-8") as f:
                json.dump(test_case, f, indent=2)

            output_robot_file = Path(tmpdir) / "hash_file_test.robot"

            # Convert the JSON file to Robot Framework
            convert_file(str(temp_json_file), str(output_robot_file))

            # Verify the Robot Framework file was created
            assert output_robot_file.exists(), "Output robot file was not created"

            # Run Robot Framework dry run to check syntax
            try:
                result = subprocess.run(
                    [
                        "robot",
                        "--dryrun",
                        "--outputdir",
                        tmpdir,
                        str(output_robot_file),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,  # We check return code explicitly below
                )

                # Check that Robot Framework executed successfully (exit code 0)
                # Note: We're checking for syntax validity, not test execution success
                assert result.returncode == 0, (
                    f"Robot Framework dry run failed with exit code "
                    f"{result.returncode}. "
                    f"STDOUT: {result.stdout} STDERR: {result.stderr}"
                )

            except subprocess.TimeoutExpired:
                pytest.fail("Robot Framework execution timed out")
            except FileNotFoundError:
                pytest.skip("Robot Framework not found, skipping execution test")

    def test_hash_file_robot_content_contains_expected_keywords(self):
        """Tests that the generated Robot Framework file contains expected keywords."""
        hash_file_path = (
            Path(__file__).parent.parent.parent / "examples" / "json" / "hash_file.json"
        )

        # Create a temporary directory for conversion
        with tempfile.TemporaryDirectory() as tmpdir:
            # Read the JSON file and extract the first test case
            with open(hash_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # The file contains an array, extract the first test case
            assert isinstance(data, list), (
                "Expected JSON to contain an array of test cases"
            )
            assert len(data) > 0, "Expected at least one test case"
            test_case = data[0]

            # Write the test case as a single object to a temporary file
            temp_json_file = Path(tmpdir) / "single_test_case.json"
            with open(temp_json_file, "w", encoding="utf-8") as f:
                json.dump(test_case, f, indent=2)

            output_robot_file = Path(tmpdir) / "hash_file_test.robot"

            # Convert the JSON file to Robot Framework
            convert_file(str(temp_json_file), str(output_robot_file))

            # Read the generated content
            with open(output_robot_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Should contain Run Process keywords for the echo and hash commands
            # The echo command should be converted to a Run Process
            assert "Run Process" in content

            # Should contain test data from the steps
            assert "echo" in content
            assert "sha256sum" in content
            assert "hash" in content

            # Should contain expected results as comments
            assert "File created" in content
            assert "Hash matches that from step 2" in content
            assert "The sha256sum is shown" in content

    def test_hash_file_conversion_provides_helpful_suggestions(self):
        """Tests that the converter provides helpful suggestions for improving
        test data."""
        hash_file_path = (
            Path(__file__).parent.parent.parent / "examples" / "json" / "hash_file.json"
        )

        # Read the JSON file and extract the first test case
        with open(hash_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # The file contains an array, extract the first test case
        test_case = data[0]

        # Get conversion suggestions
        suggestions = get_conversion_suggestions(test_case)

        # Should provide at least one suggestion (the test data has some issues)
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

        # Check for specific suggestions
        suggestion_texts = " ".join(suggestions).lower()
        # Should mention the missing closing brace in the "hash" command
        assert (
            "missing closing braces" in suggestion_texts
            or "unmatched braces" in suggestion_texts
        )

    def test_conversion_suggestions_displayed_in_correct_order(self):
        """Tests that conversion suggestions are displayed in the correct
        numerical order, even when there are 10 or more steps."""
        # Load the many steps test file
        many_steps_file = Path(__file__).parent / "test_data" / "many_steps_test.json"
        with open(many_steps_file, "r", encoding="utf-8") as f:
            test_case = json.load(f)

        # Get conversion suggestions
        suggestions = get_conversion_suggestions(test_case)

        # Should be a list
        assert isinstance(suggestions, list)

        # Find step-related suggestions and verify they're in order
        step_suggestions = []
        import re  # pylint: disable=import-outside-toplevel

        for suggestion in suggestions:
            # Look for patterns like "Step 1:", "Step 2:", etc.
            match = re.search(r"[Ss]tep\s+(\d+)", suggestion)
            if match:
                step_number = int(match.group(1))
                step_suggestions.append((step_number, suggestion))

        # If we have step suggestions, verify they're in numerical order
        if step_suggestions:
            step_numbers = [num for num, _ in step_suggestions]
            # Sort them to check if they're already in order
            sorted_numbers = sorted(step_numbers)

            # Verify that the order is correct
            assert step_numbers == sorted_numbers, (
                f"Step suggestions should be in numerical order but got {step_numbers}"
            )

            # Specifically check that numbers increment properly
            # (testing order correctness)
            for i in range(len(step_numbers) - 1):
                assert step_numbers[i] < step_numbers[i + 1], (
                    f"Step numbers should be in ascending order: {step_numbers}"
                )

            # Verify that we have the correct sequence (1, 2, 3, ..., N)
            expected_sequence = list(range(1, len(step_numbers) + 1))
            assert step_numbers == expected_sequence, (
                f"Step numbers should form sequence 1,2,3,... but got {step_numbers}"
            )

            # This specifically tests that ordering handles 2-digit numbers correctly
            # (e.g., step 10 comes after step 9, not after step 1)
            if len(step_numbers) >= 10:
                # Make sure step 9 comes before step 10
                nine_index = step_numbers.index(9) if 9 in step_numbers else -1
                ten_index = step_numbers.index(10) if 10 in step_numbers else -1
                if nine_index != -1 and ten_index != -1:
                    assert nine_index < ten_index, (
                        "Step 9 should come before step 10 in ordering"
                    )
