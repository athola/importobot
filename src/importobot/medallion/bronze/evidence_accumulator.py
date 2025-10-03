"""Evidence accumulation system for format detection confidence scoring.

Based on medallion architecture best practices and Bayesian evidence accumulation
research, this module provides a mathematically sound confidence scoring system
that avoids arbitrary scaling factors.

Key principles:
1. Evidence accumulation follows Bayesian principles
2. Confidence reflects quality of evidence, not just quantity
3. Handles edge cases, ties, and uncertainty quantification
4. Provides transparent reasoning for confidence scores
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .format_models import EvidenceWeight
from .mvlp_bayesian_confidence import (
    EvidenceMetrics,
    MVLPBayesianConfidenceScorer,
)
from .shared_config import DEFAULT_FORMAT_PRIORS


@dataclass
class EvidenceItem:
    """Single piece of evidence for format detection."""

    source: str  # What generated this evidence (e.g., "required_key", "pattern_match")
    weight: EvidenceWeight  # Strength of this evidence
    confidence: float  # How certain we are about this evidence (0.0-1.0)
    details: str = ""  # Human-readable explanation

    @property
    def effective_weight(self) -> float:
        """Calculate effective weight considering confidence."""
        return self.weight.value * self.confidence


@dataclass
class FormatEvidenceProfile:
    """Complete evidence profile for a format detection attempt."""

    format_name: str
    evidence_items: List[EvidenceItem]
    total_possible_weight: float

    @property
    def total_evidence_weight(self) -> float:
        """Sum of all effective evidence weights."""
        return sum(item.effective_weight for item in self.evidence_items)

    @property
    def evidence_quality(self) -> float:
        """Average confidence across all evidence items."""
        if not self.evidence_items:
            return 0.0
        return sum(item.confidence for item in self.evidence_items) / len(
            self.evidence_items
        )

    @property
    def unique_evidence_count(self) -> int:
        """Count of unique-level evidence items."""
        return sum(
            1 for item in self.evidence_items if item.weight == EvidenceWeight.UNIQUE
        )

    @property
    def strong_evidence_count(self) -> int:
        """Count of strong-level evidence items."""
        return sum(
            1 for item in self.evidence_items if item.weight == EvidenceWeight.STRONG
        )


class EvidenceAccumulator:
    """Bayesian evidence accumulator for format detection confidence scoring.

    This class implements a principled approach to confidence scoring that:
    1. Accumulates evidence using Bayesian principles
    2. Handles uncertainty and evidence quality
    3. Provides tie-breaking mechanisms
    4. Handles edge cases and data skew
    """

    # Use shared format priors configuration
    FORMAT_PRIORS = DEFAULT_FORMAT_PRIORS

    # Confidence thresholds based on evidence accumulation research
    HIGH_CONFIDENCE_THRESHOLD = 0.8
    MEDIUM_CONFIDENCE_THRESHOLD = 0.6
    LOW_CONFIDENCE_THRESHOLD = 0.4

    def __init__(self) -> None:
        """Initialize the evidence accumulator with empty evidence profiles."""
        self.evidence_profiles: Dict[str, FormatEvidenceProfile] = {}
        # Initialize MVLP Bayesian scorer
        self.mvlp_scorer = MVLPBayesianConfidenceScorer(self.FORMAT_PRIORS)

    def add_evidence(self, format_name: str, evidence: EvidenceItem) -> None:
        """Add a piece of evidence for a format."""
        if format_name not in self.evidence_profiles:
            self.evidence_profiles[format_name] = FormatEvidenceProfile(
                format_name=format_name, evidence_items=[], total_possible_weight=0.0
            )

        self.evidence_profiles[format_name].evidence_items.append(evidence)

    def set_total_possible_weight(self, format_name: str, weight: float) -> None:
        """Set the total possible weight for a format."""
        if format_name not in self.evidence_profiles:
            self.evidence_profiles[format_name] = FormatEvidenceProfile(
                format_name=format_name, evidence_items=[], total_possible_weight=weight
            )
        else:
            self.evidence_profiles[format_name].total_possible_weight = weight

    def calculate_bayesian_confidence(self, format_name: str) -> float:
        """Calculate Bayesian confidence score using MVLP approach."""
        if format_name not in self.evidence_profiles:
            return 0.0

        profile = self.evidence_profiles[format_name]

        # Convert evidence profile to standardized metrics
        metrics = self._profile_to_metrics(profile)

        # Calculate confidence using MVLP Bayesian scorer
        result = self.mvlp_scorer.calculate_confidence(metrics, format_name)

        return result["confidence"]

    def _profile_to_metrics(self, profile: FormatEvidenceProfile) -> EvidenceMetrics:
        """Convert FormatEvidenceProfile to standardized EvidenceMetrics."""
        # Calculate completeness ratio
        if profile.total_possible_weight > 0:
            completeness = min(
                1.0, profile.total_evidence_weight / profile.total_possible_weight
            )
        else:
            completeness = 0.0

        # Calculate evidence quality (average confidence)
        quality = profile.evidence_quality

        # Calculate normalized uniqueness strength
        unique_count = profile.unique_evidence_count
        total_count = len(profile.evidence_items)

        if total_count > 0:
            # Normalize uniqueness: ratio of unique evidence weighted by strength
            unique_weight_sum = sum(
                item.weight.value
                for item in profile.evidence_items
                if item.weight == EvidenceWeight.UNIQUE
            )
            total_weight_sum = sum(item.weight.value for item in profile.evidence_items)

            if total_weight_sum > 0:
                uniqueness = unique_weight_sum / total_weight_sum
            else:
                uniqueness = 0.0
        else:
            uniqueness = 0.0

        return EvidenceMetrics(
            completeness=completeness,
            quality=quality,
            uniqueness=uniqueness,
            evidence_count=total_count,
            unique_count=unique_count,
        )

    def optimize_parameters(self, training_data: List[Tuple[str, float]]) -> None:
        """Optimize MVLP parameters using training data.

        Args:
            training_data: List of (format_name, expected_confidence) pairs
        """
        # Convert training data to EvidenceMetrics format
        mvlp_training_data = []

        for format_name, expected_confidence in training_data:
            if format_name in self.evidence_profiles:
                profile = self.evidence_profiles[format_name]
                metrics = self._profile_to_metrics(profile)
                mvlp_training_data.append((metrics, expected_confidence))

        if mvlp_training_data:
            # Optimize parameters using MVLP approach
            self.mvlp_scorer.optimize_parameters(mvlp_training_data)

    def get_parameter_summary(self) -> Dict[str, Any]:
        """Get summary of optimized MVLP parameters."""
        return self.mvlp_scorer.get_parameter_summary()

    def get_detection_confidence(self, format_name: str) -> Dict[str, Any]:
        """Get comprehensive confidence metrics using MVLP approach."""
        if format_name not in self.evidence_profiles:
            return {
                "confidence": 0.0,
                "evidence_quality": 0.0,
                "evidence_completeness": 0.0,
                "evidence_count": 0,
                "confidence_level": "NONE",
            }

        profile = self.evidence_profiles[format_name]
        metrics = self._profile_to_metrics(profile)

        # Get detailed confidence analysis from MVLP scorer
        mvlp_result = self.mvlp_scorer.calculate_confidence(
            metrics, format_name, use_uncertainty=True
        )

        confidence = mvlp_result["confidence"]

        # Determine confidence level
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            confidence_level = "HIGH"
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            confidence_level = "MEDIUM"
        elif confidence >= self.LOW_CONFIDENCE_THRESHOLD:
            confidence_level = "LOW"
        else:
            confidence_level = "INSUFFICIENT"

        # Combine MVLP results with profile information
        result = {
            "confidence": confidence,
            "evidence_quality": profile.evidence_quality,
            "evidence_completeness": metrics.completeness,
            "evidence_count": len(profile.evidence_items),
            "confidence_level": confidence_level,
            "unique_evidence_count": profile.unique_evidence_count,
            "strong_evidence_count": profile.strong_evidence_count,
            "likelihood": mvlp_result.get("likelihood", 0.0),
            "prior": mvlp_result.get("prior", 0.0),
        }

        # Add uncertainty bounds if available
        if "confidence_lower_95" in mvlp_result:
            result.update(
                {
                    "confidence_lower_95": mvlp_result["confidence_lower_95"],
                    "confidence_upper_95": mvlp_result["confidence_upper_95"],
                    "confidence_std": mvlp_result["confidence_std"],
                }
            )

        return result

    def handle_ties(
        self, format_scores: Dict[str, float]
    ) -> Tuple[str, float, Dict[str, str]]:
        """Handle tie-breaking between formats with similar scores.

        Returns:
            Tuple of (best_format, confidence, tie_breaking_reasons)
        """
        if not format_scores:
            return "unknown", 0.0, {"reason": "No formats detected"}

        # Sort formats by confidence score
        sorted_formats = sorted(format_scores.items(), key=lambda x: x[1], reverse=True)

        if len(sorted_formats) == 1:
            best_format, confidence = sorted_formats[0]
            return best_format, confidence, {"reason": "Single format detected"}

        best_format, best_confidence = sorted_formats[0]
        second_format, second_confidence = sorted_formats[1]

        # Check for close tie (within 5% confidence)
        confidence_diff = best_confidence - second_confidence
        if confidence_diff < 0.05:
            # Apply tie-breaking rules
            tie_breaker_result = self._apply_tie_breaking_rules(
                best_format, second_format, best_confidence
            )

            return (
                tie_breaker_result["winner"],
                tie_breaker_result["confidence"],
                tie_breaker_result["reasons"],
            )

        return best_format, best_confidence, {"reason": "Clear confidence winner"}

    def _apply_tie_breaking_rules(
        self, format1: str, format2: str, confidence: float
    ) -> Dict:
        """Apply tie-breaking rules when formats have similar confidence."""
        reasons = []

        # Rule 1: Prefer format with more unique evidence
        profile1 = self.evidence_profiles.get(format1)
        profile2 = self.evidence_profiles.get(format2)

        if profile1 and profile2:
            unique1 = profile1.unique_evidence_count
            unique2 = profile2.unique_evidence_count

            if unique1 > unique2:
                reasons.append(
                    f"{format1} has more unique evidence ({unique1} vs {unique2})"
                )
                return {"winner": format1, "confidence": confidence, "reasons": reasons}
            if unique2 > unique1:
                reasons.append(
                    f"{format2} has more unique evidence ({unique2} vs {unique1})"
                )
                return {"winner": format2, "confidence": confidence, "reasons": reasons}

            # Rule 2: Prefer format with higher evidence quality
            quality1 = profile1.evidence_quality
            quality2 = profile2.evidence_quality

            if abs(quality1 - quality2) > 0.1:
                if quality1 > quality2:
                    msg = (
                        f"{format1} has higher evidence quality "
                        f"({quality1:.2f} vs {quality2:.2f})"
                    )
                    reasons.append(msg)
                    return {
                        "winner": format1,
                        "confidence": confidence,
                        "reasons": reasons,
                    }
                msg = (
                    f"{format2} has higher evidence quality "
                    f"({quality2:.2f} vs {quality1:.2f})"
                )
                reasons.append(msg)
                return {
                    "winner": format2,
                    "confidence": confidence,
                    "reasons": reasons,
                }

        # Rule 3: Prefer format with higher prior probability
        prior1 = self.FORMAT_PRIORS.get(format1, 0.1)
        prior2 = self.FORMAT_PRIORS.get(format2, 0.1)

        if prior1 > prior2:
            reasons.append(
                f"{format1} has higher prior probability ({prior1} vs {prior2})"
            )
            return {
                "winner": format1,
                "confidence": confidence * 0.95,
                "reasons": reasons,
            }
        if prior2 > prior1:
            reasons.append(
                f"{format2} has higher prior probability ({prior2} vs {prior1})"
            )
            return {
                "winner": format2,
                "confidence": confidence * 0.95,
                "reasons": reasons,
            }

        # Default: Return first format with reduced confidence
        reasons.append("True tie - defaulting to first format with reduced confidence")
        return {"winner": format1, "confidence": confidence * 0.8, "reasons": reasons}
