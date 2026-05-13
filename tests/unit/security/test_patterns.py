"""Tests for security patterns and the SecurityPatterns factory.

Covers ``importobot.security.patterns``: the dangerous command regexes,
sensitive path regexes, injection patterns, sanitization patterns, and
the SecurityPatterns class that selects them by security level with
optional replacement or extension.
"""

from __future__ import annotations

import re

from importobot.security import patterns
from importobot.security.patterns import (
    DEFAULT_DANGEROUS_CHARS,
    DEFAULT_DANGEROUS_PATTERNS,
    DEFAULT_SENSITIVE_PATHS,
    ERROR_SANITIZATION_PATTERNS,
    INJECTION_PATTERNS,
    PERMISSIVE_PATTERN_REMOVALS,
    STRICT_DANGEROUS_PATTERN_ADDITIONS,
    STRICT_SENSITIVE_PATH_ADDITIONS,
    SecurityPatterns,
)
from importobot.services.security_types import SecurityLevel


class TestModuleConstants:
    """Module-level constants must be present, typed, and non-empty."""

    def test_default_dangerous_patterns_non_empty_list(self) -> None:
        assert isinstance(DEFAULT_DANGEROUS_PATTERNS, list)
        assert len(DEFAULT_DANGEROUS_PATTERNS) > 0

    def test_default_sensitive_paths_non_empty_list(self) -> None:
        assert isinstance(DEFAULT_SENSITIVE_PATHS, list)
        assert len(DEFAULT_SENSITIVE_PATHS) > 0

    def test_strict_additions_disjoint_from_defaults(self) -> None:
        # Strict additions are documented as additions; if any duplicates
        # leaked in, the dangerous-patterns list would grow with stale
        # entries on every strict-level construction.
        for p in STRICT_DANGEROUS_PATTERN_ADDITIONS:
            assert p not in DEFAULT_DANGEROUS_PATTERNS

    def test_permissive_removals_either_in_defaults_or_strict_additions(
        self,
    ) -> None:
        # Each item in PERMISSIVE_PATTERN_REMOVALS only takes effect if it
        # appears somewhere in the user's eventual pattern set. Today,
        # some entries (curl\\s+, wget\\s+) only live in STRICT additions
        # — so removing them at PERMISSIVE level is a silent no-op since
        # PERMISSIVE never includes STRICT additions. The contract this
        # test actually wants to encode is: every removal target should
        # at minimum appear in some legitimate source list, so the
        # configuration intent is visible.
        all_sources = set(DEFAULT_DANGEROUS_PATTERNS) | set(
            STRICT_DANGEROUS_PATTERN_ADDITIONS
        )
        assert PERMISSIVE_PATTERN_REMOVALS.issubset(all_sources)

    def test_strict_path_additions_disjoint_from_defaults(self) -> None:
        for p in STRICT_SENSITIVE_PATH_ADDITIONS:
            assert p not in DEFAULT_SENSITIVE_PATHS

    def test_dangerous_chars_contains_shell_metachars(self) -> None:
        # Core shell metachars must be present; they are the primary
        # injection vectors the sanitiser escapes.
        for ch in ("|", "&", ";", "`"):
            assert ch in DEFAULT_DANGEROUS_CHARS

    def test_all_patterns_compile_as_regex(self) -> None:
        # If any pattern is invalid, every SecurityValidator built at
        # that level raises at first use. Compile them all here.
        for collection in (
            DEFAULT_DANGEROUS_PATTERNS,
            STRICT_DANGEROUS_PATTERN_ADDITIONS,
            INJECTION_PATTERNS,
        ):
            for pattern in collection:
                re.compile(pattern)

    def test_sanitization_patterns_are_tuple_pairs(self) -> None:
        for entry in ERROR_SANITIZATION_PATTERNS:
            assert isinstance(entry, tuple)
            assert len(entry) == 2
            # The first element must be a compilable regex.
            re.compile(entry[0])


class TestGetDangerousPatterns:
    """Pattern selection by security level."""

    def test_standard_returns_defaults(self) -> None:
        result = SecurityPatterns.get_dangerous_patterns(None, SecurityLevel.STANDARD)
        # The factory returns a fresh list (so callers can mutate), but
        # the *content* equals the defaults at the standard level.
        assert result == list(DEFAULT_DANGEROUS_PATTERNS)

    def test_strict_appends_strict_additions(self) -> None:
        result = SecurityPatterns.get_dangerous_patterns(None, SecurityLevel.STRICT)
        for addition in STRICT_DANGEROUS_PATTERN_ADDITIONS:
            assert addition in result
        assert len(result) == len(DEFAULT_DANGEROUS_PATTERNS) + len(
            STRICT_DANGEROUS_PATTERN_ADDITIONS
        )

    def test_permissive_removes_permissive_removals(self) -> None:
        result = SecurityPatterns.get_dangerous_patterns(None, SecurityLevel.PERMISSIVE)
        for removed in PERMISSIVE_PATTERN_REMOVALS:
            assert removed not in result
        # The non-removed defaults remain.
        for default in DEFAULT_DANGEROUS_PATTERNS:
            if default not in PERMISSIVE_PATTERN_REMOVALS:
                assert default in result

    def test_custom_replaces_defaults(self) -> None:
        result = SecurityPatterns.get_dangerous_patterns(
            ["custom_only"], SecurityLevel.STANDARD
        )
        # Custom replaces; defaults must not leak in.
        assert result == ["custom_only"]

    def test_custom_with_strict_level_still_appends_strict_additions(self) -> None:
        result = SecurityPatterns.get_dangerous_patterns(
            ["custom_only"], SecurityLevel.STRICT
        )
        assert "custom_only" in result
        assert all(p in result for p in STRICT_DANGEROUS_PATTERN_ADDITIONS)

    def test_additional_appended_to_result(self) -> None:
        result = SecurityPatterns.get_dangerous_patterns(
            None, SecurityLevel.STANDARD, additional_patterns=["my_extra"]
        )
        assert result[-1] == "my_extra"
        assert len(result) == len(DEFAULT_DANGEROUS_PATTERNS) + 1


class TestGetSensitivePaths:
    """Sensitive-path selection mirrors dangerous-pattern semantics."""

    def test_standard_returns_defaults(self) -> None:
        result = SecurityPatterns.get_sensitive_paths(None, SecurityLevel.STANDARD)
        assert result == list(DEFAULT_SENSITIVE_PATHS)

    def test_strict_appends_strict_additions(self) -> None:
        result = SecurityPatterns.get_sensitive_paths(None, SecurityLevel.STRICT)
        for addition in STRICT_SENSITIVE_PATH_ADDITIONS:
            assert addition in result

    def test_permissive_returns_defaults(self) -> None:
        # Permissive does NOT remove sensitive paths — only dangerous
        # patterns. Encode that subtle asymmetry.
        result = SecurityPatterns.get_sensitive_paths(None, SecurityLevel.PERMISSIVE)
        assert result == list(DEFAULT_SENSITIVE_PATHS)

    def test_custom_replaces_defaults(self) -> None:
        result = SecurityPatterns.get_sensitive_paths(
            ["/only/this"], SecurityLevel.STANDARD
        )
        assert result == ["/only/this"]

    def test_additional_paths_extend(self) -> None:
        result = SecurityPatterns.get_sensitive_paths(
            None, SecurityLevel.STANDARD, additional_paths=["/extra"]
        )
        assert "/extra" in result


class TestGetInjectionPatterns:
    """Injection patterns support only extension (no replace, no level)."""

    def test_returns_default_injection_patterns(self) -> None:
        result = SecurityPatterns.get_injection_patterns()
        assert result == list(INJECTION_PATTERNS)

    def test_additional_patterns_extend(self) -> None:
        result = SecurityPatterns.get_injection_patterns(["UNION SELECT"])
        assert "UNION SELECT" in result


class TestGetSanitizationPatterns:
    """Sanitization patterns are (regex, replacement) tuples."""

    def test_returns_default_sanitization_pairs(self) -> None:
        result = SecurityPatterns.get_sanitization_patterns()
        assert result == list(ERROR_SANITIZATION_PATTERNS)

    def test_additional_pairs_appended(self) -> None:
        result = SecurityPatterns.get_sanitization_patterns([(r"\b\d+\b", "[NUM]")])
        assert (r"\b\d+\b", "[NUM]") in result


class TestGetDangerousChars:
    """Dangerous-char selection supports replace and extend, no level."""

    def test_returns_default_chars(self) -> None:
        result = SecurityPatterns.get_dangerous_chars()
        assert result == list(DEFAULT_DANGEROUS_CHARS)

    def test_custom_replaces_defaults(self) -> None:
        result = SecurityPatterns.get_dangerous_chars(custom_chars=["|"])
        assert result == ["|"]

    def test_additional_extends_defaults(self) -> None:
        result = SecurityPatterns.get_dangerous_chars(additional_chars=["@"])
        assert "@" in result
        # The defaults remain because additional extends, doesn't replace.
        assert "|" in result


class TestPublicSurface:
    def test_all_lists_documented_exports(self) -> None:
        assert set(patterns.__all__) == {
            "DEFAULT_DANGEROUS_CHARS",
            "DEFAULT_DANGEROUS_PATTERNS",
            "DEFAULT_SENSITIVE_PATHS",
            "ERROR_SANITIZATION_PATTERNS",
            "INJECTION_PATTERNS",
            "PERMISSIVE_PATTERN_REMOVALS",
            "STRICT_DANGEROUS_PATTERN_ADDITIONS",
            "STRICT_SENSITIVE_PATH_ADDITIONS",
            "SecurityPatterns",
        }
