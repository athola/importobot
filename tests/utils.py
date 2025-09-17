"""Test utility functions."""

import subprocess
from typing import Any, Dict, List

from robot.api import TestSuite


def run_robot_command(command: List[str]) -> subprocess.CompletedProcess:
    """Execute a Robot Framework command and return the result."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Do not raise exception on non-zero exit code
        )
    except FileNotFoundError as err:
        # This handles the case where 'robot' command is not found
        raise RuntimeError(
            "Robot Framework command not found. "
            "Make sure it is installed and in your PATH."
        ) from err
    return result


def parse_robot_file(file_path: str) -> List[Dict[str, Any]]:
    """Parse a .robot file and extract test cases, keywords and their arguments."""
    suite = TestSuite.from_file_system(file_path)
    result = []

    def _extract_keywords(test_or_suite):
        """Recursively extract keywords from a test or suite."""
        keywords = []
        if hasattr(test_or_suite, "body"):
            for item in test_or_suite.body:
                if hasattr(item, "name") and item.name:
                    keywords.append(
                        {
                            "keyword": item.name,
                            "args": [str(arg) for arg in item.args],
                        }
                    )
        return keywords

    for test in suite.tests:
        test_info = {"name": test.name, "keywords": _extract_keywords(test)}
        result.append(test_info)

    return result


def validate_test_script_structure(test_script: Dict[str, Any]) -> None:
    """Validate the basic structure of a test script.

    Common validation logic extracted from multiple test files.
    """
    assert "type" in test_script
    assert test_script["type"] == "STEP_BY_STEP"
    assert "steps" in test_script
    assert isinstance(test_script["steps"], list)
    assert len(test_script["steps"]) > 0
