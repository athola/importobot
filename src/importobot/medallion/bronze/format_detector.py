"""Modular format detection facade coordinating specialized detection modules."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

from importobot.config import (
    FORMAT_DETECTION_CIRCUIT_RESET_SECONDS,
    FORMAT_DETECTION_FAILURE_THRESHOLD,
)
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.utils.logging import setup_logger
from importobot.utils.string_cache import data_to_lower_cached

from .complexity_analyzer import ComplexityAnalyzer
from .confidence_calculator import ConfidenceCalculator
from .detection_cache import DetectionCache
from .detection_metrics import PerformanceMonitor
from .evidence_accumulator import EvidenceAccumulator
from .evidence_collector import EvidenceCollector
from .evidence_evaluator import EvidenceEvaluator
from .format_registry import FormatRegistry
from .scoring_algorithms import ScoringAlgorithms, ScoringConstants
from .shared_config import PRIORITY_MULTIPLIERS

logger = setup_logger(__name__)


class FormatDetector:
    """Main facade for format detection using modular components."""

    def __init__(self) -> None:
        """Initialize the modular format detector."""
        self.format_registry = FormatRegistry()
        self.detection_cache = DetectionCache()
        self.evidence_collector = EvidenceCollector(self.format_registry)
        self.confidence_calculator = ConfidenceCalculator(
            self.evidence_collector.get_all_patterns()
        )
        self.evidence_accumulator = EvidenceAccumulator()

        self._cache_lock = threading.Lock()
        self._circuit_lock = threading.Lock()
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

        logger.info(
            "Initialized modular FormatDetector with %d formats",
            len(self.format_registry.get_all_formats()),
        )

    def detect_format(self, data: Dict[str, Any]) -> SupportedFormat:
        """Detect the format type of the provided test data."""
        start_time = time.perf_counter()
        result = SupportedFormat.UNKNOWN
        data_size_estimate = len(str(data)) if data else 0

        with PerformanceMonitor(data_size_estimate) as monitor:
            cached_result = self.detection_cache.get_cached_detection_result(data)
            if cached_result is not None:
                self._reset_circuit_after_success()
                self.detection_cache.enforce_min_detection_time(start_time, data)
                monitor.record_detection(
                    cached_result,
                    1.0,
                    fast_path_used=True,
                )
                return cached_result

            if self._is_circuit_open():
                logger.warning(
                    "Format detection circuit breaker is open; "
                    "using fallback detection."
                )
                fallback_result = self._fallback_detection(data)
                self.detection_cache.enforce_min_detection_time(start_time, data)
                confidence = (
                    self.get_format_confidence(data, fallback_result)
                    if fallback_result != SupportedFormat.UNKNOWN
                    else 0.0
                )
                monitor.record_detection(fallback_result, confidence)
                return fallback_result

            if not isinstance(data, dict) or not data:
                if not isinstance(data, dict):
                    logger.warning("Data is not a dictionary, cannot detect format")
                self._reset_circuit_after_success()
                self.detection_cache.enforce_min_detection_time(start_time, data)
                monitor.record_detection(result, 0.0)
                return result

            try:
                complexity_info = ComplexityAnalyzer.assess_data_complexity(data)
                if complexity_info["too_complex"]:
                    logger.warning(
                        "Data complexity exceeds algorithm limits: %s. "
                        "Using simplified detection algorithm. %s",
                        complexity_info["reason"],
                        complexity_info["recommendation"],
                    )
                    result = self._quick_format_detection(data)
                    self.detection_cache.cache_detection_result(data, result)
                    self.detection_cache.enforce_min_detection_time(start_time, data)
                    monitor.record_detection(
                        result,
                        self.get_format_confidence(data, result),
                        complexity_assessment=complexity_info,
                    )
                    self._reset_circuit_after_success()
                    return result

                fast_path_result = self._fast_path_if_strong_indicators(data)
                if fast_path_result != SupportedFormat.UNKNOWN:
                    result = fast_path_result
                    fast_path_used = True
                else:
                    result = self._full_format_detection(data)
                    fast_path_used = False

                self.detection_cache.cache_detection_result(data, result)
                self.detection_cache.enforce_min_detection_time(start_time, data)

                monitor.record_detection(
                    result,
                    self.get_format_confidence(data, result),
                    fast_path_used=fast_path_used,
                    complexity_assessment=complexity_info,
                )
                self._reset_circuit_after_success()
                return result
            except Exception:  # pragma: no cover - defensive circuit breaker guard
                logger.exception("Format detection pipeline failed unexpectedly.")
                self._note_detection_failure()
                self.detection_cache.enforce_min_detection_time(start_time, data)
                monitor.record_detection(SupportedFormat.UNKNOWN, 0.0)
                return SupportedFormat.UNKNOWN

    def _quick_format_detection(self, data: Dict[str, Any]) -> SupportedFormat:
        """Quickly compare format candidates using Bayesian relative scoring."""
        data_str = self.detection_cache.get_data_string_efficient(data)
        format_patterns = self.evidence_collector.get_all_patterns()

        best_score = float("-inf")
        second_best_score = float("-inf")
        best_format = SupportedFormat.UNKNOWN

        for format_type, patterns in format_patterns.items():
            score = ScoringAlgorithms.calculate_format_score(data_str, patterns, data)
            weighted_score = score * PRIORITY_MULTIPLIERS.get(format_type, 1.0)

            if weighted_score > best_score:
                second_best_score = best_score
                best_score = weighted_score
                best_format = format_type
            elif weighted_score > second_best_score:
                second_best_score = weighted_score

        confidence_gap = best_score - second_best_score
        has_positive_evidence = best_score > 0
        has_clear_separation = confidence_gap >= 1

        if has_positive_evidence or (
            has_clear_separation and best_score > float("-inf")
        ):
            return best_format
        return SupportedFormat.UNKNOWN

    def _fast_path_if_strong_indicators(self, data: Dict[str, Any]) -> SupportedFormat:
        """Check for strong format indicators for fast detection."""
        strong_indicators = {
            SupportedFormat.JIRA_XRAY: ["testExecutions", "testInfo", "evidences"],
            SupportedFormat.ZEPHYR: ["testCase", "execution", "cycle"],
            SupportedFormat.TESTRAIL: ["suite_id", "project_id", "milestone_id"],
            SupportedFormat.TESTLINK: ["testsuites", "testsuite"],
        }

        top_level_field_names = set(data.keys()) if isinstance(data, dict) else set()
        for format_type, indicators in strong_indicators.items():
            matches = sum(
                1 for indicator in indicators if indicator in top_level_field_names
            )
            if matches >= ScoringConstants.MIN_STRONG_INDICATORS_THRESHOLD:
                return format_type

        return SupportedFormat.UNKNOWN

    def _full_format_detection(self, data: Dict[str, Any]) -> SupportedFormat:
        """Full format detection algorithm."""
        data_str = self.detection_cache.get_data_string_efficient(data)
        format_patterns = self.evidence_collector.get_all_patterns()

        scores: Dict[SupportedFormat, float] = {}
        for format_type, patterns in format_patterns.items():
            score = ScoringAlgorithms.calculate_format_score(data_str, patterns, data)
            scores[format_type] = score * PRIORITY_MULTIPLIERS.get(format_type, 1.0)

        best_format = max(scores.keys(), key=lambda k: scores[k])
        best_score = scores[best_format]

        if not EvidenceEvaluator.is_sufficient_for_detection(int(best_score)):
            return SupportedFormat.UNKNOWN

        return best_format

    def _fallback_detection(self, data: Dict[str, Any]) -> SupportedFormat:
        """Fallback detection used while the circuit breaker is open."""
        if not isinstance(data, dict) or not data:
            return SupportedFormat.UNKNOWN
        try:
            return self._quick_format_detection(data)
        except Exception:  # pragma: no cover - fallback should be lightweight
            logger.debug("Fallback detection failed; returning UNKNOWN.", exc_info=True)
            return SupportedFormat.UNKNOWN

    def _note_detection_failure(self) -> None:
        """Track consecutive failures and trip the circuit breaker if needed."""
        with self._circuit_lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= FORMAT_DETECTION_FAILURE_THRESHOLD:
                self._circuit_open_until = (
                    time.time() + FORMAT_DETECTION_CIRCUIT_RESET_SECONDS
                )
                logger.error(
                    "Format detection circuit breaker opened for %d seconds "
                    "after %d consecutive failures.",
                    FORMAT_DETECTION_CIRCUIT_RESET_SECONDS,
                    self._consecutive_failures,
                )

    def _reset_circuit_after_success(self) -> None:
        """Clear failure counters after a successful detection."""
        with self._circuit_lock:
            if self._consecutive_failures or self._circuit_open_until:
                self._consecutive_failures = 0
                self._circuit_open_until = 0.0

    def _is_circuit_open(self) -> bool:
        """Return True if the circuit breaker is currently open."""
        with self._circuit_lock:
            if self._circuit_open_until == 0.0:
                return False
            if time.time() >= self._circuit_open_until:
                self._consecutive_failures = 0
                self._circuit_open_until = 0.0
                return False
            return True

    def get_format_confidence(
        self, data: Dict[str, Any], format_type: SupportedFormat
    ) -> float:
        """Return confidence estimate for a specific format with Bayesian correction."""
        if not isinstance(data, dict):
            return 0.0

        data_str = self.detection_cache.get_data_string_efficient(data)
        data_str_lower = data_to_lower_cached(data_str)

        base_confidence = self.confidence_calculator.get_format_confidence(
            data, format_type, data_str, ScoringAlgorithms.calculate_format_score
        )

        patterns = self.evidence_collector.get_patterns(format_type)
        required_keys = patterns.get("required_keys", [])

        if required_keys:
            if format_type == SupportedFormat.GENERIC:
                generic_alternatives = ["tests", "test_cases", "testcases"]
                has_any_alternative = any(
                    alt.lower() in data_str_lower for alt in generic_alternatives
                )
                return (
                    base_confidence if has_any_alternative else base_confidence * 0.01
                )

            matches = sum(1 for key in required_keys if key.lower() in data_str_lower)
            total_required = len(required_keys)
            required_ratio = matches / total_required

            if required_ratio == 0:
                bayesian_multiplier = 0.01
            else:
                bayesian_multiplier = required_ratio**1.5
            return base_confidence * bayesian_multiplier

        return base_confidence

    def get_supported_formats(self) -> List[SupportedFormat]:
        """Get list of supported format types."""
        return list(self.format_registry.get_all_formats().keys())

    def get_format_evidence(
        self, data: Dict[str, Any], format_type: SupportedFormat
    ) -> Dict[str, Any]:
        """Get detailed evidence for format detection."""
        if not isinstance(data, dict):
            return {"evidence": [], "total_weight": 0}

        evidence_items, total_weight = self.evidence_collector.collect_evidence(
            data, format_type
        )

        return {
            "evidence": [
                {
                    "type": item.source,
                    "description": item.details,
                    "weight": item.weight,
                    "confidence": item.confidence,
                }
                for item in evidence_items
            ],
            "total_weight": total_weight,
        }


__all__ = ["FormatDetector"]
