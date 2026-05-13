"""Tests for scanner pattern definitions and ScannerPatterns factory.

Covers ``importobot.security.scanner_patterns``: the suspicious variable
set, hardcoded-value pattern dicts, Robot-framework pattern dicts, safe
keyword set, placeholder indicators, severity-classification sets, and
the ``ScannerPatterns`` class that wires them together with merge
helpers.
"""

from __future__ import annotations

import re
from typing import Any, ClassVar

import pytest

from importobot.security import scanner_patterns
from importobot.security.scanner_patterns import (
    CRITICAL_SEVERITY_VARIABLES,
    HARDCODED_VALUE_PATTERNS,
    HIGH_SEVERITY_VARIABLES,
    PLACEHOLDER_INDICATORS,
    ROBOT_FRAMEWORK_PATTERNS,
    SAFE_KEYWORDS,
    SUSPICIOUS_VARIABLE_NAMES,
    ScannerPatterns,
)


class TestPatternConstants:
    """Module-level constants have the right shape and content."""

    def test_suspicious_variables_is_non_empty_set(self) -> None:
        assert isinstance(SUSPICIOUS_VARIABLE_NAMES, set)
        assert len(SUSPICIOUS_VARIABLE_NAMES) > 0
        # Core credential-flavoured names must be present; downstream
        # scanners rely on them.
        for required in ("password", "secret", "token", "api_key"):
            assert required in SUSPICIOUS_VARIABLE_NAMES

    def test_safe_keywords_is_non_empty_set(self) -> None:
        assert isinstance(SAFE_KEYWORDS, set)
        # Required markers that survive even with whole-word matching.
        for required in ("example", "demo", "sample", "placeholder", "dummy"):
            assert required in SAFE_KEYWORDS

    def test_safe_keywords_excludes_common_substrings(self) -> None:
        # PR #90 review B2: dictionary words that appear inside real
        # credential values must not be present, otherwise whole-word
        # matching alone is insufficient protection (an entry that's
        # both a substring of typical values and a stand-alone token
        # in many code lines is too lax). See SAFE_KEYWORDS docstring.
        for forbidden in ("test", "foo", "bar", "baz", "qux", "xxx"):
            assert forbidden not in SAFE_KEYWORDS

    def test_placeholder_indicators_is_tuple(self) -> None:
        # Tuple type is important — it's hashable and immutable, suiting
        # use as a default argument elsewhere in the codebase.
        assert isinstance(PLACEHOLDER_INDICATORS, tuple)
        assert "placeholder" in PLACEHOLDER_INDICATORS

    @pytest.mark.parametrize(
        "name", ["password", "secret", "token", "key", "db_password"]
    )
    def test_high_severity_variables_contain_core_credential_names(
        self, name: str
    ) -> None:
        assert name in HIGH_SEVERITY_VARIABLES

    @pytest.mark.parametrize(
        "name", ["aws_key", "aws_secret", "azure_key", "gcp_key", "private_key"]
    )
    def test_critical_severity_variables_contain_cloud_keys(self, name: str) -> None:
        assert name in CRITICAL_SEVERITY_VARIABLES

    def test_critical_and_high_severity_sets_are_disjoint(self) -> None:
        # If a variable appears in both, the severity classifier returns
        # "critical" because the critical check runs first. Encoding
        # disjointness makes the precedence rule explicit.
        assert CRITICAL_SEVERITY_VARIABLES.isdisjoint(HIGH_SEVERITY_VARIABLES)


class TestHardcodedPatternShapes:
    """Every hardcoded-value pattern dict must carry the expected keys."""

    REQUIRED_KEYS: ClassVar[set[str]] = {
        "name",
        "pattern",
        "severity",
        "description",
        "remediation",
    }

    def test_each_pattern_has_required_keys(self) -> None:
        for entry in HARDCODED_VALUE_PATTERNS:
            assert self.REQUIRED_KEYS.issubset(entry.keys())

    def test_each_pattern_compiles_as_regex(self) -> None:
        # If a pattern fails to compile, every scan_for_hardcoded_patterns
        # call would raise — guard this here.
        for entry in HARDCODED_VALUE_PATTERNS:
            re.compile(entry["pattern"])

    def test_hardcoded_password_pattern_matches_realistic_example(self) -> None:
        entry = next(
            e for e in HARDCODED_VALUE_PATTERNS if e["name"] == "hardcoded_password"
        )
        assert re.search(entry["pattern"], 'password = "hunter2"') is not None

    def test_connection_string_pattern_matches_mongodb(self) -> None:
        entry = next(
            e for e in HARDCODED_VALUE_PATTERNS if e["name"] == "connection_string"
        )
        assert (
            re.search(entry["pattern"], "mongodb://user:password@localhost:27017/db")
            is not None
        )


class TestRobotFrameworkPatternShapes:
    REQUIRED_KEYS: ClassVar[set[str]] = {
        "name",
        "pattern",
        "severity",
        "description",
        "remediation",
    }

    def test_each_pattern_has_required_keys(self) -> None:
        for entry in ROBOT_FRAMEWORK_PATTERNS:
            assert self.REQUIRED_KEYS.issubset(entry.keys())

    def test_each_pattern_compiles_as_regex(self) -> None:
        for entry in ROBOT_FRAMEWORK_PATTERNS:
            re.compile(entry["pattern"])

    def test_variables_section_pattern_matches_header(self) -> None:
        entry = next(
            e
            for e in ROBOT_FRAMEWORK_PATTERNS
            if e["name"] == "credentials_in_variables_section"
        )
        # The pattern is anchored to line start/end, so test against a
        # plain header line.
        assert re.search(entry["pattern"], "*** Variables ***") is not None


class TestScannerPatternsClass:
    """ScannerPatterns class methods (suspicious vars, severity, etc.)."""

    def test_get_suspicious_variables_includes_base_set(self) -> None:
        result = ScannerPatterns.get_suspicious_variables()
        assert "password" in result
        assert "secret" in result

    def test_get_suspicious_variables_adds_case_and_dash_variations(self) -> None:
        result = ScannerPatterns.get_suspicious_variables()
        # The factory adds upper/lower and dash<->underscore variations.
        assert "PASSWORD" in result
        assert "api-key" in result
        # The starting form survives too.
        assert "api_key" in result

    def test_get_suspicious_variables_merges_additional(self) -> None:
        result = ScannerPatterns.get_suspicious_variables({"my_custom_var"})
        assert "my_custom_var" in result
        # Variations get applied to the additions as well.
        assert "MY_CUSTOM_VAR" in result

    def test_get_hardcoded_patterns_returns_copy(self) -> None:
        # The accessor must not let callers mutate the module-level list.
        result = ScannerPatterns.get_hardcoded_patterns()
        result.append({"name": "tampered"})
        assert all(
            entry.get("name") != "tampered" for entry in HARDCODED_VALUE_PATTERNS
        )

    def test_get_hardcoded_patterns_appends_additional(self) -> None:
        extra: list[dict[str, Any]] = [{"name": "extra_pattern"}]
        result = ScannerPatterns.get_hardcoded_patterns(extra)
        assert any(p.get("name") == "extra_pattern" for p in result)

    def test_get_robot_patterns_returns_copy_and_supports_extension(self) -> None:
        baseline = ScannerPatterns.get_robot_patterns()
        extended = ScannerPatterns.get_robot_patterns([{"name": "extra"}])
        assert len(extended) == len(baseline) + 1

    def test_get_safe_keywords_merges_additional(self) -> None:
        result = ScannerPatterns.get_safe_keywords({"my_keyword"})
        assert "my_keyword" in result
        assert "example" in result

    def test_get_variable_severity_critical_takes_precedence(self) -> None:
        # "private_key" is in CRITICAL set; it must classify as critical
        # even though it contains the substring "key" which is in HIGH.
        assert ScannerPatterns.get_variable_severity("private_key") == "critical"

    def test_get_variable_severity_high_for_credential_names(self) -> None:
        assert ScannerPatterns.get_variable_severity("password") == "high"
        assert ScannerPatterns.get_variable_severity("token") == "high"

    def test_get_variable_severity_medium_for_other_names(self) -> None:
        assert ScannerPatterns.get_variable_severity("foo_unknown") == "medium"

    def test_get_variable_severity_is_case_insensitive(self) -> None:
        # The classifier lowercases the input before lookup.
        assert ScannerPatterns.get_variable_severity("PASSWORD") == "high"


class TestPublicSurface:
    """Encode the documented __all__ — these names are public."""

    def test_all_exports_documented_names(self) -> None:
        assert set(scanner_patterns.__all__) == {
            "CRITICAL_SEVERITY_VARIABLES",
            "HARDCODED_VALUE_PATTERNS",
            "HIGH_SEVERITY_VARIABLES",
            "PLACEHOLDER_INDICATORS",
            "ROBOT_FRAMEWORK_PATTERNS",
            "SAFE_KEYWORDS",
            "SUSPICIOUS_VARIABLE_NAMES",
            "ScannerPatterns",
        }
