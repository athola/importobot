"""Implementation of test file parsing components."""

from typing import Any

from importobot.core.field_definitions import TEST_STEP_FIELDS, is_test_case
from importobot.core.interfaces import TestFileParser
from importobot.utils.logging import setup_logger

logger = setup_logger(__name__)


class GenericTestFileParser(TestFileParser):
    """Generic parser that handles any JSON test format programmatically."""

    def __init__(self) -> None:
        """Initialize parser with step field names cache."""
        super().__init__()
        self._step_field_names_cache = frozenset(
            field.lower() for field in TEST_STEP_FIELDS.fields
        )

    def find_tests(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Find test structures anywhere in JSON, regardless of format."""
        if not isinstance(data, dict):
            return []

        tests = []

        # Strategy 1: Look for explicit test arrays
        for key, value in data.items():
            key_lower = key.lower()
            if isinstance(value, list) and key_lower in [
                "tests",
                "testcases",
                "test_cases",
            ]:
                tests.extend([t for t in value if isinstance(t, dict)])
            elif key_lower in ["test_case", "testcase"] and isinstance(value, dict):
                # Strategy 3: Look inside test_case/testCase key
                if is_test_case(value):
                    tests.append(value)

        # Strategy 2: Single test case (has name + steps or testScript)
        if not tests and is_test_case(data):
            tests.append(data)

        return tests

    def _get_step_field_names(self) -> frozenset:
        """Get cached set of step field names."""
        # Using an instance-level cache to avoid lru_cache on methods
        return self._step_field_names_cache

    def find_steps(self, test_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Find step structures anywhere in test data."""
        steps = []
        step_field_names = self._get_step_field_names()

        def search_for_steps(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, list) and key.lower() in step_field_names:
                        steps.extend([s for s in value if isinstance(s, dict)])
                    elif (
                        key.lower() == "testscript"
                        and isinstance(value, dict)
                        and "steps" in value
                    ):
                        # Handle testScript.steps structure
                        if isinstance(value["steps"], list):
                            steps.extend(
                                [s for s in value["steps"] if isinstance(s, dict)]
                            )
                    elif isinstance(value, dict):
                        search_for_steps(value)
            elif isinstance(obj, list):
                for item in obj:
                    search_for_steps(item)

        search_for_steps(test_data)
        return steps
