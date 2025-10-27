"""
Unit tests for conversion.py benchmark suite.

These tests ensure conversion benchmark setup/teardown work correctly and
benchmarks can run without errors. They validate fixture structure and
conversion pipeline functionality without measuring performance.
"""

import json
import sys
from pathlib import Path

import pytest

# Add benchmarks directory to path
benchmark_dir = Path(__file__).parent.parent.parent.parent / "benchmarks"
sys.path.insert(0, str(benchmark_dir))

from conversion import (  # noqa: E402
    DirectoryConversionSuite,
    ValidationSuite,
    ZephyrConversionSuite,
)


class TestZephyrConversionSuite:
    """Tests for ZephyrConversionSuite benchmark class."""

    def test_setup_creates_all_files(self):
        """Verify setup creates simple, moderate, and complex test files."""
        suite = ZephyrConversionSuite()
        suite.setup()

        try:
            assert suite.simple_file.exists(), "Simple file not created"
            assert suite.moderate_file.exists(), "Moderate file not created"
            assert suite.complex_file.exists(), "Complex file not created"

            # Verify files have content
            assert suite.simple_file.stat().st_size > 0
            assert suite.moderate_file.stat().st_size > 0
            assert suite.complex_file.stat().st_size > 0
        finally:
            suite.teardown()

    def test_teardown_removes_temp_directory(self):
        """Verify teardown cleans up all temporary files."""
        suite = ZephyrConversionSuite()
        suite.setup()
        temp_dir = Path(suite.temp_dir)

        suite.teardown()

        assert not temp_dir.exists(), "Temp directory not cleaned up"

    def test_simple_fixture_has_correct_structure(self):
        """Verify simple Zephyr fixture has expected structure."""
        suite = ZephyrConversionSuite()
        suite.setup()

        try:
            with open(suite.simple_file) as f:
                data = json.load(f)

            assert "testCase" in data
            assert "name" in data["testCase"]
            assert "description" in data["testCase"]
            assert "steps" in data["testCase"]
            assert len(data["testCase"]["steps"]) == 2

            # Verify step structure
            step = data["testCase"]["steps"][0]
            assert "stepDescription" in step
            assert "expectedResult" in step
        finally:
            suite.teardown()

    def test_moderate_fixture_has_multiple_tests(self):
        """Verify moderate fixture contains 20 test cases."""
        suite = ZephyrConversionSuite()
        suite.setup()

        try:
            with open(suite.moderate_file) as f:
                data = json.load(f)

            assert "testCases" in data
            assert len(data["testCases"]) == 20

            # Verify each test has steps
            for test_case in data["testCases"]:
                assert "steps" in test_case
                assert len(test_case["steps"]) == 5
        finally:
            suite.teardown()

    def test_complex_fixture_has_metadata(self):
        """Verify complex fixture includes rich metadata."""
        suite = ZephyrConversionSuite()
        suite.setup()

        try:
            with open(suite.complex_file) as f:
                data = json.load(f)

            assert "testCases" in data
            assert len(data["testCases"]) == 100

            # Verify metadata fields exist
            test_case = data["testCases"][0]
            assert "component" in test_case
            assert "tags" in test_case
            assert "preconditions" in test_case
            assert "customFields" in test_case
            assert len(test_case["steps"]) == 15
        finally:
            suite.teardown()

    def test_time_convert_simple_single_test_runs(self):
        """Verify simple conversion benchmark runs without error."""
        suite = ZephyrConversionSuite()
        suite.setup()

        try:
            suite.time_convert_simple_single_test()
            # Verify output file was created
            assert suite.simple_output.exists(), "Output file not created"
        finally:
            suite.teardown()

    def test_time_convert_moderate_multiple_tests_runs(self):
        """Verify moderate conversion benchmark runs without error."""
        suite = ZephyrConversionSuite()
        suite.setup()

        try:
            suite.time_convert_moderate_multiple_tests()
            assert suite.moderate_output.exists(), "Output file not created"
        finally:
            suite.teardown()

    def test_time_convert_large_complex_suite_runs(self):
        """Verify large conversion benchmark runs without error."""
        suite = ZephyrConversionSuite()
        suite.setup()

        try:
            suite.time_convert_large_complex_suite()
            assert suite.complex_output.exists(), "Output file not created"
        finally:
            suite.teardown()

    def test_peakmem_convert_large_suite_runs(self):
        """Verify memory profiling benchmark runs without error."""
        suite = ZephyrConversionSuite()
        suite.setup()

        try:
            suite.peakmem_convert_large_suite()
            assert suite.complex_output.exists(), "Output file not created"
        finally:
            suite.teardown()


class TestDirectoryConversionSuite:
    """Tests for DirectoryConversionSuite benchmark class."""

    @pytest.mark.parametrize("num_files", [5, 10, 25])
    def test_setup_creates_multiple_files(self, num_files):
        """Verify setup creates correct number of input files."""
        suite = DirectoryConversionSuite()
        suite.setup(num_files)

        try:
            assert suite.input_dir.exists(), "Input directory not created"
            assert suite.output_dir.exists(), "Output directory not created"

            # Count JSON files in input directory
            json_files = list(suite.input_dir.glob("*.json"))
            assert len(json_files) == num_files, (
                f"Expected {num_files} files, found {len(json_files)}"
            )

            # Verify each file has content
            for json_file in json_files:
                assert json_file.stat().st_size > 0
        finally:
            suite.teardown(num_files)

    @pytest.mark.parametrize("num_files", [5])
    def test_time_convert_directory_runs(self, num_files):
        """Verify directory conversion benchmark runs (test with small count)."""
        suite = DirectoryConversionSuite()
        suite.setup(num_files)

        try:
            suite.time_convert_directory(num_files)

            # Verify output files were created
            output_files = list(suite.output_dir.glob("*.robot"))
            assert len(output_files) > 0, "No output files created"
        finally:
            suite.teardown(num_files)

    def test_input_files_have_valid_structure(self):
        """Verify generated input files have valid test case structure."""
        suite = DirectoryConversionSuite()
        suite.setup(5)

        try:
            for json_file in suite.input_dir.glob("*.json"):
                with open(json_file) as f:
                    data = json.load(f)

                assert "testCase" in data
                assert "name" in data["testCase"]
                assert "steps" in data["testCase"]
                assert len(data["testCase"]["steps"]) == 5
        finally:
            suite.teardown(5)


class TestValidationSuite:
    """Tests for ValidationSuite benchmark class."""

    def test_setup_creates_valid_and_invalid_files(self):
        """Verify setup creates both valid and invalid test fixtures."""
        suite = ValidationSuite()
        suite.setup()

        try:
            assert suite.valid_file.exists(), "Valid file not created"
            assert suite.invalid_missing_file.exists(), (
                "Invalid missing file not created"
            )
            assert suite.invalid_malformed_file.exists(), (
                "Invalid malformed file not created"
            )
        finally:
            suite.teardown()

    def test_valid_fixture_has_correct_structure(self):
        """Verify valid fixture has proper test case structure."""
        suite = ValidationSuite()
        suite.setup()

        try:
            with open(suite.valid_file) as f:
                data = json.load(f)

            assert "testCase" in data
            assert "name" in data["testCase"]
            assert "steps" in data["testCase"]
            assert len(data["testCase"]["steps"]) > 0
        finally:
            suite.teardown()

    def test_invalid_missing_fixture_lacks_steps(self):
        """Verify invalid missing fields fixture is missing steps."""
        suite = ValidationSuite()
        suite.setup()

        try:
            with open(suite.invalid_missing_file) as f:
                data = json.load(f)

            assert "testCase" in data
            assert "steps" not in data["testCase"], (
                "Invalid fixture should be missing steps"
            )
        finally:
            suite.teardown()

    def test_invalid_malformed_fixture_has_wrong_types(self):
        """Verify invalid malformed fixture has incorrect data types."""
        suite = ValidationSuite()
        suite.setup()

        try:
            with open(suite.invalid_malformed_file) as f:
                data = json.load(f)

            assert "testCase" in data
            # Name is None instead of string
            assert data["testCase"]["name"] is None
            # Steps is string instead of array
            assert isinstance(data["testCase"]["steps"], str)
        finally:
            suite.teardown()

    def test_time_validate_valid_input_runs(self):
        """Verify validation of valid input runs without error."""
        suite = ValidationSuite()
        suite.setup()

        try:
            suite.time_validate_valid_input()
        finally:
            suite.teardown()

    def test_time_validate_invalid_input_runs(self):
        """Verify validation of invalid input runs (may fail gracefully)."""
        suite = ValidationSuite()
        suite.setup()

        try:
            # This benchmark should handle errors gracefully
            suite.time_validate_invalid_input()
        finally:
            suite.teardown()


class TestConversionBenchmarkIntegration:
    """Integration tests across conversion benchmark suites."""

    def test_all_suites_have_timeout(self):
        """Verify all conversion suites define timeout attribute."""
        suites = [
            ZephyrConversionSuite,
            DirectoryConversionSuite,
            ValidationSuite,
        ]

        for suite_class in suites:
            assert hasattr(suite_class, "timeout"), (
                f"{suite_class.__name__} missing timeout attribute"
            )
            assert isinstance(suite_class.timeout, (int, float))
            assert suite_class.timeout > 0

    def test_parameterized_suite_configuration(self):
        """Verify DirectoryConversionSuite has correct parameter config."""
        suite = DirectoryConversionSuite

        assert hasattr(suite, "params")
        assert hasattr(suite, "param_names")
        assert len(suite.param_names) == 1
        assert suite.param_names[0] == "num_files"
        assert suite.params == [5, 10, 25]

    def test_all_conversion_suites_follow_naming_convention(self):
        """Verify all conversion benchmarks follow ASV naming conventions."""
        suites = [
            ZephyrConversionSuite(),
            ValidationSuite(),
        ]

        for suite in suites:
            # Get all time_ methods
            time_methods = [m for m in dir(suite) if m.startswith("time_")]
            assert len(time_methods) > 0, (
                f"{suite.__class__.__name__} has no time_ benchmark methods"
            )

    def test_output_files_are_robot_format(self):
        """Verify conversion creates .robot extension files."""
        suite = ZephyrConversionSuite()
        suite.setup()

        try:
            assert suite.simple_output.suffix == ".robot"
            assert suite.moderate_output.suffix == ".robot"
            assert suite.complex_output.suffix == ".robot"
        finally:
            suite.teardown()

    def test_fixtures_scale_appropriately(self):
        """Verify test fixtures have appropriate size scaling."""
        suite = ZephyrConversionSuite()
        suite.setup()

        try:
            # Simple < Moderate < Complex
            simple_size = suite.simple_file.stat().st_size
            moderate_size = suite.moderate_file.stat().st_size
            complex_size = suite.complex_file.stat().st_size

            assert simple_size < moderate_size < complex_size, (
                "Fixture sizes should scale: simple < moderate < complex"
            )
        finally:
            suite.teardown()

    def test_all_suites_cleanup_properly(self):
        """Verify all suites clean up their temporary resources."""
        suites = [
            ZephyrConversionSuite(),
            ValidationSuite(),
        ]

        temp_dirs = []

        for suite in suites:
            suite.setup()
            temp_dirs.append(Path(suite.temp_dir))

        for suite in suites:
            suite.teardown()

        for temp_dir in temp_dirs:
            assert not temp_dir.exists(), f"Temp directory {temp_dir} not cleaned up"
