"""Centralized field definitions for test case parsing and conversion."""

from dataclasses import dataclass
from typing import Any

from importobot.core.constants import EXPECTED_RESULT_FIELD_NAMES, TEST_DATA_FIELD_NAMES


@dataclass(frozen=True)
class FieldGroup:
    """Represents a group of field names that serve the same purpose."""

    fields: tuple
    description: str

    def __contains__(self, item: str) -> bool:
        """Check if a field name is in this group."""
        return item.lower() in (f.lower() for f in self.fields)

    def find_first(self, data: dict) -> tuple[str | None, Any]:
        """Find the first matching field in data and return (field_name, value)."""
        for field in self.fields:
            if field in data and data[field]:
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


def get_field_value(data: dict, field_group: FieldGroup) -> str:
    """Extract value from first matching field in group."""
    _, value = field_group.find_first(data)
    return str(value) if value else ""


def has_field(data: dict, field_group: FieldGroup) -> bool:
    """Check if data has any field from the group."""
    return any(field in data and data[field] for field in field_group.fields)


def detect_libraries_from_text(text: str) -> set[str]:
    """Detect required libraries from text content."""
    text_lower = text.lower()
    text_words = set(text_lower.split())

    detected_libraries = set()
    for library, keywords in LIBRARY_KEYWORDS.items():
        if keywords & text_words:
            detected_libraries.add(library)

    return detected_libraries


def is_test_case(data: Any) -> bool:
    """Check if data looks like a test case."""
    if not isinstance(data, dict):
        return False
    return bool(TEST_INDICATORS & {key.lower() for key in data.keys()})
