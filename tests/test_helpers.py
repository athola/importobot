"""Helper functions for testing Robot Framework content."""

import re
from collections.abc import Iterable

EXPECTED_PUBLIC_EXPORTS = {
    "JsonToRobotConverter",
    "config",
    "exceptions",
    "api",
    "convert",
    "convert_directory",
    "convert_file",
}


def assert_module_exports(module: object, expected: Iterable[str]) -> None:
    """Assert that a module exposes exactly the expected `__all__` entries."""

    exports = getattr(module, "__all__", None)
    assert exports is not None, "Module is missing __all__ definition"
    assert set(exports) == set(expected), (
        f"Unexpected exports: {sorted(exports)} != {sorted(expected)}"
    )


class RobotFrameworkAssertion:
    """Helper class for semantic Robot Framework content assertions."""

    def __init__(self, content: str):
        """Initialize with Robot Framework content."""
        self.content = content
        self.lines = [line.strip() for line in content.splitlines() if line.strip()]

    def has_settings_section(self) -> bool:
        """Check if content has a Settings section."""
        return any(line.startswith("*** Settings ***") for line in self.lines)

    def has_test_cases_section(self) -> bool:
        """Check if content has a Test Cases section."""
        return any(line.startswith("*** Test Cases ***") for line in self.lines)

    def has_library_import(self, library: str) -> bool:
        """Check if content imports a specific library."""
        library_pattern = re.compile(f"Library\\s+{re.escape(library)}", re.IGNORECASE)
        return any(library_pattern.search(line) for line in self.lines)

    def get_library_imports(self) -> set[str]:
        """Get all library imports from the content."""
        libraries = set()
        library_pattern = re.compile(r"Library\s+(\w+)", re.IGNORECASE)
        for line in self.lines:
            match = library_pattern.search(line)
            if match:
                libraries.add(match.group(1))
        return libraries

    def has_test_case(self, test_name: str) -> bool:
        """Check if content has a specific test case."""
        return any(line.strip() == test_name for line in self.lines)

    def get_test_cases(self) -> list[str]:
        """Get all test case names from the content."""
        test_cases = []
        in_test_section = False
        for line in self.lines:
            if line.startswith("*** Test Cases ***"):
                in_test_section = True
                continue
            if line.startswith("***") and in_test_section:
                break
            if in_test_section and not line.startswith((" ", "\t", "#", "[")):
                # Test case names are not indented and don't start with special chars
                test_cases.append(line.strip())
        return test_cases

    def has_keyword(self, keyword: str) -> bool:
        """Check if content contains a specific keyword."""
        keyword_pattern = re.compile(f"^\\s*{re.escape(keyword)}", re.IGNORECASE)
        return any(keyword_pattern.search(line) for line in self.lines)

    def get_keywords_used(self) -> set[str]:
        """Get all keywords used in the content (heuristic approach)."""
        keywords = set()
        in_test_section = False
        for line in self.lines:
            if line.startswith("*** Test Cases ***"):
                in_test_section = True
                continue
            if line.startswith("***") and in_test_section:
                break
            if (
                in_test_section
                and line.startswith((" ", "\t"))
                and not line.strip().startswith("#")
            ):
                # This is likely a keyword line
                # Extract the first word/phrase as the keyword
                keyword_match = re.match(
                    r"\s*([A-Za-z][A-Za-z0-9\s]*[A-Za-z0-9])", line
                )
                if keyword_match:
                    keywords.add(keyword_match.group(1).strip())
        return keywords

    def has_documentation(self, doc_text: str | None = None) -> bool:
        """Check if content has documentation (optionally matching specific text)."""
        doc_pattern = re.compile(r"Documentation\s+(.+)", re.IGNORECASE)
        if doc_text is None:
            return any(doc_pattern.search(line) for line in self.lines)
        for line in self.lines:
            match = doc_pattern.search(line)
            if match and doc_text.lower() in match.group(1).lower():
                return True
        return False

    def has_tags(self, *tags: str) -> bool:
        """Check if content has specific tags."""
        tag_pattern = re.compile(r"Force Tags\s+(.+)", re.IGNORECASE)
        for line in self.lines:
            match = tag_pattern.search(line)
            if match:
                found_tags = [tag.strip() for tag in match.group(1).split()]
                return all(tag in found_tags for tag in tags)
        return False

    def count_comments(self) -> int:
        """Count comment lines in the content."""
        return sum(1 for line in self.lines if line.strip().startswith("#"))

    def has_security_warnings(self) -> bool:
        """Check if content contains security warnings."""
        return any(
            "WARNING" in line and "Security Warning" in line for line in self.lines
        )


def assert_robot_content_equivalent(generated: str, expected: str) -> None:
    """Assert that generated Robot Framework content is equivalent to expected.

    Args:
        generated: Generated Robot Framework content
        expected: Expected Robot Framework content
    """
    # Semantic comparison
    gen_robot = RobotFrameworkAssertion(generated)
    exp_robot = RobotFrameworkAssertion(expected)

    # Check structural elements
    assert gen_robot.has_settings_section() == exp_robot.has_settings_section(), (
        "Settings section mismatch"
    )
    assert gen_robot.has_test_cases_section() == exp_robot.has_test_cases_section(), (
        "Test Cases section mismatch"
    )

    # Check library imports
    gen_libs = gen_robot.get_library_imports()
    exp_libs = exp_robot.get_library_imports()
    assert gen_libs == exp_libs, (
        f"Library imports mismatch. Generated: {gen_libs}, Expected: {exp_libs}"
    )

    # Check test cases exist
    gen_tests = gen_robot.get_test_cases()
    exp_tests = exp_robot.get_test_cases()
    assert set(gen_tests) == set(exp_tests), (
        f"Test cases mismatch. Generated: {gen_tests}, Expected: {exp_tests}"
    )

    # Check keywords are used
    gen_keywords = gen_robot.get_keywords_used()
    exp_keywords = exp_robot.get_keywords_used()
    # Allow generated content to have additional keywords (like security warnings)
    missing_keywords = exp_keywords - gen_keywords
    assert not missing_keywords, f"Missing expected keywords: {missing_keywords}"


def assert_robot_framework_syntax_valid(content: str) -> bool:
    """Assert that Robot Framework content has valid basic syntax."""
    robot = RobotFrameworkAssertion(content)

    # Basic structural requirements
    assert robot.has_settings_section() or robot.has_test_cases_section(), (
        "Content must have at least Settings or Test Cases section"
    )

    # If it has test cases, it should have at least one
    if robot.has_test_cases_section():
        test_cases = robot.get_test_cases()
        assert len(test_cases) > 0, "Test Cases section exists but no test cases found"

    return True
