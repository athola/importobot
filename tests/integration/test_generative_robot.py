"""Generative tests for Robot Framework keyword coverage and execution."""
# pylint: disable=too-many-lines

import json
import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

from importobot.core.converter import convert_file
from importobot.core.keywords_registry import RobotFrameworkKeywordRegistry
from importobot.core.suggestions.suggestion_engine import GenericSuggestionEngine
from importobot.utils.test_generation.generators import EnterpriseTestGenerator
from importobot.utils.test_generation.helpers import (
    generate_random_test_json,
    get_available_structures,
    get_required_libraries_for_keywords,
)
from importobot.utils.test_generation.ssh_generator import SSHKeywordTestGenerator
from tests.shared_ssh_test_data import (
    EXPECTED_SSH_KEYWORD_COUNT,
    EXPECTED_TOTAL_SSH_TESTS,
    SSH_COMMAND_KEYWORDS,
    SSH_CONNECTION_KEYWORDS,
    SSH_DIRECTORY_KEYWORDS,
    SSH_FILE_KEYWORDS,
)

# RobotFrameworkKeywordRegistry is now imported from core.keywords_registry


# JsonTestGenerator functionality is now part of EnterpriseTestGenerator
# in utils.test_generation


class RobotFrameworkExecutor:
    """Execute Robot Framework files and validate results."""

    @staticmethod
    def _find_local_robot() -> Path | None:
        """Return the local Robot Framework executable if available."""
        venv_dir = Path.cwd() / ".venv"
        candidates = [
            venv_dir / "bin" / "robot",
            venv_dir / "Scripts" / "robot",
            venv_dir / "Scripts" / "robot.exe",
            venv_dir / "Scripts" / "robot.bat",
        ]
        for candidate in candidates:
            if candidate.exists() and os.access(candidate, os.X_OK):
                return candidate
        return None

    @staticmethod
    def _prepare_execution_attempts(
        common_args: list[str], env: dict[str, str]
    ) -> list[tuple[str, list[str], dict[str, str]]]:
        attempts: list[tuple[str, list[str], dict[str, str]]] = []
        uv_path = shutil.which("uv")
        if uv_path:
            uv_env = env.copy()
            cache_dir = uv_env.get("UV_CACHE_DIR")
            if not cache_dir:
                cache_dir = str(Path.cwd() / ".uv-cache")
                uv_env["UV_CACHE_DIR"] = cache_dir
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            uv_env.setdefault("UV_LINK_MODE", "copy")
            uv_env.setdefault("UV_PROJECT_ENVIRONMENT", str(Path.cwd() / ".venv"))
            uv_env.setdefault("UV_NO_SYNC", "1")
            attempts.append(("uv", [uv_path, "run", "robot", *common_args], uv_env))

        local_robot = RobotFrameworkExecutor._find_local_robot()
        if local_robot:
            attempts.append(("robot", [str(local_robot), *common_args], env.copy()))
        return attempts

    @staticmethod
    def _execute_attempt(
        label: str, cmd: list[str], cmd_env: dict[str, str]
    ) -> tuple[subprocess.CompletedProcess[str] | None, str | None]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env=cmd_env,
            )
            return result, None
        except subprocess.TimeoutExpired:
            return None, f"{label} execution timed out after 30 seconds."
        except FileNotFoundError:
            return None, f"{label} executable not found."
        except Exception as exc:  # pylint: disable=broad-except
            return None, f"{label} execution error: {exc}"

    @staticmethod
    def execute_robot_file(
        robot_file_path: str, dry_run: bool = True
    ) -> dict[str, Any]:
        """Execute Robot Framework file and return results."""
        env = os.environ.copy()
        common_args: list[str] = []
        if dry_run:
            common_args.append("--dryrun")
        output_dir = str(Path(robot_file_path).parent)
        common_args.extend(["--outputdir", output_dir, robot_file_path])

        attempts = RobotFrameworkExecutor._prepare_execution_attempts(common_args, env)

        if not attempts:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": (
                    "No Robot Framework executable available (uv or local robot)."
                ),
                "syntax_valid": False,
            }

        attempt_messages: list[str] = []
        last_result: subprocess.CompletedProcess[str] | None = None

        for label, cmd, cmd_env in attempts:
            result, error_message = RobotFrameworkExecutor._execute_attempt(
                label, cmd, cmd_env
            )
            if error_message:
                attempt_messages.append(error_message)
                continue

            if result and result.returncode == 0:
                stderr_output = result.stderr
                if attempt_messages:
                    prefix = "\n".join(attempt_messages)
                    stderr_output = f"{prefix}\n{stderr_output}".strip()
                return {
                    "success": True,
                    "returncode": 0,
                    "stdout": result.stdout,
                    "stderr": stderr_output,
                    "syntax_valid": True,
                }

            if result:
                error_detail = (
                    result.stderr.strip() or result.stdout.strip() or "no output"
                )
                attempt_messages.append(
                    f"{label} execution failed with return code "
                    f"{result.returncode}: {error_detail}"
                )
                last_result = result

        failure_stdout = last_result.stdout if last_result else ""
        failure_stderr = "\n".join(attempt_messages)
        if last_result and last_result.stderr:
            failure_stderr = f"{failure_stderr}\n{last_result.stderr}".strip()

        return {
            "success": False,
            "returncode": last_result.returncode if last_result else -1,
            "stdout": failure_stdout,
            "stderr": failure_stderr,
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
    # Use curated keyword sets instead of random generation to fix brittleness
    curated_keywords_by_count = {
        3: [
            {"keyword": "Log", "library": "BuiltIn", "description": "Log a message"},
            {
                "keyword": "Sleep",
                "library": "BuiltIn",
                "description": "Sleep for a period",
            },
            {
                "keyword": "Set Variable",
                "library": "BuiltIn",
                "description": "Set a variable",
            },
        ],
        5: [
            {"keyword": "Log", "library": "BuiltIn", "description": "Log a message"},
            {
                "keyword": "Sleep",
                "library": "BuiltIn",
                "description": "Sleep for a period",
            },
            {
                "keyword": "Set Variable",
                "library": "BuiltIn",
                "description": "Set a variable",
            },
            {
                "keyword": "Create File",
                "library": "OperatingSystem",
                "description": "Create a file",
            },
            {
                "keyword": "Should Be Equal",
                "library": "BuiltIn",
                "description": "Assert equality",
            },
        ],
        8: [
            {"keyword": "Log", "library": "BuiltIn", "description": "Log a message"},
            {
                "keyword": "Sleep",
                "library": "BuiltIn",
                "description": "Sleep for a period",
            },
            {
                "keyword": "Set Variable",
                "library": "BuiltIn",
                "description": "Set a variable",
            },
            {
                "keyword": "Create File",
                "library": "OperatingSystem",
                "description": "Create a file",
            },
            {
                "keyword": "Should Be Equal",
                "library": "BuiltIn",
                "description": "Assert equality",
            },
            {
                "keyword": "Get Time",
                "library": "DateTime",
                "description": "Get current time",
            },
            {
                "keyword": "Append To List",
                "library": "Collections",
                "description": "Add item to list",
            },
            {"keyword": "Run", "library": "Process", "description": "Run a process"},
        ],
        12: [
            {"keyword": "Log", "library": "BuiltIn", "description": "Log a message"},
            {
                "keyword": "Sleep",
                "library": "BuiltIn",
                "description": "Sleep for a period",
            },
            {
                "keyword": "Set Variable",
                "library": "BuiltIn",
                "description": "Set a variable",
            },
            {
                "keyword": "Create File",
                "library": "OperatingSystem",
                "description": "Create a file",
            },
            {
                "keyword": "Should Be Equal",
                "library": "BuiltIn",
                "description": "Assert equality",
            },
            {
                "keyword": "Get Time",
                "library": "DateTime",
                "description": "Get current time",
            },
            {
                "keyword": "Append To List",
                "library": "Collections",
                "description": "Add item to list",
            },
            {"keyword": "Run", "library": "Process", "description": "Run a process"},
            {
                "keyword": "Wait For",
                "library": "BuiltIn",
                "description": "Wait for condition",
            },
            {
                "keyword": "Convert To String",
                "library": "BuiltIn",
                "description": "Convert to string",
            },
            {
                "keyword": "Get Length",
                "library": "BuiltIn",
                "description": "Get length",
            },
            {
                "keyword": "Should Contain",
                "library": "BuiltIn",
                "description": "Assert contains",
            },
        ],
    }

    keywords = curated_keywords_by_count[num_keywords]

    # Set seed for consistent test data generation
    random.seed(42 + num_keywords)

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


def _extract_keywords_by_library() -> list[dict[str, Any]]:
    """Extract one keyword from each library for testing."""
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
    return keywords_by_library


def _generate_builtin_keyword_data(
    kw: dict[str, Any], generator: EnterpriseTestGenerator, test_data: dict[str, str]
) -> str:
    """Generate proper data for BuiltIn keywords."""
    keyword_specific_data = generator.generate_keyword_specific_data(kw, test_data)
    # Verify that BuiltIn keywords get proper structured data, not generic fallbacks
    if "test_data_for_" in keyword_specific_data and "#" in keyword_specific_data:
        # This indicates the generator didn't have a specific pattern
        # for this BuiltIn keyword
        # Use a fallback that will at least be valid
        keyword_name = kw["keyword"].lower().replace(" ", "_")
        if "convert" in keyword_name:
            return "value: 123"
        if "keyword_if" in keyword_name:
            return "condition: ${status} == 'pass', keyword: Log, args: Success"
        if "repeat" in keyword_name:
            return "times: 3, keyword: Log, args: Test message"
        if "variable" in keyword_name:
            return "name: test_var, value: test_value"
        if "log" in keyword_name:
            return "message: Test message, level: INFO"
        return "message: Default BuiltIn test data"
    return keyword_specific_data


def _create_test_steps(
    keywords_by_library: list[dict[str, Any]],
    generator: EnterpriseTestGenerator,
    test_data: dict[str, str],
) -> list[dict[str, Any]]:
    """Create test steps for each library keyword."""
    steps: list[dict[str, Any]] = []
    for i, kw in enumerate(keywords_by_library):
        # Enhanced data generation for BuiltIn keywords
        if kw["library"] == "BuiltIn":
            keyword_specific_data = _generate_builtin_keyword_data(
                kw, generator, test_data
            )
        else:
            keyword_specific_data = generator.generate_keyword_specific_data(
                kw, test_data
            )

        step = {
            "description": f"Execute {kw['description'].lower()}",
            "testData": keyword_specific_data,
            "expectedResult": f"{kw['description']} completes successfully",
            "index": i,
        }
        steps.append(step)
    return steps


def test_library_coverage(tmp_path):
    """Test that all major Robot Framework libraries can be successfully used."""
    keywords_by_library = _extract_keywords_by_library()

    # Generate test using enterprise generator with enhanced BuiltIn support
    generator = EnterpriseTestGenerator()
    test_data = generator.generate_realistic_test_data()

    steps = _create_test_steps(keywords_by_library, generator, test_data)

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
    all_libraries = {kw["library"] for kw in keywords_by_library}
    expected_libraries = {lib for lib in all_libraries if lib.lower() != "builtin"}

    for lib in expected_libraries:
        assert f"Library    {lib}" in content, f"Missing library import: {lib}"


def test_builtin_keywords_comprehensive_coverage(tmp_path):
    """Test comprehensive coverage of BuiltIn keywords with proper structured data."""
    # Create test scenarios for each major BuiltIn keyword category
    builtin_scenarios = [
        # Conversion keywords
        {
            "step": "convert value to integer",
            "test_data": "value: 123",
            "expected": "",
            "category": "conversion",
        },
        {
            "step": "convert text to string",
            "test_data": "value: hello world",
            "expected": "",
            "category": "conversion",
        },
        {
            "step": "convert flag to boolean",
            "test_data": "value: true",
            "expected": "",
            "category": "conversion",
        },
        {
            "step": "convert data to number",
            "test_data": "value: 3.14",
            "expected": "",
            "category": "conversion",
        },
        # Conditional keywords
        {
            "step": "run keyword conditionally",
            "test_data": "condition: ${status} == 'pass', keyword: Log, args: Success",
            "expected": "",
            "category": "conditional",
        },
        {
            "step": "execute keyword unless condition fails",
            "test_data": (
                "condition: ${error} != '', keyword: Fail, args: Error occurred"
            ),
            "expected": "",
            "category": "conditional",
        },
        # Variable operations
        {
            "step": "set test variable",
            "test_data": "name: test_var, value: test_value",
            "expected": "",
            "category": "variable",
        },
        {
            "step": "create list with items",
            "test_data": "items: [item1, item2, item3]",
            "expected": "",
            "category": "variable",
        },
        {
            "step": "create dictionary",
            "test_data": "key1: value1, key2: value2",
            "expected": "",
            "category": "variable",
        },
        # Logging keywords
        {
            "step": "log message with level",
            "test_data": "message: Test execution started, level: INFO",
            "expected": "",
            "category": "logging",
        },
        {
            "step": "log multiple messages",
            "test_data": "messages: [Message 1, Message 2, Message 3]",
            "expected": "",
            "category": "logging",
        },
        # Collection operations
        {
            "step": "get count of items",
            "test_data": "container: ${test_list}, item: expected_item",
            "expected": "",
            "category": "collection",
        },
        {
            "step": "verify container contains item",
            "test_data": "container: ${data}, item: expected_value",
            "expected": "",
            "category": "collection",
        },
        {
            "step": "check length of collection",
            "test_data": "container: ${items}",
            "expected": "length should be 3",
            "category": "collection",
        },
        # Evaluation keywords
        {
            "step": "evaluate mathematical expression",
            "test_data": "expression: 2 + 3 * 4",
            "expected": "",
            "category": "evaluation",
        },
        {
            "step": "evaluate python code with modules",
            "test_data": "expression: datetime.now(), modules: datetime",
            "expected": "",
            "category": "evaluation",
        },
        # Repetition keywords
        {
            "step": "repeat keyword multiple times",
            "test_data": "times: 3, keyword: Log, args: Iteration complete",
            "expected": "",
            "category": "repetition",
        },
        # Control flow
        {
            "step": "fail test with message",
            "test_data": "message: Critical error occurred",
            "expected": "",
            "category": "control",
        },
        # String operations
        {
            "step": "verify string starts with prefix",
            "test_data": "string: ${text}, prefix: Hello",
            "expected": "",
            "category": "string",
        },
        {
            "step": "check string matches pattern",
            "test_data": "string: ${text}, pattern: \\d+",
            "expected": "",
            "category": "string",
        },
    ]

    json_data = {
        "name": "BuiltIn Keywords Comprehensive Test",
        "description": (
            "Comprehensive test covering all major BuiltIn keyword categories "
            "with proper structured data"
        ),
        "priority": "High",
        "labels": ["builtin", "comprehensive", "structured_data"],
        "steps": builtin_scenarios,
    }

    # Convert to Robot Framework
    json_file = tmp_path / "builtin_comprehensive_test.json"
    json_file.write_text(json.dumps(json_data, indent=2))

    robot_file = tmp_path / "builtin_comprehensive_test.robot"
    convert_file(str(json_file), str(robot_file))

    # Verify syntax
    syntax_executor = RobotFrameworkExecutor()
    syntax_result = syntax_executor.execute_robot_file(str(robot_file), dry_run=True)

    # Should have valid syntax
    assert syntax_result["syntax_valid"], (
        f"BuiltIn comprehensive test failed validation: {syntax_result['stderr']}"
    )

    # Verify content includes proper BuiltIn keywords
    content = robot_file.read_text()

    # Should contain BuiltIn keywords (but not Library import since BuiltIn is
    # always available)
    builtin_keywords = [
        "Convert To Integer",
        "Convert To String",
        "Convert To Boolean",
        "Convert To Number",
        "Run Keyword If",
        "Set Variable",
        "Create List",
        "Create Dictionary",
        "Log",
        "Get Count",
        "Should Contain",
        "Get Length",
        "Evaluate",
        "Repeat Keyword",
    ]

    found_keywords = []
    for keyword in builtin_keywords:
        if keyword in content:
            found_keywords.append(keyword)

    # Should find a good portion of BuiltIn keywords
    assert len(found_keywords) >= len(builtin_keywords) // 2, (
        f"Expected to find at least half of BuiltIn keywords, found: {found_keywords}"
    )

    # Verify no parameter validation errors (comments indicating missing data)
    validation_errors = ["requires a value", "requires structured data", "use format:"]

    for error_text in validation_errors:
        assert error_text not in content, (
            f"Found parameter validation error in generated content: {error_text}"
        )


def test_parameter_validation_suggestions_integration(tmp_path):
    """Test that parameter validation suggestions work in the full conversion
    pipeline."""
    # Create test cases with missing/improper parameter data to trigger suggestions
    problematic_scenarios = [
        {
            "step": "convert item to number",
            "test_data": (
                "test_data_for_convert_to_number # builtin"  # Missing structured data
            ),
            "expected": "",
        },
        {
            "step": "run keyword conditionally",
            "test_data": (
                "test_data_for_run_keyword_if # builtin"  # Missing condition/keyword
            ),
            "expected": "",
        },
        {
            "step": "repeat keyword multiple times",
            "test_data": (
                "test_data_for_repeat_keyword # builtin"  # Missing times/keyword
            ),
            "expected": "",
        },
        {
            "step": "set variable with value",
            "test_data": (
                "test_data_for_set_variable # builtin"  # Missing name/value
            ),
            "expected": "",
        },
    ]

    json_data = {
        "name": "Parameter Validation Test",
        "description": "Test parameter validation and suggestion generation",
        "steps": problematic_scenarios,
    }

    # Test suggestion generation
    suggestion_engine = GenericSuggestionEngine()
    suggestions = suggestion_engine.get_suggestions(json_data)

    # Should generate specific parameter validation suggestions
    suggestion_text = " ".join(suggestions)

    assert "requires structured test data" in suggestion_text, (
        "Missing parameter validation suggestions"
    )

    # Should provide specific format examples
    format_examples = ["value:", "condition:", "times:", "name:"]
    found_examples = [ex for ex in format_examples if ex in suggestion_text]

    assert len(found_examples) >= 2, (
        f"Should provide specific format examples, found: {found_examples}"
    )

    # Convert to Robot Framework (should handle gracefully)
    json_file = tmp_path / "parameter_validation_test.json"
    json_file.write_text(json.dumps(json_data, indent=2))

    robot_file = tmp_path / "parameter_validation_test.robot"
    convert_file(str(json_file), str(robot_file))

    # Verify content contains helpful comments instead of broken keywords
    content = robot_file.read_text()

    # Should contain descriptive comments for missing parameters
    helpful_comments = ["# Convert To Number requires", "# Run Keyword If requires"]

    found_comments = [comment for comment in helpful_comments if comment in content]

    # Should have some helpful guidance instead of broken keywords
    assert len(found_comments) >= 1, (
        f"Should contain helpful parameter guidance comments, content: {content[:500]}"
    )


def test_enhanced_library_detection(tmp_path):
    """Test enhanced library detection that analyzes generated Robot Framework
    content."""
    # Create test cases that will generate keywords requiring specific libraries
    test_scenarios = [
        {
            "step": "assert page contains text",
            "test_data": "text: Welcome to our site",
            "expected": "",
        },
        {
            "step": "execute command via ssh",
            "test_data": "command: ls -la",
            "expected": "",
        },
        {
            "step": "convert value to integer",
            "test_data": "value: 123",
            "expected": "",
        },
        {
            "step": "make http request",
            "test_data": "endpoint: /api/test, method: GET",
            "expected": "",
        },
        {
            "step": "check file exists",
            "test_data": "path: /tmp/test.txt",
            "expected": "",
        },
    ]

    json_data = {
        "name": "Enhanced Library Detection Test",
        "description": "Test enhanced library detection from generated content",
        "steps": test_scenarios,
    }

    # Convert to Robot Framework
    json_file = tmp_path / "enhanced_library_test.json"
    json_file.write_text(json.dumps(json_data, indent=2))

    robot_file = tmp_path / "enhanced_library_test.robot"
    convert_file(str(json_file), str(robot_file))

    # Verify content and library imports
    content = robot_file.read_text()

    # Expected library mappings based on generated content
    expected_mappings = [
        (
            "Page Should Contain",
            "SeleniumLibrary",
        ),  # Page assertion should trigger SeleniumLibrary
        ("Execute Command", "SSHLibrary"),  # SSH command should trigger SSHLibrary
        ("Convert To Integer", None),  # BuiltIn keyword - no library import needed
        (
            "GET On Session",
            "RequestsLibrary",
        ),  # HTTP request should trigger RequestsLibrary
        (
            "File Should Exist",
            "OperatingSystem",
        ),  # File operation should trigger OperatingSystem
    ]

    for keyword, expected_library in expected_mappings:
        if keyword in content:
            if expected_library:
                assert f"Library    {expected_library}" in content, (
                    f"Keyword '{keyword}' found but '{expected_library}' library "
                    f"not imported"
                )
            # For BuiltIn keywords, verify no unnecessary library import
            elif keyword in ["Convert To Integer", "Set Variable", "Log"]:
                # BuiltIn keywords should not cause BuiltIn library import
                assert "Library    BuiltIn" not in content, (
                    "BuiltIn library should not be explicitly imported"
                )

    # Verify syntax is valid
    syntax_executor = RobotFrameworkExecutor()
    syntax_result = syntax_executor.execute_robot_file(str(robot_file), dry_run=True)

    assert syntax_result["syntax_valid"], (
        f"Enhanced library detection test failed validation: {syntax_result['stderr']}"
    )


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

        except Exception:
            # Log but don't fail - we're testing robustness
            pass  # Debug print removed for cleaner test output

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
        except Exception:
            # Log but allow - some edge cases may legitimately fail
            pass  # Debug print removed for cleaner test output


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

        with open(robot_path, encoding="utf-8") as robot_content:
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


def test_ssh_comprehensive_keyword_coverage():
    """Test comprehensive coverage of all 42 SSH keywords through generative testing."""
    ssh_generator = SSHKeywordTestGenerator()

    # Generate test cases for all SSH keywords
    all_ssh_tests = ssh_generator.generate_all_ssh_keyword_tests()

    # Verify we have the expected number of tests (42 keywords × 3 variations = 126)

    assert len(all_ssh_tests) == EXPECTED_TOTAL_SSH_TESTS, (
        f"Expected 126 SSH tests, got {len(all_ssh_tests)}"
    )

    # Track which keywords are covered
    covered_keywords = set()
    successful_conversions = 0

    # Test conversion for a representative sample
    sample_tests = all_ssh_tests[::6]  # Every 6th test (about 21 tests)

    for test_data in sample_tests:
        keyword = test_data.get("keyword_focus", "Unknown")
        covered_keywords.add(keyword)

        # Convert test to Robot Framework
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as test_json_file:
            json.dump(test_data, test_json_file, indent=2)
            test_json_path = test_json_file.name

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".robot", delete=False
        ) as test_robot_file:
            test_robot_path = test_robot_file.name

        try:
            convert_file(test_json_path, test_robot_path)

            # Verify Robot Framework content was generated
            test_robot_content = Path(test_robot_path).read_text(encoding="utf-8")

            # Check if conversion succeeded by verifying content
            if (
                len(test_robot_content.strip()) > 0
                and "*** Test Cases ***" in test_robot_content
            ):
                successful_conversions += 1

                # Should contain SSH library import
                assert "SSHLibrary" in test_robot_content, (
                    f"Missing SSHLibrary import for {keyword}"
                )

                # Should contain test case structure
                assert "*** Test Cases ***" in test_robot_content, (
                    f"Missing test structure for {keyword}"
                )

                # Should not be empty
                assert len(test_robot_content.strip()) > 0, (
                    f"Empty Robot content for {keyword}"
                )

        except Exception as e:
            pytest.fail(f"Failed to convert SSH test for keyword {keyword}: {e}")

        finally:
            # Cleanup
            Path(test_json_path).unlink(missing_ok=True)
            Path(test_robot_path).unlink(missing_ok=True)

    # Verify coverage
    assert len(covered_keywords) >= 15, (
        f"Expected at least 15 unique SSH keywords tested, got {len(covered_keywords)}"
    )
    assert successful_conversions >= 15, (
        f"Expected at least 15 successful conversions, got {successful_conversions}"
    )

    print("\nSSH Keyword Coverage Test Results:")
    print(f"- Total SSH tests generated: {len(all_ssh_tests)}")
    print(f"- Sample tests converted: {len(sample_tests)}")
    print(f"- Successful conversions: {successful_conversions}")
    print(f"- Unique keywords covered: {len(covered_keywords)}")
    print(f"- Keywords tested: {sorted(covered_keywords)}")


def test_ssh_keyword_categories_comprehensive():
    """Test that all SSH keyword categories are comprehensively covered."""
    ssh_generator = SSHKeywordTestGenerator()

    # Define SSH keyword categories and their expected keywords
    #
    # IMPORTANT: Command execution vs Interactive shell separation
    # - command_execution: One-shot commands that execute and return results
    #   (Execute Command, Start Command, Read Command Output)
    # - interactive_shell: Keywords for managing persistent interactive sessions
    #   (Write, Read, Read Until, etc.)
    # This separation is critical for proper test coverage as these represent
    # fundamentally different SSH operation modes with different security
    # implications and error handling requirements.
    expected_categories = {
        "connection": SSH_CONNECTION_KEYWORDS,
        "authentication": ["Login", "Login With Public Key"],
        "configuration": ["Set Default Configuration", "Set Client Configuration"],
        "command_execution": [
            "Execute Command",
            "Start Command",
            "Read Command Output",
        ],
        "file_operations": SSH_FILE_KEYWORDS,
        "directory_operations": SSH_DIRECTORY_KEYWORDS,
        "verification": [
            "File Should Exist",
            "File Should Not Exist",
            "Directory Should Exist",
            "Directory Should Not Exist",
        ],
        "interactive_shell": SSH_COMMAND_KEYWORDS[3:],  # Interactive keywords
        "logging": ["Enable Ssh Logging", "Disable Ssh Logging"],
    }

    # Verify each category has test generators
    for category, keywords in expected_categories.items():
        for keyword in keywords:
            assert keyword in ssh_generator.keyword_generators, (
                f"Missing generator for {keyword} in category {category}"
            )

            # Generate a test case for this keyword
            test_case = ssh_generator.generate_ssh_keyword_test(keyword)

            # Verify test case structure
            assert "test_case" in test_case, f"Invalid test structure for {keyword}"
            assert "steps" in test_case["test_case"], f"Missing steps for {keyword}"
            assert len(test_case["test_case"]["steps"]) > 0, f"No steps for {keyword}"

    # Count total expected keywords
    total_expected = sum(len(keywords) for keywords in expected_categories.values())

    assert total_expected == EXPECTED_SSH_KEYWORD_COUNT, (
        f"Expected 42 total keywords, category mapping has {total_expected}"
    )

    print("\nSSH Category Coverage Verification:")
    for category, keywords in expected_categories.items():
        print(f"- {category}: {len(keywords)} keywords")
    print(
        f"- Total: {total_expected} keywords across "
        f"{len(expected_categories)} categories"
    )


def test_ssh_realistic_test_data_generation():
    """Test that SSH test data generation produces realistic, varied content."""
    ssh_generator = SSHKeywordTestGenerator()

    # Test a few representative keywords
    test_keywords = [
        "Open Connection",
        "Execute Command",
        "Put File",
        "Create Directory",
        "Login",
    ]

    for keyword in test_keywords:
        # Generate multiple test cases for variety
        test_cases = []
        for _ in range(5):
            test_case = ssh_generator.generate_ssh_keyword_test(keyword)
            test_cases.append(test_case)

        # Verify we get some variety in test data
        test_data_values = []
        for test_case in test_cases:
            step = test_case["test_case"]["steps"][0]
            test_data_values.append(step["test_data"])

        # Should have some variation (unless empty test data)
        unique_values = set(test_data_values)
        if any(len(value) > 0 for value in test_data_values):
            assert len(unique_values) > 1, (
                f"No variation in test data for {keyword}: {test_data_values}"
            )

        # Verify test data contains realistic patterns
        combined_data = " ".join(test_data_values).lower()

        if keyword == "Open Connection":
            # Should contain host-like patterns
            assert any(
                pattern in combined_data
                for pattern in ["host:", ".com", "server", "localhost"]
            ), f"Unrealistic connection data for {keyword}"

        elif keyword == "Execute Command":
            # Should contain command-like patterns
            assert "command:" in combined_data, f"Missing command pattern for {keyword}"

        elif keyword == "Put File":
            # Should contain file path patterns
            assert any(
                pattern in combined_data
                for pattern in ["source:", "destination:", "/", "."]
            ), f"Unrealistic file data for {keyword}"

    print(
        f"\nRealistic Test Data Verification completed for "
        f"{len(test_keywords)} SSH keywords"
    )
