"""Independent Bayesian evidence scorer.

This module exposes the full probability model: independence assumptions,
log-probability accumulation, and the quadratic P(E|¬H) decay. The helpers are
shared by the unit tests that guard the 1.5:1 ambiguity cap and the benchmark
jobs in CI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

from importobot.utils.logging import get_logger

from .evidence_metrics import EvidenceMetrics
from .shared_config import (
    DEFAULT_FORMAT_PRIORS,
    P_E_NOT_H_HARDCODED,
    P_E_NOT_H_LEARNED,
    P_E_NOT_H_MODE,
)
from .test_case_complexity_analyzer import ComplexityMetrics

logger = get_logger()

LOG_LIKELIHOOD_FLOOR = 1e-12  # Keeps log products bounded (~-27.6) for three factors
AMBIGUOUS_RATIO_CAP = 1.5  # Caps weak signals so the posterior stays near the priors
STRONG_EVIDENCE_RATIO_CAP = 3.0  # Caps strong signals so likelihood ratios stay bounded


@dataclass
class BayesianConfiguration:
    """Mathematical configuration for Bayesian inference parameters.

    This configuration contains all mathematical constants used in Bayesian inference
    with clear theoretical justification for each value.
    """

    # P(E|¬H) Estimation Parameters
    # ================================
    # These parameters control how we estimate P(E|¬H) - the probability that
    # observed evidence would be generated if the format is NOT the hypothesized one.

    # Minimum P(E|¬H): Lower bound for evidence coming from wrong format
    # Mathematical basis: Even with perfect evidence (likelihood=1.0), there's always
    # some probability it could be from the wrong format due to measurement error or
    # coincidental structural patterns. This prevents overconfidence.
    min_evidence_not_format: float = 0.01  # 1% chance perfect evidence is wrong format

    # Scale Factor: Controls how quickly P(E|¬H) decreases with stronger evidence
    # Mathematical basis: With quadratic decay (c=2): P(E|¬H) = 0.01 + 0.49 * (1-L)²
    # When L=0.0: P(E|¬H) = 0.50 (maximum ambiguity - weak evidence could be anything)
    # When L=1.0: P(E|¬H) = 0.01 (minimum ambiguity - perfect evidence is specific)
    evidence_not_format_scale: float = 0.49

    # Decay Exponent: Shape parameter for P(E|¬H) vs likelihood relationship
    # Mathematical basis: Exponent > 1 provides convex relationship, ensuring
    # diminishing returns for evidence strength. Quadratic (c=2) is mathematically
    # well-behaved and provides good discrimination for format detection.
    evidence_not_format_exponent: float = 2.0

    # Numerical Stability Parameters
    # =========================
    # These parameters prevent numerical issues in Bayesian calculations.

    # Division by Zero Prevention: Small epsilon to avoid denominator = 0
    # Mathematical basis: Bayes' theorem requires P(E) > 0 for valid posterior.
    # This epsilon ensures computational stability while preserving meaning.
    numerical_epsilon: float = 1e-15

    def validate(self) -> bool:
        """Validate that all configuration parameters are within acceptable bounds."""
        # Check each parameter bound separately
        min_format_ok = 0.0 < self.min_evidence_not_format < 0.05
        scale_ok = 0.0 < self.evidence_not_format_scale < 1.0
        exponent_ok = 1.0 <= self.evidence_not_format_exponent <= 5.0
        epsilon_ok = 1e-20 < self.numerical_epsilon < 1e-10

        return all([min_format_ok, scale_ok, exponent_ok, epsilon_ok])

    def get_p_e_not_h_params(self) -> dict[str, float]:
        """Get P(E|¬H) parameters based on current mode."""
        if P_E_NOT_H_MODE == "learned":
            # Filter out None values from learned parameters
            return {k: v for k, v in P_E_NOT_H_LEARNED.items() if v is not None}
        return P_E_NOT_H_HARDCODED


class EvidenceType(str, Enum):
    """Types of evidence used in format detection.

    Each evidence type contributes independently to the overall likelihood
    calculation under the Naive Bayes independence assumption.
    """

    COMPLETENESS = "completeness"
    QUALITY = "quality"
    UNIQUENESS = "uniqueness"


@dataclass
class IndependentBayesianParameters:
    """Parameters for independent Bayesian evidence scoring.

    These parameters define Beta distributions and mathematical
    parameters for evidence scoring based on discriminative analysis.

    Beta Distribution Parameters:
    - Alpha > Beta favors higher values (good for quality/completeness)
    - Beta > Alpha favors lower values (good for uniqueness, which should be rare)
    """

    # Beta distribution parameters for evidence quality (0-1 range)
    # Alpha > Beta favors higher quality scores
    quality_alpha: float = 3.0
    quality_beta: float = 1.5

    # Beta distribution parameters for completeness (0-1 range)
    # Alpha > Beta favors higher completeness
    completeness_alpha: float = 4.0
    completeness_beta: float = 1.0

    # Beta distribution parameters for uniqueness (0-1 range)
    # Monotonic increasing distribution (Alpha > Beta) to ensure coherence
    # Higher uniqueness values should always have higher likelihood
    uniqueness_alpha: float = 3.0
    uniqueness_beta: float = 1.5

    # Numerical stability parameters
    min_log_likelihood: float = -20.0
    max_log_likelihood: float = 2.0  # Increased to allow higher likelihoods

    def validate(self) -> bool:
        """Validate that parameters are within acceptable ranges."""
        # Beta distribution parameters must be positive
        beta_params_valid = all(
            p > 0
            for p in [
                self.quality_alpha,
                self.quality_beta,
                self.completeness_alpha,
                self.completeness_beta,
                self.uniqueness_alpha,
                self.uniqueness_beta,
            ]
        )

        # Log likelihood bounds
        bounds_valid = self.min_log_likelihood < self.max_log_likelihood

        return beta_params_valid and bounds_valid


class IndependentBayesianScorer:
    """Bayesian evidence scorer using evidence independence assumptions.

    This scorer implements proper Bayesian inference using:
    1. Independence assumptions for evidence combination
    2. Log-likelihood calculations for numerical stability
    3. Proper probability distributions for each evidence type
    4. Bayesian updating with P(E|¬H) estimation for proper multi-class inference
    5. Mathematically rigorous posterior calculation using Bayes' theorem

    The key innovation is treating different evidence types as independent
    random variables rather than components of an arbitrary weighted sum,
    while ensuring proper Bayesian normalization across all format hypotheses.
    """

    def __init__(
        self,
        format_priors: dict[str, float] | None = None,
        parameters: IndependentBayesianParameters | None = None,
    ):
        """Initialize the independent Bayesian scorer.

        Args:
            format_priors: Prior probabilities for each format type
            parameters: Bayesian parameters for evidence scoring
        """
        self.format_priors = format_priors or DEFAULT_FORMAT_PRIORS
        self.parameters = parameters or IndependentBayesianParameters()

        # Initialize Bayesian configuration with mathematical constants
        self.bayesian_config = BayesianConfiguration()
        if not self.bayesian_config.validate():
            raise ValueError("Invalid Bayesian configuration parameters")

        if not self.parameters.validate():
            raise ValueError("Invalid Bayesian parameters")

    def _conservative_likelihood_mapping(self, value: float) -> float:
        """Map a metric in [0, 1] into [0.05, 0.90] before any boosts.

        The 0.05 floor keeps the product of three evidence terms away from zero,
        and the 0.90 ceiling leaves headroom for amplification without breaching
        probabilistic bounds.
        """
        return 0.05 + 0.85 * value

    def _amplify_strong_evidence(
        self, base_likelihood: float, evidence_type: EvidenceType, value: float
    ) -> float:
        """Boost strong evidence while keeping the result ≤ 0.95.

        Uniqueness gets the biggest multiplier because it is usually scarce.
        Completeness and quality receive lighter boosts so the scorer does not
        outrun the ambiguity caps.
        """
        if evidence_type == EvidenceType.UNIQUENESS and value > 0.9:
            # Very strong uniqueness evidence - highest amplification
            amplified = base_likelihood * 1.5
            return min(amplified, 0.95)
        if evidence_type == EvidenceType.UNIQUENESS and value > 0.8:
            # Strong uniqueness evidence - moderate amplification
            amplified = base_likelihood * 1.2
            return min(amplified, 0.90)
        if value > 0.9:
            # Very strong completeness/quality evidence - light amplification
            amplified = base_likelihood * 1.1
            return min(amplified, 0.85)
        # No amplification for moderate/weak evidence
        return base_likelihood

    def _metric_to_likelihood(self, value: float, evidence_type: EvidenceType) -> float:
        """Convert evidence metric to proper likelihood P(metric|format).

        Research-backed implementation combining conservative baseline with
        evidence amplification for discriminative power while maintaining
        mathematical soundness and prevent extreme overconfidence.

        Mathematical Principle:
            1. Start with conservative baseline mapping
            2. Apply amplification for strong evidence
            3. Ensure bounds to prevent overconfidence

        Args:
            value: Evidence metric value in [0, 1]
            evidence_type: Type of evidence (from EvidenceType enum)

        Returns:
            Calibrated likelihood probability in [0, 1]
        """
        # Step 1: Conservative baseline likelihood
        base_likelihood = self._conservative_likelihood_mapping(value)

        # Step 2: Apply evidence amplification for strong indicators
        amplified_likelihood = self._amplify_strong_evidence(
            base_likelihood, evidence_type, value
        )

        return amplified_likelihood

    def _apply_likelihood_ratio_capping(
        self,
        likelihoods: dict[str, float],
        max_ratio: float = STRONG_EVIDENCE_RATIO_CAP,
    ) -> dict[str, float]:
        """Clamp low-probability formats so ratios stay within an interpretable band."""
        if not likelihoods:
            return likelihoods

        max_likelihood = max(likelihoods.values())
        if max_likelihood <= 0:
            return likelihoods

        # Adaptive ratio based on evidence strength
        if max_likelihood <= 0.3:
            # Very weak/ambiguous evidence - use conservative ratio
            effective_max_ratio = AMBIGUOUS_RATIO_CAP
        else:
            # Moderate to strong evidence - allow more discriminative power
            effective_max_ratio = max_ratio

        capped_likelihoods = {}
        for format_name, likelihood in likelihoods.items():
            ratio = likelihood / max_likelihood if max_likelihood > 0 else 0

            # Apply adaptive ratio capping
            if ratio < 1.0 / effective_max_ratio:
                # This likelihood is too low compared to the maximum
                # Boost it to maintain the maximum allowed ratio
                capped_likelihood = max_likelihood / effective_max_ratio
                capped_likelihoods[format_name] = capped_likelihood
            else:
                # This likelihood is within acceptable bounds
                capped_likelihoods[format_name] = likelihood

        return capped_likelihoods

    def calculate_likelihood(self, metrics: EvidenceMetrics) -> float:
        """Calculate likelihood using research-backed Bayesian approach.

        Mathematical Foundation:
        - Naive Bayes independence: P(E1,E2,E3|H) = P(E1|H) * P(E2|H) * P(E3|H)
        - Conservative baseline with evidence amplification
        - Likelihood ratio capping to prevent extreme discrimination
        - Log-likelihood for numerical stability

        Args:
            metrics: Evidence metrics for the format

        Returns:
            Calibrated likelihood P(Evidence|Format) in (0, 1] range
        """
        # Calculate individual component likelihoods using research-backed approach
        completeness_likelihood = self._metric_to_likelihood(
            metrics.completeness, EvidenceType.COMPLETENESS
        )
        quality_likelihood = self._metric_to_likelihood(
            metrics.quality, EvidenceType.QUALITY
        )
        uniqueness_likelihood = self._metric_to_likelihood(
            metrics.uniqueness, EvidenceType.UNIQUENESS
        )

        # Independence assumption: multiply likelihoods
        # Use log-space for numerical stability (standard Naive Bayes practice)
        floor = max(self.bayesian_config.numerical_epsilon, LOG_LIKELIHOOD_FLOOR)
        log_likelihood = (
            math.log(max(completeness_likelihood, floor))
            + math.log(max(quality_likelihood, floor))
            + math.log(max(uniqueness_likelihood, floor))
        )

        # Convert back from log-space
        raw_likelihood = math.exp(log_likelihood)
        raw_likelihood *= getattr(metrics, "penalty_factor", 1.0)

        # Apply conservative bounds to prevent overconfidence
        # Even the strongest evidence should not exceed 95% likelihood
        calibrated_likelihood = min(raw_likelihood, 0.95)

        return float(calibrated_likelihood)

    def calculate_posterior(
        self,
        likelihood: float,
        format_name: str,
        metrics: EvidenceMetrics | None = None,
    ) -> float:
        """Calculate posterior probability using proper multi-class Bayesian inference.

        Mathematical Framework (Multi-Class):
            P(H_i|E) = P(E|H_i) * P(H_i) / Σ_j[P(E|H_j) * P(H_j)]

        where:
            H_i = "Data is from format i"
            E = Observed evidence metrics
            P(H_i) = prior probability of format i
            P(E|H_i) = likelihood of evidence given format i
            Σ_j = sum over all possible formats

        This is the mathematically correct normalization for multi-class classification.
        Unlike binary classification, we cannot use P(E|¬H) as a single value because
        "not format X" comprises multiple specific alternative formats, each with their
        own likelihood of producing the observed evidence.

        Args:
            likelihood: P(E|H_i) - likelihood from evidence for this format
            format_name: Name of the format being evaluated
            metrics: Evidence metrics for context (optional but recommended)

        Returns:
            Posterior probability P(H_i|E) in [0, 1] range
        """
        # Get P(E|¬H) parameters based on current mode
        p_e_not_h_params = self.bayesian_config.get_p_e_not_h_params()

        # Numerator: P(E|H_i) * P(H_i)
        prior = self.format_priors.get(format_name, 0.1)
        numerator = likelihood * prior

        # Denominator: Σ_j[P(E|H_j) * P(H_j)] for all formats
        # This is the proper normalization constant for multi-class classification
        denominator = numerator  # Start with current format's contribution

        # Add contributions from all other formats using P(E|¬H) estimation
        for other_format, other_prior in self.format_priors.items():
            if other_format == format_name:
                continue  # Already counted in numerator

            # Estimate likelihood for other format using P(E|¬H) approach
            # Strong evidence for current format means weaker evidence for others
            other_likelihood = self._estimate_p_e_not_h_for_other_format(
                likelihood, other_format, metrics, p_e_not_h_params
            )

            denominator += other_likelihood * other_prior

        # Avoid division by zero
        if denominator < self.bayesian_config.numerical_epsilon:
            # No format can explain the evidence - very low confidence
            return 0.0

        posterior = numerator / denominator
        return float(max(0.0, min(1.0, posterior)))

    def calculate_posterior_distribution(
        self, all_metrics: dict[str, EvidenceMetrics]
    ) -> dict[str, float]:
        """Return a normalized posterior for every format with metrics.

        This helper is deliberately explicit: it multiplies each likelihood by the
        configured prior, sums the contributions, and returns posteriors whose sum
        is one (bar floating point noise). Callers that only care about a single
        format can continue to use ``calculate_posterior``.
        """
        if not all_metrics:
            return {}

        weighted_likelihoods: dict[str, float] = {}
        denominator = 0.0
        for format_name, metrics in all_metrics.items():
            likelihood = self.calculate_likelihood(metrics)
            prior = self.format_priors.get(format_name, 0.1)
            weighted = likelihood * prior
            weighted_likelihoods[format_name] = weighted
            denominator += weighted

        if denominator < self.bayesian_config.numerical_epsilon:
            # ruff: noqa: C420 -- dict.fromkeys would drop the float type annotation
            return {name: 0.0 for name in weighted_likelihoods}

        normalization_factor = 1.0 / denominator
        return {
            name: max(0.0, min(1.0, weighted * normalization_factor))
            for name, weighted in weighted_likelihoods.items()
        }

    def _estimate_p_e_not_h_for_other_format(
        self,
        current_likelihood: float,
        other_format: str,
        metrics: EvidenceMetrics | None,
        p_e_not_h_params: dict[str, float],
    ) -> float:
        """Estimate P(E|other_format) using P(E|¬H) approach.

        This method estimates how likely the observed evidence would be if it came
        from a different format than the one being evaluated.

        Args:
            current_likelihood: Likelihood P(E|current_format)
            other_format: Name of the alternative format
            metrics: Evidence metrics for additional context
            p_e_not_h_params: P(E|¬H) parameters (a, b, c)

        Returns:
            Estimated likelihood P(E|other_format)
        """
        # Get P(E|¬H) parameters
        a = p_e_not_h_params.get("a", 0.01)
        b = p_e_not_h_params.get("b", 0.49)
        c = p_e_not_h_params.get("c", 2.0)

        # Base P(E|¬H) using quadratic decay formula
        # P(E|¬H) = a + b * (1 - L) ** c
        base_p_e_not_h = a + b * (1.0 - current_likelihood) ** c

        # Apply format-specific adjustments
        format_adjustment = self._get_format_specific_adjustment(other_format, metrics)

        # Apply evidence strength adjustment
        evidence_strength = (
            self._calculate_evidence_strength(metrics) if metrics else 1.0
        )

        # Final estimated likelihood for other format
        other_likelihood = base_p_e_not_h * format_adjustment * evidence_strength

        # Ensure reasonable bounds
        return float(max(1e-10, min(1.0, other_likelihood)))

    def _get_format_specific_adjustment(
        self, format_name: str, metrics: EvidenceMetrics | None
    ) -> float:
        """Get format-specific adjustment factor for P(E|¬H) estimation.

        Different formats have different structural ambiguity profiles:
        - XML formats (TestLink): More tolerant of structural errors
        - JSON formats (TestRail): Stricter on field matching
        - JIRA formats (Xray/Zephyr): Moderate tolerance with custom fields

        Args:
            format_name: Name of the format being evaluated
            metrics: Evidence metrics for additional context

        Returns:
            Adjustment factor (typically 0.8-1.2) to scale P(E|¬H)
        """
        # Base adjustments by format family
        format_adjustments = {
            "TESTLINK": 1.1,  # XML can be ambiguous, slightly higher P(E|¬H)
            "TESTRAIL": 0.9,  # JSON is more structured, lower P(E|¬H)
            "JIRA_XRAY": 1.0,  # Standard JIRA patterns
            "ZEPHYR": 1.0,  # JIRA-based, moderate ambiguity
            "GENERIC": 1.2,  # Generic formats are most ambiguous
            "UNKNOWN": 1.5,  # Unknown formats get highest ambiguity
        }

        base_adjustment = format_adjustments.get(format_name.upper(), 1.0)

        # Quality-based adjustment: poor evidence increases ambiguity
        if metrics and metrics.quality < 0.5:
            quality_multiplier = 1.0 + (0.5 - metrics.quality)  # 1.0-1.5 range
        else:
            quality_multiplier = 1.0

        return base_adjustment * quality_multiplier

    def _calculate_evidence_strength(self, metrics: EvidenceMetrics | None) -> float:
        """Calculate overall evidence strength for adaptive P(E|¬H) estimation.

        Combines multiple aspects of evidence quality:
        - Completeness: How much required evidence is present
        - Quality: Average confidence of individual evidence items
        - Uniqueness: How distinctive the evidence is
        - Quantity: Total amount of evidence available
        - Complexity: Richness and information content

        Args:
            metrics: Evidence metrics to evaluate

        Returns:
            Evidence strength factor (typically 0.5-2.0)
        """
        if not metrics:
            return 1.0

        # Base strength from quality and completeness
        base_strength = (metrics.quality + metrics.completeness) / 2.0

        # Uniqueness bonus: unique evidence is more valuable
        uniqueness_bonus = metrics.uniqueness * 0.3

        # Quantity consideration: more evidence increases confidence
        if metrics.evidence_count >= 5:
            quantity_factor = 1.0
        elif metrics.evidence_count >= 2:
            quantity_factor = 0.8 + (metrics.evidence_count - 2) * 0.1  # 0.8-0.9
        else:
            quantity_factor = 0.7  # Very little evidence

        # Complexity bonus: richer test cases provide stronger evidence
        complexity_bonus = 0.0
        if hasattr(metrics, "complexity_score"):
            # Bonus for high-complexity evidence (max 0.3)
            complexity_bonus = min(metrics.complexity_score * 0.3, 0.3)

        # Combine all factors
        evidence_strength = base_strength + uniqueness_bonus + complexity_bonus
        evidence_strength *= quantity_factor

        # Ensure reasonable bounds
        return max(0.5, min(2.0, evidence_strength))

    def apply_complexity_amplification(
        self,
        likelihoods: dict[str, float],
        complexity_metrics: dict[str, ComplexityMetrics | None],
    ) -> dict[str, float]:
        """Apply complexity-based amplification to likelihoods.

        This method enhances discriminative power for complex test cases
        while maintaining mathematical soundness through controlled amplification.

        Mathematical Principle:
        P_enhanced = P_base * (1 + alpha * complexity_score)
        Where alpha is the complexity amplification factor.

        Args:
            likelihoods: Base likelihoods for each format
            complexity_metrics: Complexity metrics for each format

        Returns:
            Enhanced likelihoods with complexity amplification applied
        """
        enhanced_likelihoods = likelihoods.copy()

        for format_name, base_likelihood in likelihoods.items():
            complexity = complexity_metrics.get(format_name)

            if complexity:
                # Calculate complexity amplification (1.0 to 1.3 max)
                amplification = 1.0 + min(complexity.complexity_score * 0.3, 0.3)

                # Apply amplification
                enhanced_likelihood = base_likelihood * amplification

                # Cap at maximum allowed likelihood
                enhanced_likelihood = min(enhanced_likelihood, 0.95)

                enhanced_likelihoods[format_name] = enhanced_likelihood

                logger.debug(
                    "Applied %.3fx complexity amplification to %s: %.3f -> %.3f",
                    amplification,
                    format_name,
                    base_likelihood,
                    enhanced_likelihood,
                )

        return enhanced_likelihoods

    def calculate_discriminative_score(self, metrics: EvidenceMetrics) -> float:
        """Calculate discriminative score emphasizing unique evidence.

        This method provides stronger discrimination for format-specific evidence
        while maintaining mathematical rigor through likelihood ratios.

        Args:
            metrics: Evidence metrics for the format

        Returns:
            Discriminative score in [0, 1] range
        """
        base_likelihood = self.calculate_likelihood(metrics)

        # Apply uniqueness boost for formats with unique indicators
        # The Beta distribution for uniqueness (alpha=3.0, beta=1.5) provides
        # monotonic discrimination, but we add additional emphasis
        if metrics.uniqueness > 0.0:
            # Uniqueness boost proportional to observed uniqueness
            uniqueness_boost = 1.0 + (
                metrics.uniqueness * 0.7
            )  # Max 1.7x boost (increased)
            discriminative_score = base_likelihood * uniqueness_boost
        else:
            discriminative_score = base_likelihood

        return float(max(0.0, min(1.0, discriminative_score)))

    def _apply_complexity_amplification_to_all(
        self, likelihoods: dict[str, float], all_metrics: dict[str, EvidenceMetrics]
    ) -> dict[str, float]:
        """Apply complexity-based amplification across all formats.

        This method enhances discriminative power for complex test cases
        by applying complexity amplification to formats with complexity metrics.

        Args:
            likelihoods: Base likelihoods for each format
            all_metrics: Evidence metrics for all formats

        Returns:
            Complexity-enhanced likelihoods
        """
        enhanced_likelihoods = likelihoods.copy()

        for format_name, base_likelihood in likelihoods.items():
            metrics = all_metrics.get(format_name)

            if metrics and hasattr(metrics, "complexity_score"):
                complexity_score = getattr(metrics, "complexity_score", 0.0)

                if complexity_score > 0.0:
                    # Calculate complexity amplification (1.0 to 1.3 max)
                    amplification = 1.0 + min(complexity_score * 0.3, 0.3)

                    # Apply amplification with bounds
                    enhanced_likelihood = base_likelihood * amplification
                    enhanced_likelihood = min(enhanced_likelihood, 0.95)

                    enhanced_likelihoods[format_name] = enhanced_likelihood

                    logger.debug(
                        "Complexity amplification for %s: %.3f -> %.3f "
                        "(complexity: %.3f, amp: %.3f)",
                        format_name,
                        base_likelihood,
                        enhanced_likelihood,
                        complexity_score,
                        amplification,
                    )

        return enhanced_likelihoods

    def calculate_all_format_likelihoods(
        self, all_metrics: dict[str, EvidenceMetrics]
    ) -> dict[str, float]:
        """Calculate likelihoods for all formats with complexity enhancement.

        Applies ratio capping and complexity-based amplification for enhanced
        discrimination.

        This method implements the research-backed approach:
        1. Calculate raw likelihoods using evidence metrics
        2. Apply complexity-based amplification for enhanced discrimination
        3. Apply likelihood ratio capping to prevent extreme discrimination
        4. Maintain discriminative power while ensuring numerical stability

        Args:
            all_metrics: Dictionary mapping format names to their evidence metrics

        Returns:
            Dictionary mapping format names to calibrated likelihoods.
        """
        if not all_metrics:
            return {}

        # Step 1: Calculate raw likelihoods for all formats
        raw_likelihoods = {}
        for format_name, metrics in all_metrics.items():
            raw_likelihoods[format_name] = self.calculate_likelihood(metrics)

        # Step 2: Apply complexity-aware amplification
        complexity_enhanced_likelihoods = self._apply_complexity_amplification_to_all(
            raw_likelihoods, all_metrics
        )

        # Step 3: Apply likelihood ratio capping to prevent extreme discrimination
        capped_likelihoods = self._apply_likelihood_ratio_capping(
            complexity_enhanced_likelihoods
        )

        return capped_likelihoods

    def get_evidence_likelihoods(self, metrics: EvidenceMetrics) -> dict[str, float]:
        """Calculate likelihoods for different evidence components.

        Provides transparency into how different evidence types contribute
        to the overall likelihood calculation using proper likelihood functions.

        Args:
            metrics: Evidence metrics for the format

        Returns:
            Dictionary with likelihood components and overall likelihood
        """
        components = {}

        # Calculate individual component likelihoods using proper likelihood functions
        components[EvidenceType.COMPLETENESS.value] = self._metric_to_likelihood(
            metrics.completeness, EvidenceType.COMPLETENESS
        )
        components[EvidenceType.QUALITY.value] = self._metric_to_likelihood(
            metrics.quality, EvidenceType.QUALITY
        )
        components[EvidenceType.UNIQUENESS.value] = self._metric_to_likelihood(
            metrics.uniqueness, EvidenceType.UNIQUENESS
        )

        # Overall likelihood (product of independent components)
        components["overall"] = self.calculate_likelihood(metrics)
        return components

    def calculate_confidence(
        self, metrics: EvidenceMetrics, format_name: str, use_uncertainty: bool = False
    ) -> dict[str, float]:
        """Calculate confidence using independent Bayesian approach.

        This method provides compatibility with the EvidenceAccumulator interface
        while using proper Bayesian inference with P(E|¬H) estimation.

        Args:
            metrics: Evidence metrics for the format
            format_name: Name of the format being evaluated
            use_uncertainty: Whether to include parameter uncertainty
                (not implemented yet)

        Returns:
            Dictionary with confidence score and related metrics
        """
        # Calculate likelihood using independent Bayesian approach
        likelihood = self.calculate_likelihood(metrics)

        # Apply proper Bayesian inference with P(E|¬H) estimation
        posterior_confidence = self.calculate_posterior(
            likelihood, format_name, metrics
        )

        result = {
            "confidence": posterior_confidence,
            "likelihood": likelihood,
            "prior": self.format_priors.get(format_name, 0.1),
        }

        # Note: Uncertainty bounds not yet implemented for independent scorer
        if use_uncertainty:
            logger.info(
                "Uncertainty bounds not yet implemented for IndependentBayesianScorer"
            )

        return result

    def get_parameter_summary(self) -> dict[str, Any]:
        """Get summary of Bayesian parameters for transparency."""
        return {
            "parameters": self.parameters.__dict__,
            "parameter_valid": self.parameters.validate(),
            "bayesian_config": self.bayesian_config.__dict__,
            "bayesian_config_valid": self.bayesian_config.validate(),
            "format_priors": self.format_priors,
            "p_e_not_h_mode": P_E_NOT_H_MODE,
            "p_e_not_h_params": self.bayesian_config.get_p_e_not_h_params(),
            "mathematical_approach": (
                "Independent evidence with proper Bayesian inference"
            ),
        }


__all__ = [
    "BayesianConfiguration",
    "EvidenceMetrics",
    "EvidenceType",
    "IndependentBayesianParameters",
    "IndependentBayesianScorer",
]
