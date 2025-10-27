"""Scoring algorithms for format detection."""

from __future__ import annotations

import re
from typing import Any

from importobot.utils.logging import get_logger
from importobot.utils.regex_cache import get_compiled_pattern

from .format_models import EvidenceThreshold, EvidenceWeight

logger = get_logger()


def _compile_pattern_safe(pattern: str) -> re.Pattern[str] | None:
    """Compile and cache regex patterns with error handling.

    Args:
        pattern: Regular expression pattern string

    Returns:
        Compiled pattern or None if pattern is invalid
    """
    try:
        return get_compiled_pattern(pattern, re.IGNORECASE)
    except re.error as e:
        logger.warning(
            "Invalid regex pattern during compilation",
            extra={
                "pattern": pattern,
                "error": str(e),
                "context": "pattern_compilation",
            },
        )
        return None


class ScoringConstants:
    """Configuration constants for scoring algorithms with clear documentation."""

    # Pattern validation penalties
    PATTERN_MISMATCH_PENALTY = 4  # Penalty for fields with wrong patterns

    # Fast-path detection thresholds
    MIN_STRONG_INDICATORS_THRESHOLD = 2  # Require 2+ strong indicators for
    # fast-path detection

    # Confidence calculation thresholds (inherited from existing logic)
    MIN_REQUIRED_MATCH_RATIO = 0.3  # 30% of required keys must match for boost
    MIN_STRONG_INDICATORS_FOR_BOOST = 1  # Minimum strong indicators for extra boost


class ScoringAlgorithms:
    """Contains scoring algorithms for format detection."""

    # Score values for evidence types
    # Strong evidence from required key match
    REQUIRED_KEY_SCORE = EvidenceWeight.STRONG
    OPTIONAL_KEY_SCORE = EvidenceWeight.WEAK  # Weak evidence from optional key match
    STRUCTURE_INDICATOR_SCORE = (
        EvidenceWeight.MODERATE
    )  # Moderate evidence from structure match
    FIELD_PATTERN_SCORE = (
        EvidenceWeight.MODERATE
    )  # Moderate evidence from field matches

    # Detection threshold using evidence evaluation
    MIN_DETECTION_SCORE = (
        EvidenceThreshold.INSUFFICIENT_MAX + 1
    )  # Require > INSUFFICIENT

    # Confidence boost factors for strong matches (percentages as decimals)
    REQUIRED_MATCH_BOOST = (
        1.2  # 120% boost when 30%+ required keys match - moderate boost
    )
    STRONG_INDICATOR_BOOST = (
        1.4  # 40% boost multiplier for 1+ strong indicators - moderate boost
    )

    # Confidence calculation thresholds
    MIN_REQUIRED_MATCH_RATIO = (
        0.3  # 30% of required keys must match for boost - more lenient
    )
    MIN_STRONG_INDICATORS = (
        1  # Minimum strong indicators for extra boost - more lenient
    )

    @staticmethod
    def calculate_format_score(
        data_str: str, patterns: dict[str, Any], data: dict[str, Any] | None = None
    ) -> int:
        """Calculate the total score for a format based on patterns."""
        score = 0
        score += ScoringAlgorithms._score_required_keys(data_str, patterns)
        score += ScoringAlgorithms._score_optional_keys(data_str, patterns)
        score += ScoringAlgorithms._score_structure_indicators(data_str, patterns)
        score += ScoringAlgorithms._score_field_patterns(data_str, patterns, data)
        return score

    @staticmethod
    def _score_required_keys(data_str: str, patterns: dict[str, Any]) -> int:
        """
        Score based on required keys presence using Bayesian likelihood ratios.

        Mathematical foundation:
        - Required keys are necessary conditions for a format
        - P(Evidence|Format) should approach 0 when required keys are missing
        - Use log-likelihood ratios for numerical stability

        For each required key:
        - Present: +evidence_weight (positive likelihood)
        - Missing: -evidence_weight * penalty_multiplier (negative log-likelihood)

        The penalty multiplier reflects how unlikely it is to see the format
        without its required keys (Bayesian evidence against the hypothesis).
        """
        score = 0
        required_keys = patterns.get("required_keys", [])
        total_required = len(required_keys)

        if total_required == 0:
            return 0

        matches = 0
        for key in required_keys:
            if key.lower() in data_str:
                score += ScoringAlgorithms.REQUIRED_KEY_SCORE
                matches += 1
            else:
                # Bayesian penalty: log-likelihood ratio for missing necessary condition
                # Penalty should reflect how discriminative the missing key is
                # More discriminative = higher penalty, but not overwhelming
                penalty_multiplier = 0.5 + (total_required - matches) / (
                    total_required * 2
                )
                score -= int(ScoringAlgorithms.REQUIRED_KEY_SCORE * penalty_multiplier)

        return score

    @staticmethod
    def _score_optional_keys(data_str: str, patterns: dict[str, Any]) -> int:
        """Score based on optional keys presence."""
        score = 0
        optional_keys = patterns.get("optional_keys", [])
        for key in optional_keys:
            if key.lower() in data_str:
                score += ScoringAlgorithms.OPTIONAL_KEY_SCORE
        return score

    @staticmethod
    def _score_structure_indicators(data_str: str, patterns: dict[str, Any]) -> int:
        """Score based on structure indicators presence."""
        score = 0
        structure_indicators = patterns.get("structure_indicators", [])
        for indicator in structure_indicators:
            if indicator.lower() in data_str:
                score += ScoringAlgorithms.STRUCTURE_INDICATOR_SCORE
        return score

    @staticmethod
    def _score_field_patterns(
        data_str: str, patterns: dict[str, Any], data: dict[str, Any] | None = None
    ) -> int:
        """Score based on field pattern matches."""
        score = 0
        field_patterns = patterns.get("field_patterns", {})

        if data is not None:
            # For format detection, only check top-level field names to avoid
            # false positives
            # from nested structures that might contain similar field names
            # Use case-insensitive matching for top-level field names
            top_level_fields_lower = (
                {k.lower(): k for k in data if isinstance(k, str)}
                if isinstance(data, dict)
                else {}
            )
            for field_name, pattern in field_patterns.items():
                # Only score if the field exists as a top-level field (case-insensitive)
                if field_name.lower() in top_level_fields_lower:
                    actual_field_name = top_level_fields_lower[field_name.lower()]
                    field_values = (
                        [data[actual_field_name]] if actual_field_name in data else []
                    )
                    score += ScoringAlgorithms._score_structured_pattern_cached(
                        actual_field_name, pattern, field_values
                    )
        else:
            # Default to string-based matching
            for field_name, pattern in field_patterns.items():
                score += ScoringAlgorithms._score_string_pattern(
                    data_str, field_name, pattern
                )
        return score

    @staticmethod
    def _score_structured_pattern(
        data: dict[str, Any], field_name: str, pattern: str
    ) -> int:
        """Score pattern matching for structured data."""
        field_values = ScoringAlgorithms._extract_field_values(data, field_name)
        return ScoringAlgorithms._score_structured_pattern_cached(
            field_name, pattern, field_values
        )

    @staticmethod
    def _score_structured_pattern_cached(
        field_name: str, pattern: str, field_values: list[Any]
    ) -> int:
        """
        Score pattern matching using Bayesian likelihood principles.

        Mathematical foundation:
        - Pattern match: Strong positive evidence
          P(Pattern|Format) >> P(Pattern|¬Format)
        - Pattern mismatch: Negative evidence, likelihood ratio < 1
        - Missing field: Neutral (no evidence either way)

        Bayesian reasoning:
        - When a field exists but doesn't match the expected pattern,
          this is evidence AGAINST the format hypothesis
        - The penalty should reflect the likelihood ratio
          P(Mismatch|¬Format) / P(Mismatch|Format)
        - For well-defined formats, pattern mismatches are strong negative evidence
        """
        pattern_matched = ScoringAlgorithms._check_pattern_match(
            field_name, pattern, field_values
        )

        if pattern_matched:
            # Strong positive evidence: field exists and matches expected pattern
            return ScoringAlgorithms.FIELD_PATTERN_SCORE
        if field_values:
            # Negative evidence: field exists but doesn't match pattern
            # Bayesian penalty based on how discriminative the pattern should be
            return -ScoringConstants.PATTERN_MISMATCH_PENALTY
        # No evidence: field doesn't exist (neutral for optional patterns)
        return 0

    @staticmethod
    def _score_string_pattern(data_str: str, field_name: str, pattern: str) -> int:
        """Score pattern matching for string data."""
        if field_name.lower() in data_str:
            compiled_pattern = _compile_pattern_safe(pattern)
            if compiled_pattern and compiled_pattern.search(data_str):
                return ScoringAlgorithms.FIELD_PATTERN_SCORE
        return 0

    @staticmethod
    def _check_pattern_match(
        field_name: str, pattern: str, field_values: list[Any]
    ) -> bool:
        """Check if pattern matches field name or any field values."""
        compiled_pattern = _compile_pattern_safe(pattern)
        if compiled_pattern is None:
            return False

        # First, check if the field name itself matches the pattern
        if compiled_pattern.search(field_name):
            return True

        # If field name doesn't match, check field values
        return any(compiled_pattern.search(str(value)) for value in field_values)

    @staticmethod
    def _extract_field_values(data: dict[str, Any], field_name: str) -> list[Any]:
        """Extract all values for a given field name from nested data structure."""
        values = []

        def _extract_recursive(obj: Any, target_field: str) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == target_field:
                        values.append(value)
                    elif isinstance(value, dict | list):
                        _extract_recursive(value, target_field)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict | list):
                        _extract_recursive(item, target_field)

        _extract_recursive(data, field_name)
        return values


__all__ = ["ScoringAlgorithms"]
