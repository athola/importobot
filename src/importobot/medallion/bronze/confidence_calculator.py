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
        if detected_score >= 10.0:
            temperature = 0.5  # Sharper discrimination for strong evidence
        elif detected_score >= 7.0:
            temperature = 0.65  # Moderate discrimination for good evidence
        else:
            temperature = 0.8  # Gentler discrimination for minimal evidence

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
        if detected_score >= 10.0:
            # Strong evidence gets high baseline
            baseline_confidence = 0.90
        elif detected_score >= 7.0:
            # Good evidence gets solid baseline
            baseline_confidence = 0.80
        elif detected_score >= 4.0:
            # Basic evidence gets moderate baseline
            baseline_confidence = 0.65
        else:
            # Minimal evidence gets conservative baseline
            baseline_confidence = min(0.50, detected_score / 8.0)

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
        if target_score >= 5 and detected_score == target_score and second_best < 2.0:
            return max(confidence, 0.75)

        # Fallback 2: Strong indicator with good spread
        if (
            target_score >= 3
            and detected_score == target_score
            and target_score - second_best >= 2.0
        ):
            return max(confidence, 0.65)

        # Fallback 3: Any positive score with no competition
        if target_score > 0 and detected_score == target_score and second_best == 0.0:
            return max(confidence, 0.55)

        return confidence

    @staticmethod
    def _stable_logistic(value: float) -> float:
        """Smooth logistic helper that avoids overflow for large spreads."""
        capped = max(min(value, 50.0), -50.0)
        return 1.0 / (1.0 + math.exp(-capped))

    @staticmethod
    def _evidence_scale(score: float) -> float:
        """Scale raw confidence by evidence magnitude so weak signals stay modest.

        Optimized to allow higher confidence scores for realistic test data.
        Uses adaptive scaling based on score magnitude to better handle
        both minimal and comprehensive test data scenarios.
        """
        if score >= 10.0:
            # High confidence for strong evidence (10+ points)
            return min(0.95, score / 12.0)
        if score >= 7.0:
            # Good confidence for moderate evidence (7-9 points)
            return min(0.85, score / 10.0)
        if score >= 4.0:
            # Moderate confidence for basic evidence (4-6 points)
            return min(0.70, score / 8.0)
        # Low confidence for minimal evidence (0-3 points)
        return score / 6.0

    def calculate_bayesian_confidence(
        self, data: Dict[str, Any], target_format: SupportedFormat, data_str: str
    ) -> float:
        """Calculate simplified Bayesian confidence for backwards compatibility.

        This is a simplified version of the original complex Bayesian analysis
        to avoid performance issues while maintaining API compatibility.
        """
        try:
            # Use simplified confidence calculation
            return self.get_format_confidence(
                data, target_format, data_str, self._simple_score_calculation
            )
        except Exception as e:
            logger.warning(
                "Error in Bayesian confidence calculation for %s: %s",
                target_format.value,
                e,
            )
            return 0.0

    def _simple_score_calculation(self, data_str: str, patterns: Dict[str, Any]) -> int:
        """Calculate simple scoring for confidence calculation."""
        score = 0

        # Score required keys
        required_keys = patterns.get("required_keys", [])
        for key in required_keys:
            if key.lower() in data_str:
                score += 3  # Strong evidence

        # Score optional keys
        optional_keys = patterns.get("optional_keys", [])
        for key in optional_keys:
            if key.lower() in data_str:
                score += 1  # Weak evidence

        return score


__all__ = ["ConfidenceCalculator"]
