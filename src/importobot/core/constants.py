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

# Robot Framework formatting constants
ROBOT_FRAMEWORK_ARGUMENT_SEPARATOR = "    "  # 4 spaces for argument separation
ROBOT_FRAMEWORK_INDENT = "    "  # 4 spaces for indentation
