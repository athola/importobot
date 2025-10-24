"""Data models for format detection.

This module contains the core data models used by format detection,
separated to avoid cyclic imports between format_detector and format definitions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum

from importobot.medallion.interfaces.enums import SupportedFormat


class EvidenceWeight(IntEnum):
    """Individual evidence weights for format detection elements."""

    NONE = 0  # No evidence found
    WEAK = 1  # Weak evidence: optional keys, generic indicators
    MODERATE = 2  # Moderate evidence: common structure patterns, shared fields
    STRONG = 3  # Strong evidence: system-specific required keys
    UNIQUE = 5  # Unique evidence: highly system-specific identifiers
    # (e.g., "testCase", "testExecutions")

    @classmethod
    def evaluate_total_evidence(cls, total_score: int) -> str:
        """Map total accumulated score to evidence level using threshold boundaries.

        Args:
            total_score: Sum of individual evidence weights

        Returns:
            Evidence level: "INSUFFICIENT", "MODERATE", or "STRONG"
        """
        if total_score <= EvidenceThreshold.INSUFFICIENT_MAX:
            return "INSUFFICIENT"
        if total_score <= EvidenceThreshold.MODERATE_MAX:
            return "MODERATE"
        return "STRONG"

    @classmethod
    def is_sufficient_for_detection(cls, total_score: int) -> bool:
        """Check if accumulated score is sufficient for format detection."""
        return total_score > EvidenceThreshold.INSUFFICIENT_MAX


class EvidenceThreshold(IntEnum):
    """Score thresholds that define evidence level boundaries.

    Optimized for real-world test data scenarios where minimal
    indicators should still provide reasonable confidence scores.
    """

    INSUFFICIENT_MAX = 2  # Scores 0-2: UNKNOWN format (lowered from 3)
    MODERATE_MAX = 5  # Scores 3-5: Possible format match (lowered from 6)
    STRONG_MIN = 6  # Scores 6+: Confident format match (lowered from 7)
    UNIQUE_THRESHOLD = (
        4  # Single unique indicator provides strong evidence (lowered from 5)
    )


@dataclass
class FieldDefinition:
    """Definition of a field for format detection with evidence classification."""

    name: str
    evidence_weight: EvidenceWeight
    pattern: str | None = None  # Regex pattern for validation
    description: str = ""
    is_required: bool = False


@dataclass
class FormatDefinition:
    """Pluggable definition for a test management format.

    Allows dynamic addition of new test formats without code changes.
    Based on research into Medallion Architecture Bronze layer requirements
    for handling diverse data sources with unique characteristics.
    """

    name: str
    format_type: SupportedFormat
    description: str

    # Field classifications based on evidence strength
    unique_indicators: list[FieldDefinition] = field(
        default_factory=list
    )  # UNIQUE (5 points)
    strong_indicators: list[FieldDefinition] = field(
        default_factory=list
    )  # STRONG (3 points)
    moderate_indicators: list[FieldDefinition] = field(
        default_factory=list
    )  # MODERATE (2 points)
    weak_indicators: list[FieldDefinition] = field(
        default_factory=list
    )  # WEAK (1 point)

    # Confidence calculation parameters
    confidence_boost_threshold: float = 0.33  # Required field match ratio for boost
    confidence_boost_factor: float = 0.8  # Boost multiplier
    min_score_threshold: int = 4  # Minimum score for detection

    # Metadata
    version: str = "1.0"
    author: str = ""
    created_date: str | None = None

    def get_all_fields(self) -> list[FieldDefinition]:
        """Get all field definitions across all evidence levels."""
        return (
            self.unique_indicators
            + self.strong_indicators
            + self.moderate_indicators
            + self.weak_indicators
        )

    def get_max_possible_score(self) -> int:
        """Calculate maximum possible score for this format."""
        return sum(
            field_def.evidence_weight.value for field_def in self.get_all_fields()
        )

    def validate(self) -> list[str]:
        """Validate format definition and return list of issues."""
        issues = []

        if not self.name.strip():
            issues.append("Format name cannot be empty")

        if not self.unique_indicators and not self.strong_indicators:
            issues.append("Format must have at least one unique or strong indicator")

        # Check for duplicate field names
        all_fields = self.get_all_fields()
        field_names = [f.name for f in all_fields]
        if len(field_names) != len(set(field_names)):
            issues.append("Duplicate field names found")

        # Validate regex patterns
        for field_def in all_fields:
            if field_def.pattern:
                try:
                    re.compile(field_def.pattern)
                except re.error as e:
                    issues.append(
                        f"Invalid regex pattern for field '{field_def.name}': {e}"
                    )

        return issues
