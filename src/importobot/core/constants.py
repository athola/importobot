"""Shared constants used across the importobot core modules."""

from typing import List

# Field name constants for expected results
EXPECTED_RESULT_FIELD_NAMES: List[str] = [
    "expectedResult",
    "expectedresult",
    "expected_result",
    "expected",
    "result",
]

# Test data field names
TEST_DATA_FIELD_NAMES: List[str] = [
    "testData",
    "testdata",
    "test_data",
    "data",
    "input",
]

# Step description field names
STEP_DESCRIPTION_FIELD_NAMES: List[str] = [
    "step",
    "description",
    "action",
    "stepDescription",
    "step_description",
]
