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
from typing import Any

from importobot.medallion.interfaces.enums import EvidenceSource, SupportedFormat
from importobot.utils.logging import get_logger

from .evidence_metrics import EvidenceMetrics
from .format_models import EvidenceWeight
from .independent_bayesian_scorer import IndependentBayesianScorer
from .shared_config import DEFAULT_FORMAT_PRIORS
from .test_case_complexity_analyzer import ComplexityMetrics, TestCaseComplexityAnalyzer

logger = get_logger()

# Penalty constants are defined here so the ratios we enforce stay transparent.
# - PATTERN_MISMATCH_PENALTY pushes down confidence when regex checks fail.
# - SPARSE_EVIDENCE_PENALTY dampens formats that only hit generic indicators.
# - REQUIRED_FIELD_PENALTY handles cases where unique/strong keys are missing.
PATTERN_MISMATCH_PENALTY = 0.01
SPARSE_EVIDENCE_PENALTY = 0.1
REQUIRED_FIELD_PENALTY = 0.05
SPARSE_EVIDENCE_FORMATS = {
    SupportedFormat.TESTRAIL.name,
    SupportedFormat.TESTLINK.name,
}
REQUIRED_FIELD_FORMATS = {
    SupportedFormat.TESTRAIL.name,
    SupportedFormat.TESTLINK.name,
    SupportedFormat.ZEPHYR.name,
}


@dataclass
class EvidenceItem:
    """Single piece of evidence for format detection."""

    source: EvidenceSource  # Evidence source type (e.g., REQUIRED_KEY, FIELD_PATTERN)
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
    evidence_items: list[EvidenceItem]
    total_possible_weight: float
    complexity_metrics: ComplexityMetrics | None = None  # Complexity analysis results
    original_data: dict[str, Any] | None = (
        None  # Original test data for complexity analysis
    )

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
            1
            for item in self.evidence_items
            if item.weight == EvidenceWeight.UNIQUE and item.confidence > 0.0
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
        self.evidence_profiles: dict[str, FormatEvidenceProfile] = {}
        # Initialize Independent Bayesian scorer (mathematically rigorous approach)
        self.bayesian_scorer = IndependentBayesianScorer(
            format_priors=self.FORMAT_PRIORS
        )
        # Initialize complexity analyzer for enhanced evidence weighting
        self.complexity_analyzer = TestCaseComplexityAnalyzer()
        # Store original data for complexity analysis
        self.original_test_data: dict[str, Any] = {}

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
            original_data: dict[str, Any] | None = None
            if self.original_test_data:
                original_data = self.original_test_data.copy()

            self.evidence_profiles[format_name] = FormatEvidenceProfile(
                format_name=format_name,
                evidence_items=[],
                total_possible_weight=weight,
                original_data=original_data,
            )
            # Analyze complexity for this format
            if self.original_test_data:
                try:
                    self.evidence_profiles[
                        format_name
                    ].complexity_metrics = self.complexity_analyzer.analyze_complexity(
                        self.original_test_data
                    )
                except Exception as e:
                    # Use basic metrics if complexity analysis fails
                    logger.warning(
                        "Complexity analysis failed for %s: %s", format_name, e
                    )
        else:
            self.evidence_profiles[format_name].total_possible_weight = weight

    def set_test_data(self, test_data: dict[str, Any]) -> None:
        """Store original test data for complexity analysis."""
        self.original_test_data = test_data.copy()

    def analyze_complexity_for_all_formats(self) -> dict[str, ComplexityMetrics]:
        """Analyze complexity for all formats using stored test data."""
        complexity_results: dict[str, ComplexityMetrics] = {}

        if not self.original_test_data:
            return complexity_results

        for format_name, profile in self.evidence_profiles.items():
            if profile.complexity_metrics is None:
                try:
                    profile.complexity_metrics = (
                        self.complexity_analyzer.analyze_complexity(
                            self.original_test_data
                        )
                    )
                    complexity_results[format_name] = profile.complexity_metrics
                except Exception as e:
                    logger.warning(
                        "Complexity analysis failed for %s: %s", format_name, e
                    )
            else:
                complexity_results[format_name] = profile.complexity_metrics

        return complexity_results

    def calculate_bayesian_confidence(self, format_name: str) -> float:
        """Calculate Bayesian likelihood using independent Bayesian approach.

        Note: This method calculates likelihood for a single format in isolation.
        For proper multi-class normalization, use calculate_multi_class_confidence().

        Returns:
            Unnormalized likelihood P(E|H) in (0, 1] range
        """
        if format_name not in self.evidence_profiles:
            return 0.0

        profile = self.evidence_profiles[format_name]

        # Convert evidence profile to standardized metrics
        metrics = self._profile_to_metrics(profile)

        # Calculate likelihood using Independent Bayesian scorer
        likelihood = self.bayesian_scorer.calculate_likelihood(metrics)

        return likelihood

    def calculate_all_format_likelihoods(self) -> dict[str, float]:
        """Calculate likelihoods for all formats with research-backed ratio capping.

        This method implements the hybrid approach from research:
        1. Calculate raw likelihoods for all formats using evidence metrics
        2. Apply likelihood ratio capping (max 3:1) to prevent extreme discrimination
        3. Maintain discriminative power while ensuring numerical stability

        Returns:
            Dictionary mapping format names to calibrated likelihoods
        """
        if not self.evidence_profiles:
            return {}

        # Collect metrics for all formats
        all_metrics = {}
        for format_name, profile in self.evidence_profiles.items():
            all_metrics[format_name] = self._profile_to_metrics(profile)

        # Use the Bayesian scorer's research-backed approach
        calibrated_likelihoods = self.bayesian_scorer.calculate_all_format_likelihoods(
            all_metrics
        )

        return calibrated_likelihoods

    def calculate_multi_class_confidence(
        self, format_likelihoods: dict[str, float]
    ) -> dict[str, int | float]:
        """Calculate properly normalized multi-class Bayesian confidence scores.

        This implements the mathematically correct multi-class Bayesian formula:
            P(H_i|E) = P(E|H_i) * P(H_i) / Σ_j[P(E|H_j) * P(H_j)]

        where the denominator sums over ALL format hypotheses, not just
        the binary "format vs not-format" case.

        Args:
            format_likelihoods: Dictionary mapping format names to their
                evidence-derived likelihoods P(E|H_i)

        Returns:
            Dictionary mapping format names to normalized posterior probabilities
        """
        posteriors = {}

        # Calculate denominator: sum of P(E|H_j) * P(H_j) for all formats
        denominator = 0.0
        for fmt, likelihood in format_likelihoods.items():
            prior = self.FORMAT_PRIORS.get(fmt, 0.1)
            denominator += likelihood * prior

        # Avoid division by zero
        if denominator < 1e-15:
            # No format can explain the evidence - return uniform low confidence
            # Note: dict comprehension for type checker compatibility
            return {fmt: 0.0 for fmt in format_likelihoods}  # noqa: C420

        # Calculate normalized posteriors
        for fmt, likelihood in format_likelihoods.items():
            prior = self.FORMAT_PRIORS.get(fmt, 0.1)
            posteriors[fmt] = (likelihood * prior) / denominator

        return posteriors

    def _profile_to_metrics(self, profile: FormatEvidenceProfile) -> EvidenceMetrics:
        """Convert FormatEvidenceProfile to standardized EvidenceMetrics.

        Applies complexity enhancement to improve format detection accuracy.

        Returns standardized evidence metrics for format detection.
        """
        # Calculate completeness ratio
        if profile.total_possible_weight > 0:
            completeness = min(
                1.0, profile.total_evidence_weight / profile.total_possible_weight
            )
        else:
            completeness = 0.0

        # Calculate evidence quality (average confidence)
        quality = profile.evidence_quality

        # Calculate normalized uniqueness strength with complexity enhancement
        unique_count = profile.unique_evidence_count
        total_count = len(profile.evidence_items)

        # Base uniqueness calculation
        base_uniqueness = 0.0
        if total_count > 0:
            unique_weight_sum = sum(
                item.weight.value * item.confidence
                for item in profile.evidence_items
                if item.weight == EvidenceWeight.UNIQUE
            )
            total_weight_sum = sum(
                item.weight.value * item.confidence for item in profile.evidence_items
            )

            if total_weight_sum > 0:
                base_uniqueness = unique_weight_sum / total_weight_sum

        # Apply complexity enhancement to uniqueness
        enhanced_uniqueness = base_uniqueness
        complexity_score = 0.0

        if profile.complexity_metrics:
            complexity_score = profile.complexity_metrics.complexity_score
            complexity_amplification = (
                self.complexity_analyzer.calculate_complexity_amplification(
                    profile.complexity_metrics
                )
            )
            # Use the higher of base uniqueness and complexity-enhanced uniqueness
            enhanced_uniqueness = max(
                base_uniqueness,
                base_uniqueness * (complexity_amplification - 1.0) + 0.0,
            )
            enhanced_uniqueness = min(enhanced_uniqueness, 1.0)

        penalty_factor = 1.0
        if any(
            item.source == EvidenceSource.FIELD_PATTERN_MISMATCH
            for item in profile.evidence_items
        ):
            penalty_factor = min(penalty_factor, PATTERN_MISMATCH_PENALTY)
        elif (
            profile.format_name in SPARSE_EVIDENCE_FORMATS
            and unique_count == 0
            and total_count <= 3
        ):
            # Penalize formats that only produced generic indicators. This keeps simple
            # "tests" payloads from being misclassified as TestRail or TestLink.
            penalty_factor = min(penalty_factor, SPARSE_EVIDENCE_PENALTY)
        elif profile.format_name in REQUIRED_FIELD_FORMATS and any(
            item.source.is_missing() for item in profile.evidence_items
        ):
            # Missing required indicators should dramatically reduce confidence for the
            # structured formats that rely on them.
            penalty_factor = min(penalty_factor, REQUIRED_FIELD_PENALTY)

        return EvidenceMetrics(
            completeness=completeness,
            quality=quality,
            uniqueness=enhanced_uniqueness,
            evidence_count=total_count,
            unique_count=unique_count,
            complexity_score=complexity_score,
            penalty_factor=penalty_factor,
        )

    def optimize_parameters(self, training_data: list[tuple[str, float]]) -> None:
        """Optimize weighted evidence parameters using training data.

        Args:
            training_data: List of (format_name, expected_confidence) pairs
        """
        # Convert training data to EvidenceMetrics format
        scorer_training_data = []

        for format_name, expected_confidence in training_data:
            if format_name in self.evidence_profiles:
                profile = self.evidence_profiles[format_name]
                metrics = self._profile_to_metrics(profile)
                scorer_training_data.append((metrics, expected_confidence))

        if scorer_training_data:
            # Note: Parameter optimization not yet implemented
            # for IndependentBayesianScorer
            logger.info(
                "Parameter optimization requested but not yet implemented "
                "for IndependentBayesianScorer"
            )

    def get_parameter_summary(self) -> dict[str, Any]:
        """Get summary of optimized weighted evidence parameters."""
        return self.bayesian_scorer.get_parameter_summary()

    def get_detection_confidence(self, format_name: str) -> dict[str, Any]:
        """Get comprehensive confidence metrics using weighted evidence approach."""
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

        # Get detailed confidence analysis from Independent Bayesian scorer
        scorer_result = self.bayesian_scorer.calculate_confidence(
            metrics, format_name, use_uncertainty=True
        )

        confidence = scorer_result["confidence"]

        # Determine confidence level
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            confidence_level = "HIGH"
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            confidence_level = "MEDIUM"
        elif confidence >= self.LOW_CONFIDENCE_THRESHOLD:
            confidence_level = "LOW"
        else:
            confidence_level = "INSUFFICIENT"

        # Combine scorer results with profile information
        result = {
            "confidence": confidence,
            "evidence_quality": profile.evidence_quality,
            "evidence_completeness": metrics.completeness,
            "evidence_count": len(profile.evidence_items),
            "confidence_level": confidence_level,
            "unique_evidence_count": profile.unique_evidence_count,
            "strong_evidence_count": profile.strong_evidence_count,
            "likelihood": scorer_result.get("likelihood", 0.0),
            "prior": scorer_result.get("prior", 0.0),
        }

        # Add uncertainty bounds if available
        if "confidence_lower_95" in scorer_result:
            result.update(
                {
                    "confidence_lower_95": scorer_result["confidence_lower_95"],
                    "confidence_upper_95": scorer_result["confidence_upper_95"],
                    "confidence_std": scorer_result["confidence_std"],
                }
            )

        return result

    def handle_ties(
        self, format_scores: dict[str, float]
    ) -> tuple[str, float, dict[str, str]]:
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
    ) -> dict[str, Any]:
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
