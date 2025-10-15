"""Core evidence metrics for Bayesian confidence scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvidenceMetrics:
    """Standardized evidence metrics shared across Bayesian scorers."""

    completeness: float  # [0, 1] - Evidence coverage
    quality: float  # [0, 1] - Average evidence confidence
    uniqueness: float  # [0, 1] - Normalized unique evidence strength
    evidence_count: int  # [0, ∞) - Total evidence items
    unique_count: int  # [0, ∞) - Unique evidence items
    complexity_score: float = 0.0  # [0, 1] - Complexity-adjusted weighting
    penalty_factor: float = 1.0  # (0, 1] - Likelihood penalty for negative evidence

    def __post_init__(self) -> None:
        """Validate metrics are within expected ranges."""
        assert 0.0 <= self.completeness <= 1.0, (
            f"Invalid completeness: {self.completeness}"
        )
        assert 0.0 <= self.quality <= 1.0, f"Invalid quality: {self.quality}"
        assert 0.0 <= self.uniqueness <= 1.0, f"Invalid uniqueness: {self.uniqueness}"
        assert self.evidence_count >= 0, (
            f"Invalid evidence_count: {self.evidence_count}"
        )
        assert self.unique_count >= 0, f"Invalid unique_count: {self.unique_count}"
        assert 0.0 <= self.complexity_score <= 1.0, (
            f"Invalid complexity_score: {self.complexity_score}"
        )
        assert 0.0 < self.penalty_factor <= 1.0, (
            f"Invalid penalty_factor: {self.penalty_factor}"
        )


__all__ = ["EvidenceMetrics"]
