"""Implements components for parsing test files."""

from typing import Any

from importobot.core.constants import (
    STEPS_FIELD_NAME,
    TEST_CASE_WRAPPER_FIELD_NAMES,
    TEST_CONTAINER_FIELD_NAMES,
)
from importobot.core.field_definitions import (
    TEST_SCRIPT_FIELDS,
    TEST_STEP_FIELDS,
    is_test_case,
)
from importobot.core.interfaces import TestFileParser
from importobot.utils.logging import get_logger

logger = get_logger()


class GenericTestFileParser(TestFileParser):
    """A generic parser to handle various JSON test formats programmatically."""

    def __init__(self) -> None:
        """Initialize the parser with a cached set of step field names."""
        super().__init__()
        self._step_field_names_cache = frozenset(
            field.lower() for field in TEST_STEP_FIELDS.fields
        )

    def find_tests(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify test structures within JSON data regardless of format."""
        if not isinstance(data, dict):
            return []

        tests = []

        # Strategy 1: Look for explicit test arrays
        for key, value in data.items():
            key_lower = key.lower()
            if isinstance(value, list) and key_lower in TEST_CONTAINER_FIELD_NAMES:
                tests.extend([t for t in value if isinstance(t, dict)])
            elif (
                key_lower in TEST_CASE_WRAPPER_FIELD_NAMES
                and isinstance(value, dict)
                and is_test_case(value)
            ):
                # Strategy 3: Look inside test_case/testCase key
                tests.append(value)

        # Strategy 2: Single test case (has name + steps or testScript)
        if not tests and is_test_case(data):
            tests.append(data)

        return tests

    def _get_step_field_names(self) -> frozenset[str]:
        """Retrieve the cached set of step field names."""
        # Using an instance-level cache to avoid lru_cache on methods
        return self._step_field_names_cache

    def find_steps(self, test_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify step structures within the provided test data."""
        steps = []
        step_field_names = self._get_step_field_names()
        script_field_names = {name.lower() for name in TEST_SCRIPT_FIELDS.fields}

        def search_for_steps(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, list) and key.lower() in step_field_names:
                        steps.extend([s for s in value if isinstance(s, dict)])
                    elif key.lower() in script_field_names and isinstance(value, dict):
                        potential_steps = value.get(STEPS_FIELD_NAME)
                        if isinstance(potential_steps, list):
                            steps.extend(
                                [s for s in potential_steps if isinstance(s, dict)]
                            )
                    elif isinstance(value, dict):
                        search_for_steps(value)
            elif isinstance(obj, list):
                for item in obj:
                    search_for_steps(item)

        search_for_steps(test_data)
        return steps
