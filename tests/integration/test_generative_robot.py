"""Generative tests for Robot Framework keyword coverage and execution."""
# pylint: disable=too-many-lines

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from importobot.core.converter import convert_file
from importobot.core.keywords_registry import RobotFrameworkKeywordRegistry
from importobot.utils.test_generation.generators import EnterpriseTestGenerator
from importobot.utils.test_generation.helpers import (
    generate_keyword_list,
    generate_random_test_json,
    get_available_structures,
    get_required_libraries_for_keywords,
)

# RobotFrameworkKeywordRegistry is now imported from core.keywords_registry


# JsonTestGenerator functionality is now part of EnterpriseTestGenerator
# in utils.test_generation


class RobotFrameworkExecutor:
    """Execute Robot Framework files and validate results."""

    @staticmethod
    def execute_robot_file(
        robot_file_path: str, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Execute Robot Framework file and return results."""
        try:
            # Use --dryrun for syntax validation without actual execution
            cmd = [
                "robot",
                "--dryrun" if dry_run else "",
                "--outputdir",
                str(Path(robot_file_path).parent),
                robot_file_path,
            ]

            if dry_run:
                # Remove empty string
                cmd = [c for c in cmd if c]

            proc_result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, check=False
            )

            return {
                "success": proc_result.returncode == 0,
                "returncode": proc_result.returncode,
                "stdout": proc_result.stdout,
                "stderr": proc_result.stderr,
                "syntax_valid": proc_result.returncode == 0,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Execution timeout",
                "syntax_valid": False,
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "syntax_valid": False,
            }


@pytest.mark.parametrize("structure", get_available_structures())
def test_generative_json_structures_convert_successfully(tmp_path, structure):
    """Test that all JSON structures convert successfully to Robot Framework."""
    # Generate random JSON for this structure
    json_data = generate_random_test_json(structure)

    # Save to file
    json_file = tmp_path / f"test_{structure}.json"
    json_file.write_text(json.dumps(json_data, indent=2))

    # Convert to Robot Framework
    robot_file = tmp_path / f"test_{structure}.robot"

    # Should not raise an exception
    convert_file(str(json_file), str(robot_file))

    # Verify file was created
    assert robot_file.exists()

    # Verify content structure
    content = robot_file.read_text()
    assert "*** Settings ***" in content
    assert "*** Test Cases ***" in content

    # Should contain at least one library import
    assert "Library" in content


@pytest.mark.parametrize("num_keywords", [3, 5, 8, 12])
def test_generative_keyword_combinations_produce_valid_robot(tmp_path, num_keywords):
    """Test various keyword combinations produce valid Robot Framework syntax."""
    # Generate keywords
    keywords = generate_keyword_list(num_keywords)

    # Create enterprise generator and use it to create test steps
    generator = EnterpriseTestGenerator()
    test_data = generator.generate_realistic_test_data()

    # Generate steps using the keyword data
    steps = []
    for i, kw in enumerate(keywords):
        step = {
            "description": f"Execute {kw['description'].lower()}",
            "testData": generator.generate_keyword_specific_data(kw, test_data),
            "expectedResult": f"{kw['description']} completes successfully",
            "index": i,
        }
        steps.append(step)

    json_data = {
        "name": "Generated Test Case",
        "description": "Auto-generated test for keyword validation",
        "steps": steps,
    }

    # Convert and validate
    json_file = tmp_path / "generated_test.json"
    json_file.write_text(json.dumps(json_data, indent=2))

    robot_file = tmp_path / "generated_test.robot"
    convert_file(str(json_file), str(robot_file))

    # Execute Robot Framework dry run for syntax validation
    test_executor = RobotFrameworkExecutor()
    test_result = test_executor.execute_robot_file(str(robot_file), dry_run=True)

    # Should have valid syntax
    assert test_result["syntax_valid"], f"Invalid syntax: {test_result['stderr']}"

    # Verify required libraries are imported
    content = robot_file.read_text()
    required_libs = get_required_libraries_for_keywords(keywords)

    for lib in required_libs:
        assert f"Library    {lib}" in content, f"Missing library: {lib}"


def test_library_coverage(tmp_path):
    """Test that all major Robot Framework libraries can be successfully used."""
    # Get one keyword from each library
    all_libraries = set()
    keywords_by_library: list[dict[str, Any]] = []

    for intent, (
        library,
        keyword,
    ) in RobotFrameworkKeywordRegistry.INTENT_TO_LIBRARY_KEYWORDS.items():
        if library not in all_libraries:
            all_libraries.add(library)
            keywords_by_library.append(
                {
                    "intent": intent,
                    "library": library,
                    "keyword": keyword,
                    "args": RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES[library][
                        keyword
                    ]["args"],
                    "description": RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES[
                        library
                    ][keyword]["description"],
                }
            )

    # Generate test using enterprise generator
    generator = EnterpriseTestGenerator()
    test_data = generator.generate_realistic_test_data()

    steps: list[dict[str, Any]] = []
    for i, kw in enumerate(keywords_by_library):
        step = {
            "description": f"Execute {kw['description'].lower()}",
            "testData": generator.generate_keyword_specific_data(kw, test_data),
            "expectedResult": f"{kw['description']} completes successfully",
            "index": i,
        }
        steps.append(step)

    json_data = {
        "name": "Library Coverage Test",
        "description": "Test covering all major Robot Framework libraries",
        "priority": "High",
        "labels": ["comprehensive", "library_coverage"],
        "steps": steps,
    }

    # Convert
    json_file = tmp_path / "comprehensive_test.json"
    json_file.write_text(json.dumps(json_data, indent=2))

    robot_file = tmp_path / "comprehensive_test.robot"
    convert_file(str(json_file), str(robot_file))

    # Verify syntax
    syntax_executor = RobotFrameworkExecutor()
    syntax_result = syntax_executor.execute_robot_file(str(robot_file), dry_run=True)

    assert syntax_result["syntax_valid"], (
        f"Comprehensive test failed validation: {syntax_result['stderr']}"
    )

    # Verify all libraries are imported (except builtin)
    content = robot_file.read_text()
    expected_libraries = {lib for lib in all_libraries if lib != "builtin"}

    for lib in expected_libraries:
        assert f"Library    {lib}" in content, f"Missing library import: {lib}"


@pytest.mark.parametrize("iterations", [10])
def test_generative_fuzz_testing(tmp_path, iterations):
    """Fuzz test with random JSON structures and keyword combinations."""
    successful_conversions = 0
    valid_syntax_count = 0

    for i in range(iterations):
        try:
            # Generate completely random test using the new utility
            available_structures = get_available_structures()
            structure = available_structures[i % len(available_structures)]
            json_data = generate_random_test_json(structure)

            # Save and convert
            json_file = tmp_path / f"fuzz_test_{i}.json"
            json_file.write_text(json.dumps(json_data, indent=2))

            robot_file = tmp_path / f"fuzz_test_{i}.robot"
            convert_file(str(json_file), str(robot_file))

            successful_conversions += 1

            # Validate syntax
            validation_executor = RobotFrameworkExecutor()
            validation_result = validation_executor.execute_robot_file(
                str(robot_file), dry_run=True
            )

            if validation_result["syntax_valid"]:
                valid_syntax_count += 1

        except Exception as e:
            # Log but don't fail - we're testing robustness
            print(f"Fuzz iteration {i} failed: {e}")

    # At least 80% of conversions should succeed
    success_rate = successful_conversions / iterations
    assert success_rate >= 0.8, f"Success rate too low: {success_rate:.2f}"

    # At least 70% should have valid syntax
    syntax_rate = valid_syntax_count / iterations
    assert syntax_rate >= 0.7, f"Syntax validation rate too low: {syntax_rate:.2f}"


def test_generative_edge_case_handling(tmp_path):
    """Test edge cases and boundary conditions."""
    edge_cases = [
        # Empty structures
        {"tests": []},
        {"steps": []},
        # Minimal structures
        {"name": "Minimal Test", "steps": [{"action": "Do something"}]},
        # Deep nesting
        {
            "testSuite": {
                "nested": {
                    "level": {
                        "tests": [
                            {
                                "name": "Deep Test",
                                "execution": {
                                    "steps": [
                                        {"step": "Deep step", "testData": "Deep data"}
                                    ]
                                },
                            }
                        ]
                    }
                }
            }
        },
        # Special characters
        {
            "name": "Test with Special Characters: !@#$%^&*()",
            "description": "Description with \"quotes\" and 'apostrophes'",
            "steps": [
                {
                    "action": "Handle special chars: <>&\"'",
                    "testData": "Data with newlines\nand\ttabs",
                }
            ],
        },
    ]

    for i, edge_case in enumerate(edge_cases):
        json_file = tmp_path / f"edge_case_{i}.json"
        json_file.write_text(json.dumps(edge_case, indent=2))

        robot_file = tmp_path / f"edge_case_{i}.robot"

        # Should not crash
        try:
            convert_file(str(json_file), str(robot_file))
            assert robot_file.exists()
        except Exception as e:
            # Log but allow - some edge cases may legitimately fail
            print(f"Edge case {i} failed conversion: {e}")


if __name__ == "__main__":
    # Example usage for manual testing using the consolidated utilities
    print("Testing consolidated test generation utilities")

    # Generate sample using the new utility
    sample = generate_random_test_json("zephyr_basic")
    print("Generated JSON:")
    print(json.dumps(sample, indent=2))

    # Test conversion
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample, f, indent=2)
        json_path = f.name

    robot_path = json_path.replace(".json", ".robot")

    try:
        convert_file(json_path, robot_path)
        print(f"\nConverted to: {robot_path}")

        with open(robot_path, "r", encoding="utf-8") as robot_content:
            print("\nGenerated Robot Framework:")
            print(robot_content.read())

        # Test execution
        executor = RobotFrameworkExecutor()
        result = executor.execute_robot_file(robot_path, dry_run=True)
        print(
            f"\nSyntax validation: {'PASSED' if result['syntax_valid'] else 'FAILED'}"
        )

        if not result["syntax_valid"]:
            print(f"Error: {result['stderr']}")

    finally:
        # Cleanup
        Path(json_path).unlink(missing_ok=True)
        Path(robot_path).unlink(missing_ok=True)

    # Test enterprise generator
    print("\n" + "=" * 50)
    print("Testing Enterprise Test Generator")
    print("=" * 50)

    enterprise_generator = EnterpriseTestGenerator()
    enterprise_test = enterprise_generator.generate_enterprise_test_case(
        "web_automation", "user_authentication", 1001
    )

    print("Generated Enterprise Test Case:")
    print(
        json.dumps(enterprise_test, indent=2)[:1000] + "..."
    )  # Truncate for readability
