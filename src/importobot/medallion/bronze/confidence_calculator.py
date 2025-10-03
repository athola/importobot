"""Confidence calculation algorithms for format detection."""

from __future__ import annotations

import math
from typing import Any, Callable, Dict

from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.utils.logging import setup_logger

from .shared_config import PRIORITY_MULTIPLIERS

logger = setup_logger(__name__)


class ConfidenceCalculator:
    """Calculates confidence scores for format detection."""

    # Temperature values for adaptive confidence calculation
    HIGH_EVIDENCE_TEMPERATURE = 0.5  # For scores >= 10.0
    MODERATE_EVIDENCE_TEMPERATURE = 0.65  # For scores >= 7.0
    LOW_EVIDENCE_TEMPERATURE = 0.8  # For scores < 7.0

    # Score thresholds for evidence classification
    HIGH_EVIDENCE_THRESHOLD = 10.0
    MODERATE_EVIDENCE_THRESHOLD = 7.0
    BASIC_EVIDENCE_THRESHOLD = 4.0

    # Baseline confidence levels
    HIGH_BASELINE_CONFIDENCE = 0.90
    MODERATE_BASELINE_CONFIDENCE = 0.80
    BASIC_BASELINE_CONFIDENCE = 0.65
    MINIMAL_BASELINE_CONFIDENCE = 0.50
    MINIMAL_EVIDENCE_DIVISOR = 8.0

    # Fallback confidence thresholds and values
    FALLBACK_UNIQUE_SCORE_THRESHOLD = 5
    FALLBACK_UNIQUE_COMPETITION_THRESHOLD = 2.0
    FALLBACK_UNIQUE_CONFIDENCE = 0.75

    FALLBACK_STRONG_SCORE_THRESHOLD = 3
    FALLBACK_STRONG_SPREAD_THRESHOLD = 2.0
    FALLBACK_STRONG_CONFIDENCE = 0.65

    FALLBACK_MINIMAL_CONFIDENCE = 0.55

    # Evidence scaling thresholds and values
    EVIDENCE_SCALE_HIGH_THRESHOLD = 10.0
    EVIDENCE_SCALE_HIGH_DIVISOR = 12.0
    EVIDENCE_SCALE_HIGH_MAX = 0.95

    EVIDENCE_SCALE_MODERATE_THRESHOLD = 7.0
    EVIDENCE_SCALE_MODERATE_DIVISOR = 10.0
    EVIDENCE_SCALE_MODERATE_MAX = 0.85

    EVIDENCE_SCALE_BASIC_THRESHOLD = 4.0
    EVIDENCE_SCALE_BASIC_DIVISOR = 8.0
    EVIDENCE_SCALE_BASIC_MAX = 0.70

    EVIDENCE_SCALE_MINIMAL_DIVISOR = 6.0

    # Logistic function limits
    LOGISTIC_VALUE_MAX = 50.0
    LOGISTIC_VALUE_MIN = -50.0

    # Simple scoring values
    REQUIRED_KEY_SCORE = 3
    OPTIONAL_KEY_SCORE = 1

    # Bayesian reasoning constants
    PRIOR_PROBABILITY_BASE = 0.1  # Base prior for unknown formats
    PRIOR_PROBABILITY_BOOST = 0.05  # Boost for known format patterns
    EVIDENCE_WEIGHT_REQUIRED = 2.0  # Weight for required field evidence
    EVIDENCE_WEIGHT_OPTIONAL = 0.5  # Weight for optional field evidence
    EVIDENCE_WEIGHT_STRUCTURE = 1.5  # Weight for structural evidence
    BAYESIAN_SMOOTHING_FACTOR = 1.0  # Laplace smoothing
    CONFIDENCE_THRESHOLD_MIN = 0.01  # Minimum meaningful confidence
    CONFIDENCE_THRESHOLD_MAX = 0.99  # Maximum achievable confidence
    PATTERN_MATCH_BONUS = 0.2  # Bonus for matching known patterns
    NEGATIVE_EVIDENCE_PENALTY = 0.1  # Penalty for contradictory evidence

    def __init__(self, format_patterns: Dict[SupportedFormat, Dict[str, Any]]):
        """Initialize confidence calculator with format patterns."""
        self.format_patterns = format_patterns
        self.priority_multipliers = PRIORITY_MULTIPLIERS

    def get_format_confidence(
        self,
        data: Dict[str, Any],
        format_type: SupportedFormat,
        data_str: str,
        calculate_format_score_func: Callable,
    ) -> float:
        """Return a fast, deterministic confidence estimate for a specific format.

        Args:
            data: Data sample to analyse. Non-dictionaries always yield 0.0.
            format_type: Target format to compute confidence for.
            data_str: String representation of data for efficiency.
            calculate_format_score_func: Function to calculate format scores.

        Returns:
            A float between 0.0 and 1.0 representing the relative strength of
            evidence for format_type compared to other supported formats.
        """
        if not self._is_valid_input(data, format_type, data_str):
            return 0.0

        weighted_scores = self._calculate_weighted_scores(
            data, data_str, calculate_format_score_func
        )

        target_score = weighted_scores.get(format_type, 0.0)
        if target_score <= 0.0:
            return 0.0

        score_info = self._get_scoring_info(weighted_scores, format_type)
        if score_info["detected_score"] <= 0.0 and score_info["second_best"] <= 0.0:
            return 0.0

        confidence = self._calculate_confidence(score_info, format_type)

        # Apply fallback confidence mechanism for edge cases
        confidence = self._apply_fallback_confidence(
            confidence, score_info, format_type
        )

        if format_type == score_info["detected_format"]:
            confidence = self._apply_baseline_boost(
                confidence, score_info["detected_score"]
            )

        return float(max(0.0, min(1.0, confidence)))

    def _is_valid_input(
        self, data: Dict[str, Any], format_type: SupportedFormat, data_str: str
    ) -> bool:
        """Validate input parameters."""
        return (
            isinstance(data, dict)
            and format_type in self.format_patterns
            and bool(data_str)
        )

    def _calculate_weighted_scores(
        self, data: Dict[str, Any], data_str: str, calculate_format_score_func: Callable
    ) -> Dict[SupportedFormat, float]:
        """Calculate weighted scores for all formats."""
        weighted_scores: Dict[SupportedFormat, float] = {}
        for candidate, patterns in self.format_patterns.items():
            raw_score = calculate_format_score_func(data_str, patterns, data)
            multiplier = self.priority_multipliers.get(candidate, 1.0)
            weighted_scores[candidate] = max(0.0, raw_score * multiplier)
        return weighted_scores

    def _get_scoring_info(
        self,
        weighted_scores: Dict[SupportedFormat, float],
        target_format: SupportedFormat,
    ) -> Dict:
        """Extract scoring information from weighted scores."""
        detected_format = max(
            weighted_scores, key=lambda x: weighted_scores.get(x, 0.0)
        )
        detected_score = weighted_scores.get(detected_format, 0.0)
        target_score = weighted_scores.get(target_format, 0.0)

        other_scores = [
            score for fmt, score in weighted_scores.items() if fmt != detected_format
        ]
        second_best = max(other_scores) if other_scores else 0.0

        return {
            "detected_format": detected_format,
            "detected_score": detected_score,
            "target_score": target_score,
            "second_best": second_best,
        }

    def _calculate_confidence(
        self, score_info: Dict, format_type: SupportedFormat
    ) -> float:
        """Calculate confidence based on scoring information.

        Enhanced with adaptive temperature based on score magnitude
        to provide better discrimination across different evidence levels.
        """
        # Adaptive temperature: lower for high scores, higher for low scores
        detected_score = score_info["detected_score"]
        if detected_score >= self.HIGH_EVIDENCE_THRESHOLD:
            temperature = self.HIGH_EVIDENCE_TEMPERATURE
        elif detected_score >= self.MODERATE_EVIDENCE_THRESHOLD:
            temperature = self.MODERATE_EVIDENCE_TEMPERATURE
        else:
            temperature = self.LOW_EVIDENCE_TEMPERATURE

        if format_type == score_info["detected_format"]:
            spread = max(score_info["detected_score"] - score_info["second_best"], 0.0)
            logistic_conf = self._stable_logistic(spread / temperature)
            confidence = logistic_conf * self._evidence_scale(
                score_info["detected_score"]
            )
        else:
            best_competitor = max(
                score_info["detected_score"], score_info["second_best"]
            )
            spread = score_info["target_score"] - best_competitor
            logistic_conf = self._stable_logistic(spread / temperature)
            confidence = logistic_conf * self._evidence_scale(
                score_info["target_score"]
            )

        return confidence

    def _apply_baseline_boost(self, confidence: float, detected_score: float) -> float:
        """Apply baseline confidence boost for detected format.

        Enhanced to provide more appropriate baseline confidence for
        realistic test data scenarios while maintaining discrimination.
        """
        if detected_score >= self.HIGH_EVIDENCE_THRESHOLD:
            # Strong evidence gets high baseline
            baseline_confidence = self.HIGH_BASELINE_CONFIDENCE
        elif detected_score >= self.MODERATE_EVIDENCE_THRESHOLD:
            # Good evidence gets solid baseline
            baseline_confidence = self.MODERATE_BASELINE_CONFIDENCE
        elif detected_score >= self.BASIC_EVIDENCE_THRESHOLD:
            # Basic evidence gets moderate baseline
            baseline_confidence = self.BASIC_BASELINE_CONFIDENCE
        else:
            # Minimal evidence gets conservative baseline
            baseline_confidence = min(
                self.MINIMAL_BASELINE_CONFIDENCE,
                detected_score / self.MINIMAL_EVIDENCE_DIVISOR,
            )

        return max(confidence, baseline_confidence)

    def _apply_fallback_confidence(
        self,
        confidence: float,
        score_info: Dict,
        format_type: SupportedFormat,  # pylint: disable=unused-argument
    ) -> float:
        """Apply fallback confidence mechanism for edge cases.

        Provides reasonable confidence scores for scenarios where
        the main algorithm might be too conservative.
        """
        target_score = score_info["target_score"]
        detected_score = score_info["detected_score"]
        second_best = score_info["second_best"]

        # Fallback 1: Unique indicator with minimal competition
        if (
            target_score >= self.FALLBACK_UNIQUE_SCORE_THRESHOLD
            and detected_score == target_score
            and second_best < self.FALLBACK_UNIQUE_COMPETITION_THRESHOLD
        ):
            return max(confidence, self.FALLBACK_UNIQUE_CONFIDENCE)

        # Fallback 2: Strong indicator with good spread
        if (
            target_score >= self.FALLBACK_STRONG_SCORE_THRESHOLD
            and detected_score == target_score
            and target_score - second_best >= self.FALLBACK_STRONG_SPREAD_THRESHOLD
        ):
            return max(confidence, self.FALLBACK_STRONG_CONFIDENCE)

        # Fallback 3: Any positive score with no competition
        if target_score > 0 and detected_score == target_score and second_best == 0.0:
            return max(confidence, self.FALLBACK_MINIMAL_CONFIDENCE)

        return confidence

    @classmethod
    def _stable_logistic(cls, value: float) -> float:
        """Smooth logistic helper that avoids overflow for large spreads."""
        capped = max(min(value, cls.LOGISTIC_VALUE_MAX), cls.LOGISTIC_VALUE_MIN)
        return 1.0 / (1.0 + math.exp(-capped))

    @classmethod
    def _evidence_scale(cls, score: float) -> float:
        """Scale raw confidence by evidence magnitude so weak signals stay modest.

        Optimized to allow higher confidence scores for realistic test data.
        Uses adaptive scaling based on score magnitude to better handle
        both minimal and comprehensive test data scenarios.
        """
        if score >= cls.EVIDENCE_SCALE_HIGH_THRESHOLD:
            # High confidence for strong evidence (10+ points)
            return min(
                cls.EVIDENCE_SCALE_HIGH_MAX, score / cls.EVIDENCE_SCALE_HIGH_DIVISOR
            )
        if score >= cls.EVIDENCE_SCALE_MODERATE_THRESHOLD:
            # Good confidence for moderate evidence (7-9 points)
            return min(
                cls.EVIDENCE_SCALE_MODERATE_MAX,
                score / cls.EVIDENCE_SCALE_MODERATE_DIVISOR,
            )
        if score >= cls.EVIDENCE_SCALE_BASIC_THRESHOLD:
            # Moderate confidence for basic evidence (4-6 points)
            return min(
                cls.EVIDENCE_SCALE_BASIC_MAX, score / cls.EVIDENCE_SCALE_BASIC_DIVISOR
            )
        # Low confidence for minimal evidence (0-3 points)
        return score / cls.EVIDENCE_SCALE_MINIMAL_DIVISOR

    def calculate_bayesian_confidence(
        self, data: Dict[str, Any], target_format: SupportedFormat, data_str: str
    ) -> float:
        """Calculate advanced Bayesian confidence using pattern reasoning.

        Implements sophisticated Bayesian inference that considers:
        - Prior probabilities based on format characteristics
        - Multiple types of evidence (required fields, optional fields, structure)
        - Evidence weighting and smoothing
        - Negative evidence penalties
        - Pattern matching bonuses

        Args:
            data: Data structure to analyze
            target_format: Format to calculate confidence for
            data_str: String representation for efficient analysis

        Returns:
            Bayesian confidence score between 0.0 and 1.0
        """
        try:
            if not self._is_valid_input(data, target_format, data_str):
                return 0.0

            # Calculate prior probability for target format
            prior = self._calculate_prior_probability(target_format, data)

            # Gather evidence from multiple sources
            evidence_scores = self._gather_bayesian_evidence(
                data, target_format, data_str
            )

            # Calculate likelihood given evidence
            likelihood = self._calculate_likelihood(evidence_scores)

            # Apply Bayesian inference with normalization
            posterior = self._apply_bayesian_inference(
                prior, likelihood, data, data_str
            )

            return float(
                max(
                    self.CONFIDENCE_THRESHOLD_MIN,
                    min(self.CONFIDENCE_THRESHOLD_MAX, posterior),
                )
            )

        except Exception as e:
            logger.warning(
                "Error in Bayesian confidence calculation for %s: %s",
                target_format.value,
                e,
            )
            return 0.0

    def _calculate_prior_probability(
        self, target_format: SupportedFormat, data: Dict[str, Any]
    ) -> float:
        """Calculate prior probability for the target format.

        Based on format characteristics and data structure hints.
        """
        base_prior = self.PRIOR_PROBABILITY_BASE

        # Get format patterns for the target format
        patterns = self.format_patterns.get(target_format, {})

        # Boost prior for formats with more specific patterns
        required_keys = patterns.get("required_keys", [])
        optional_keys = patterns.get("optional_keys", [])

        if required_keys or optional_keys:
            base_prior += self.PRIOR_PROBABILITY_BOOST

        # Adjust based on data structure complexity
        if isinstance(data, dict):
            data_keys = len(data.keys())
            expected_keys = len(required_keys) + len(optional_keys)

            if expected_keys > 0:
                # Closer match in key count suggests higher prior
                key_match_ratio = min(data_keys, expected_keys) / max(
                    data_keys, expected_keys, 1
                )
                base_prior += self.PRIOR_PROBABILITY_BOOST * key_match_ratio

        return min(base_prior, 0.5)  # Cap prior at 0.5 to avoid overconfidence

    def _gather_bayesian_evidence(
        self, data: Dict[str, Any], target_format: SupportedFormat, data_str: str
    ) -> Dict[str, float]:
        """Gather weighted evidence from multiple sources."""
        evidence = {
            "required_fields": 0.0,
            "optional_fields": 0.0,
            "structural_match": 0.0,
            "negative_evidence": 0.0,
            "pattern_bonus": 0.0,
        }

        patterns = self.format_patterns.get(target_format, {})

        # Required field evidence
        required_keys = patterns.get("required_keys", [])
        for key in required_keys:
            if self._key_present_in_data(key, data, data_str):
                evidence["required_fields"] += self.EVIDENCE_WEIGHT_REQUIRED
            else:
                evidence["negative_evidence"] += self.NEGATIVE_EVIDENCE_PENALTY

        # Optional field evidence
        optional_keys = patterns.get("optional_keys", [])
        for key in optional_keys:
            if self._key_present_in_data(key, data, data_str):
                evidence["optional_fields"] += self.EVIDENCE_WEIGHT_OPTIONAL

        # Structural evidence
        evidence["structural_match"] = self._assess_structural_evidence(data, patterns)

        # Pattern matching bonus
        if self._has_format_specific_patterns(target_format, data_str):
            evidence["pattern_bonus"] = self.PATTERN_MATCH_BONUS

        return evidence

    def _calculate_likelihood(self, evidence_scores: Dict[str, float]) -> float:
        """Calculate likelihood of evidence given the target format."""
        # Sum weighted evidence with smoothing
        total_positive_evidence = (
            evidence_scores["required_fields"]
            + evidence_scores["optional_fields"]
            + evidence_scores["structural_match"]
            + evidence_scores["pattern_bonus"]
        )

        total_negative_evidence = evidence_scores["negative_evidence"]

        # Apply smoothing and normalize
        smoothed_positive = total_positive_evidence + self.BAYESIAN_SMOOTHING_FACTOR
        net_evidence = smoothed_positive - total_negative_evidence

        # Convert to likelihood using sigmoid-like function
        likelihood = net_evidence / (net_evidence + self.BAYESIAN_SMOOTHING_FACTOR * 2)

        return max(0.0, min(1.0, likelihood))

    def _apply_bayesian_inference(
        self, prior: float, likelihood: float, data: Dict[str, Any], data_str: str
    ) -> float:
        """Apply Bayesian inference to calculate posterior probability."""
        # Calculate evidence (normalization factor) across all formats
        total_evidence = 0.0

        for fmt in self.format_patterns.keys():
            fmt_prior = self._calculate_prior_probability(fmt, data)
            fmt_evidence = self._gather_bayesian_evidence(data, fmt, data_str)
            fmt_likelihood = self._calculate_likelihood(fmt_evidence)
            total_evidence += fmt_prior * fmt_likelihood

        # Apply Bayes' theorem: P(H|E) = P(E|H) * P(H) / P(E)
        if total_evidence > 0:
            posterior = (likelihood * prior) / total_evidence
        else:
            posterior = prior  # Fall back to prior if no evidence

        return posterior

    def _key_present_in_data(
        self, key: str, data: Dict[str, Any], data_str: str
    ) -> bool:
        """Check if a key is present in data using multiple strategies."""
        key_lower = key.lower()

        # Direct key presence
        if key in data or key_lower in (k.lower() for k in data.keys()):
            return True

        # String-based search (for nested structures)
        if key_lower in data_str.lower():
            return True

        return False

    def _assess_structural_evidence(
        self, data: Dict[str, Any], patterns: Dict[str, Any]
    ) -> float:
        """Assess structural match between data and expected format patterns."""
        evidence = 0.0

        # Check for expected data types and structures
        expected_structure = patterns.get("structure_hints", {})

        for field, expected_type in expected_structure.items():
            if field in data:
                actual_value = data[field]
                if self._type_matches_expectation(actual_value, expected_type):
                    evidence += self.EVIDENCE_WEIGHT_STRUCTURE

        return evidence

    def _has_format_specific_patterns(
        self, target_format: SupportedFormat, data_str: str
    ) -> bool:
        """Check for format-specific patterns in the data."""
        # Implementation can be enhanced with format-specific heuristics
        patterns = self.format_patterns.get(target_format, {})
        specific_indicators = patterns.get("specific_patterns", [])

        for pattern in specific_indicators:
            if pattern.lower() in data_str.lower():
                return True

        return False

    def _type_matches_expectation(self, value: Any, expected_type: str) -> bool:
        """Check if a value matches the expected type."""
        type_mapping: dict[str, type | tuple[type, ...]] = {
            "string": str,
            "number": (int, float),
            "list": list,
            "dict": dict,
            "boolean": bool,
        }

        expected_python_type = type_mapping.get(expected_type.lower())
        if expected_python_type:
            return isinstance(value, expected_python_type)

        return False

    def _score_calculation(self, data_str: str, patterns: Dict[str, Any]) -> int:
        """Calculate simple scoring for confidence calculation."""
        score = 0

        # Score required keys
        required_keys = patterns.get("required_keys", [])
        for key in required_keys:
            if key.lower() in data_str:
                score += self.REQUIRED_KEY_SCORE  # Strong evidence

        # Score optional keys
        optional_keys = patterns.get("optional_keys", [])
        for key in optional_keys:
            if key.lower() in data_str:
                score += self.OPTIONAL_KEY_SCORE  # Weak evidence

        return score


__all__ = ["ConfidenceCalculator"]
