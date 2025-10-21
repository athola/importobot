"""
Benchmarks for test case conversion operations in importobot.

These benchmarks measure the performance of converting various test export
formats (Zephyr, TestLink, Xray) into Robot Framework files across different
file sizes and complexity levels.
"""

import json
import tempfile
from pathlib import Path


class ZephyrConversionSuite:
    """Benchmark suite for Zephyr JSON to Robot Framework conversion."""

    timeout = 120.0

    def setup(self):
        """Create Zephyr test fixtures of varying complexity."""
        # Single test case with minimal steps
        self.single_simple = {
            "testCase": {
                "name": "Simple Login Test",
                "description": "Verify basic login functionality",
                "priority": "High",
                "steps": [
                    {
                        "stepDescription": "Navigate to login page",
                        "expectedResult": "Login page displays correctly",
                    },
                    {
                        "stepDescription": "Enter valid credentials",
                        "expectedResult": "Credentials accepted",
                    },
                ],
            }
        }

        # Multiple test cases with moderate complexity
        self.multiple_moderate = {
            "testCases": [
                {
                    "name": f"Test Case {i}",
                    "description": f"Test description for case {i}",
                    "priority": ["High", "Medium", "Low"][i % 3],
                    "tags": [f"tag{j}" for j in range(3)],
                    "steps": [
                        {
                            "stepDescription": f"Step {j} action for test {i}",
                            "expectedResult": f"Step {j} expected result",
                            "testData": f"Data for step {j}",
                        }
                        for j in range(5)
                    ],
                }
                for i in range(20)
            ]
        }

        # Large suite with complex nested structures
        self.large_complex = {
            "testCases": [
                {
                    "name": f"Complex Integration Test {i}",
                    "description": f"Comprehensive test scenario {i}\n" * 5,
                    "priority": "Critical",
                    "component": f"Component {i % 5}",
                    "tags": ["integration", f"component{i % 5}", f"priority{i % 3}"],
                    "preconditions": f"Setup precondition {i}",
                    "steps": [
                        {
                            "stepDescription": f"Detailed step {j} for test {i}",
                            "expectedResult": f"Expected outcome for step {j}",
                            "testData": f"Test data: {j * 100}",
                            "attachments": [f"screenshot{k}.png" for k in range(2)],
                        }
                        for j in range(15)
                    ],
                    "customFields": {f"field{k}": f"value{k}" for k in range(5)},
                }
                for i in range(100)
            ]
        }

        # Create temporary files
        self.temp_dir = tempfile.mkdtemp()

        self.simple_file = Path(self.temp_dir) / "simple_zephyr.json"
        self.moderate_file = Path(self.temp_dir) / "moderate_zephyr.json"
        self.complex_file = Path(self.temp_dir) / "complex_zephyr.json"

        with open(self.simple_file, "w") as f:
            json.dump(self.single_simple, f, indent=2)
        with open(self.moderate_file, "w") as f:
            json.dump(self.multiple_moderate, f, indent=2)
        with open(self.complex_file, "w") as f:
            json.dump(self.large_complex, f, indent=2)

        # Output files
        self.simple_output = Path(self.temp_dir) / "simple_output.robot"
        self.moderate_output = Path(self.temp_dir) / "moderate_output.robot"
        self.complex_output = Path(self.temp_dir) / "complex_output.robot"

    def teardown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def time_convert_simple_single_test(self):
        """Benchmark converting a single simple test case."""
        import importobot

        converter = importobot.JsonToRobotConverter()
        converter.convert_file(str(self.simple_file), str(self.simple_output))

    def time_convert_moderate_multiple_tests(self):
        """Benchmark converting 20 moderate complexity test cases."""
        import importobot

        converter = importobot.JsonToRobotConverter()
        converter.convert_file(str(self.moderate_file), str(self.moderate_output))

    def time_convert_large_complex_suite(self):
        """Benchmark converting 100 complex test cases with metadata."""
        import importobot

        converter = importobot.JsonToRobotConverter()
        converter.convert_file(str(self.complex_file), str(self.complex_output))

    def peakmem_convert_large_suite(self):
        """Memory usage for converting large test suite."""
        import importobot

        converter = importobot.JsonToRobotConverter()
        converter.convert_file(str(self.complex_file), str(self.complex_output))


class DirectoryConversionSuite:
    """Benchmark suite for bulk directory conversion operations."""

    timeout = 180.0
    params = [5, 10, 25]
    param_names = ["num_files"]

    def setup(self, num_files):
        """Create directory with multiple test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = Path(self.temp_dir) / "input"
        self.output_dir = Path(self.temp_dir) / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()

        # Create multiple files in input directory
        for i in range(num_files):
            test_data = {
                "testCase": {
                    "name": f"Test {i}",
                    "steps": [
                        {
                            "stepDescription": f"Step {j}",
                            "expectedResult": f"Result {j}",
                        }
                        for j in range(5)
                    ],
                }
            }

            file_path = self.input_dir / f"test_{i}.json"
            with open(file_path, "w") as f:
                json.dump(test_data, f)

    def teardown(self, num_files):
        """Clean up directory structure."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def time_convert_directory(self, num_files):
        """Benchmark recursive directory conversion."""
        import importobot

        converter = importobot.JsonToRobotConverter()
        # Assuming directory conversion method exists
        # converter.convert_directory(str(self.input_dir), str(self.output_dir))

        # Fallback: convert files individually
        for json_file in self.input_dir.glob("*.json"):
            output_file = self.output_dir / f"{json_file.stem}.robot"
            converter.convert_file(str(json_file), str(output_file))


class ValidationSuite:
    """Benchmark suite for input validation and error detection."""

    timeout = 60.0

    def setup(self):
        """Create valid and invalid test fixtures."""
        self.valid_data = {
            "testCase": {
                "name": "Valid Test",
                "steps": [{"stepDescription": "step", "expectedResult": "result"}],
            }
        }

        self.invalid_missing_fields = {
            "testCase": {
                "name": "Invalid Test"
                # Missing steps
            }
        }

        self.invalid_malformed = {"testCase": {"name": None, "steps": "not an array"}}

        self.temp_dir = tempfile.mkdtemp()

        self.valid_file = Path(self.temp_dir) / "valid.json"
        self.invalid_missing_file = Path(self.temp_dir) / "invalid_missing.json"
        self.invalid_malformed_file = Path(self.temp_dir) / "invalid_malformed.json"

        with open(self.valid_file, "w") as f:
            json.dump(self.valid_data, f)
        with open(self.invalid_missing_file, "w") as f:
            json.dump(self.invalid_missing_fields, f)
        with open(self.invalid_malformed_file, "w") as f:
            json.dump(self.invalid_malformed, f)

    def teardown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def time_validate_valid_input(self):
        """Benchmark validation of valid test input."""
        import importobot

        converter = importobot.JsonToRobotConverter()
        output = Path(self.temp_dir) / "output.robot"
        converter.convert_file(str(self.valid_file), str(output))

    def time_validate_invalid_input(self):
        """Benchmark validation and error handling for invalid input."""
        import importobot

        converter = importobot.JsonToRobotConverter()
        output = Path(self.temp_dir) / "output.robot"

        try:
            converter.convert_file(str(self.invalid_missing_file), str(output))
        except Exception:
            pass  # Expected to fail validation
