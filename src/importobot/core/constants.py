"""Shared constants used across the importobot core modules."""

# Field name constants for expected results
EXPECTED_RESULT_FIELD_NAMES: list[str] = [
    "expectedResult",
    "expectedresult",
    "expected_result",
    "expected",
    "result",
]

# Test data field names
TEST_DATA_FIELD_NAMES: list[str] = [
    "testData",
    "testdata",
    "test_data",
    "data",
    "input",
]

# Step description field names
STEP_DESCRIPTION_FIELD_NAMES: list[str] = [
    "step",
    "description",
    "action",
    "stepDescription",
    "step_description",
]

# Test container field names (for finding test arrays in JSON)
TEST_CONTAINER_FIELD_NAMES: frozenset[str] = frozenset(
    [
        "tests",
        "testcases",
        "test_cases",
    ]
)

# Single test case wrapper field names
TEST_CASE_WRAPPER_FIELD_NAMES: frozenset[str] = frozenset(
    [
        "test_case",
        "testcase",
    ]
)

# Test script structure field names
TEST_SCRIPT_FIELD_NAMES: frozenset[str] = frozenset(
    [
        "testScript",
        "test_script",
        "script",
    ]
)

# Steps array field name (canonical)
STEPS_FIELD_NAME: str = "steps"

# Parameters field names
PARAMETERS_FIELD_NAMES: frozenset[str] = frozenset(
    [
        "parameters",
        "params",
        "variables",
    ]
)

# Robot Framework formatting constants
ROBOT_FRAMEWORK_ARGUMENT_SEPARATOR = "    "  # 4 spaces for argument separation
ROBOT_FRAMEWORK_INDENT = "    "  # 4 spaces for indentation
