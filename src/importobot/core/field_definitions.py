"""Centralizes field definitions for test case parsing and conversion."""

from dataclasses import dataclass
from typing import Any

from importobot.core.constants import EXPECTED_RESULT_FIELD_NAMES, TEST_DATA_FIELD_NAMES


@dataclass(frozen=True)
class FieldGroup:
    """Represents a collection of field names serving a common purpose."""

    fields: tuple[str, ...]
    description: str

    def __contains__(self, item: str) -> bool:
        """Check if a given field name exists within this group."""
        return item.lower() in (f.lower() for f in self.fields)

    def find_first(self, data: dict[str, Any]) -> tuple[str | None, Any]:
        """Find the first matching field in data and returns its name and value."""
        for field in self.fields:
            if data.get(field):
                return field, data[field]
        return None, None


# Test case field groups
TEST_NAME_FIELDS = FieldGroup(
    fields=("name", "title", "testname", "summary"),
    description="Test case name or title",
)

TEST_DESCRIPTION_FIELDS = FieldGroup(
    fields=("description", "objective", "documentation"),
    description="Test case description or documentation",
)

TEST_TAG_FIELDS = FieldGroup(
    fields=("tags", "labels", "categories", "priority"),
    description="Test categorization and tagging",
)

TEST_STEP_FIELDS = FieldGroup(
    fields=("steps", "teststeps", "actions"), description="Test execution steps"
)

# Test script structure field group
TEST_SCRIPT_FIELDS = FieldGroup(
    fields=("testScript", "test_script", "script"),
    description="Test script structure containing steps",
)

# Parameters field group
PARAMETERS_FIELDS = FieldGroup(
    fields=("parameters", "params", "variables"),
    description="Test case parameters and variables",
)

# Step field groups
STEP_ACTION_FIELDS = FieldGroup(
    fields=("step", "description", "action", "instruction"),
    description="Step action or instruction",
)

STEP_DATA_FIELDS = FieldGroup(
    fields=tuple(TEST_DATA_FIELD_NAMES),
    description="Step input data",
)

STEP_EXPECTED_FIELDS = FieldGroup(
    fields=tuple(EXPECTED_RESULT_FIELD_NAMES),
    description="Step expected result",
)

# Zephyr-specific field groups
ZEPHYR_DETAILS_FIELDS = FieldGroup(
    fields=("status", "priority", "component", "owner", "estimatedTime", "folder"),
    description="Zephyr test case details and metadata",
)

ZEPHYR_PRECONDITION_FIELDS = FieldGroup(
    fields=("precondition", "preconditions", "setup", "requirements"),
    description="Test setup requirements and preconditions",
)

ZEPHYR_TRACEABILITY_FIELDS = FieldGroup(
    fields=("issues", "confluence", "webLinks", "linkedCRS", "requirements"),
    description="Test case traceability and requirement links",
)

ZEPHYR_LEVEL_FIELDS = FieldGroup(
    fields=("testLevel", "level", "importance", "criticality"),
    description="Test level and importance classification",
)

ZEPHYR_PLATFORM_FIELDS = FieldGroup(
    fields=("supportedPlatforms", "platforms", "targets"),
    description="Supported target platforms and architectures",
)

# Enhanced step structure for Zephyr's three-segment approach
ZEPHYR_STEP_STRUCTURE_FIELDS = FieldGroup(
    fields=("step", "testData", "expectedResult", "description", "actual"),
    description="Zephyr step structure with action, data, and expected result",
)

# Test structure indicators
TEST_INDICATORS = frozenset(
    [
        "name",
        "description",
        "steps",
        "testscript",
        "objective",
        "summary",
        "title",
        "testname",
        "precondition",
        "testLevel",
        "supportedPlatforms",
        "status",
        "priority",
    ]
)

# Library detection keywords
LIBRARY_KEYWORDS = {
    "SeleniumLibrary": frozenset(
        [
            "browser",
            "navigate",
            "click",
            "input",
            "page",
            "web",
            "url",
            "login",
            "button",
            "element",
            "selenium",
        ]
    ),
    "SSHLibrary": frozenset(["ssh", "remote", "connection", "host", "server"]),
    "Process": frozenset(
        ["command", "execute", "run", "curl", "wget", "bash", "process"]
    ),
    "OperatingSystem": frozenset(
        ["file", "directory", "exists", "remove", "delete", "filesystem"]
    ),
    "DatabaseLibrary": frozenset(
        [
            "database",
            "sql",
            "query",
            "table",
            "db_",
            "row",
            "insert",
            "update",
            "select",
            "from",
        ]
    ),
    "RequestsLibrary": frozenset(
        [
            "api",
            "rest",
            "request",
            "response",
            "session",
            "http",
            "get",
            "post",
            "put",
            "delete",
        ]
    ),
    "Collections": frozenset(["list", "dictionary", "collection", "append", "dict"]),
    "String": frozenset(
        ["string", "uppercase", "lowercase", "replace", "split", "strip"]
    ),
}


def get_field_value(data: dict[str, Any], field_group: FieldGroup) -> str:
    """Extract the value from the first matching field within the specified group."""
    _, value = field_group.find_first(data)
    return str(value) if value else ""


def has_field(data: dict[str, Any], field_group: FieldGroup) -> bool:
    """Check if the provided data contains any field from the specified group."""
    return any(field in data and data[field] for field in field_group.fields)


def detect_libraries_from_text(text: str) -> set[str]:
    """Detect required libraries based on the provided text content."""
    text_lower = text.lower()
    text_words = set(text_lower.split())

    detected_libraries = set()
    for library, keywords in LIBRARY_KEYWORDS.items():
        if keywords & text_words:
            detected_libraries.add(library)

    return detected_libraries


# Zephyr-specific indicators
ZEPHYR_TEST_INDICATORS = frozenset(
    ["testscript", "precondition", "testlevel", "supportedplatforms", "objective"]
)


def is_test_case(data: Any) -> bool:
    """Determine if the provided data resembles a test case structure."""
    if not isinstance(data, dict):
        return False
    return bool(TEST_INDICATORS & {key.lower() for key in data})


def is_zephyr_test_case(data: Any) -> bool:
    """Determine if the provided data adheres to the Zephyr test case structure."""
    if not isinstance(data, dict):
        return False

    zephyr_indicators = {
        "testscript",
        "precondition",
        "testlevel",
        "supportedplatforms",
        "objective",
    }

    data_keys = {key.lower() for key in data}
    return bool(zephyr_indicators & data_keys)
