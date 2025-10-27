"""Modular format detection facade coordinating specialized detection modules."""

from __future__ import annotations

import threading
import time
from typing import Any

from importobot.config import (
    FORMAT_DETECTION_CIRCUIT_RESET_SECONDS,
    FORMAT_DETECTION_FAILURE_THRESHOLD,
)
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.utils.logging import get_logger

from .complexity_analyzer import ComplexityAnalyzer
from .detection_cache import DetectionCache
from .detection_metrics import PerformanceMonitor
from .evidence_accumulator import EvidenceAccumulator
from .evidence_collector import EvidenceCollector
from .format_registry import FormatRegistry
from .hierarchical_classifier import HierarchicalClassifier
from .scoring_algorithms import ScoringAlgorithms, ScoringConstants
from .shared_config import PRIORITY_MULTIPLIERS

logger = get_logger()


class FormatDetector:
    """Main facade for format detection using modular components."""

    def __init__(self, *, cache: DetectionCache | None = None) -> None:
        """Initialize modular format detector with Bayesian evidence accumulation."""
        self.format_registry = FormatRegistry()
        self.detection_cache = cache or DetectionCache()
        self.evidence_collector = EvidenceCollector(self.format_registry)
        self.evidence_accumulator = EvidenceAccumulator()
        self.hierarchical_classifier = HierarchicalClassifier(
            self.format_registry,
            self.evidence_collector,
            self.evidence_accumulator,
        )

        self._cache_lock = threading.Lock()
        self._circuit_lock = threading.Lock()
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0
        self._stage1_warning_emitted = False

        logger.debug(
            "Initialized modular FormatDetector with %d formats",
            len(self.format_registry.get_all_formats()),
        )

    def detect_format(self, data: dict[str, Any]) -> SupportedFormat:
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

            # Circuit breaker removed - fail fast instead of defaulting
            if self._is_circuit_open():
                logger.error(
                    "Format detection circuit breaker is open; returning UNKNOWN."
                )
                self.detection_cache.enforce_min_detection_time(start_time, data)
                monitor.record_detection(SupportedFormat.UNKNOWN, 0.0)
                return SupportedFormat.UNKNOWN

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

    def _quick_format_detection(self, data: dict[str, Any]) -> SupportedFormat:
        """Quickly compare format candidates using Bayesian relative scoring."""
        # First, check for strong format indicators (same as fast path)
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

        # Fall back to pattern-based scoring
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

    def _fast_path_if_strong_indicators(self, data: dict[str, Any]) -> SupportedFormat:
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

    def _full_format_detection(self, data: dict[str, Any]) -> SupportedFormat:
        """Full format detection algorithm using hierarchical classifier."""
        # Use hierarchical classifier for proper two-stage detection
        result = self.hierarchical_classifier.classify(data)

        # If Stage 1 failed (not test data), return UNKNOWN
        if not result.is_test_data:
            return SupportedFormat.UNKNOWN

        # Get format with highest posterior probability
        if not result.format_posteriors:
            return SupportedFormat.UNKNOWN

        best_format_name = max(result.format_posteriors.items(), key=lambda x: x[1])[0]
        best_confidence = result.format_posteriors[best_format_name]

        # Minimum confidence threshold for detection
        min_detection_confidence = 0.3  # Business requirement for valid detection
        if best_confidence < min_detection_confidence:
            return SupportedFormat.UNKNOWN

        # Convert format name to enum
        try:
            return SupportedFormat[best_format_name]
        except KeyError:
            logger.warning("Unknown format name from classifier: %s", best_format_name)
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
        self, data: dict[str, Any], format_type: SupportedFormat
    ) -> float:
        """Return confidence estimate using proper multi-class Bayesian normalization.

        This method implements mathematically correct multi-class classification:
        1. Evaluates evidence against ALL format hypotheses
        2. Calculates likelihoods P(E|H_i) for each format
        3. Applies proper Bayesian normalization:
           P(H_i|E) = P(E|H_i)*P(H_i) / Σ_j[P(E|H_j)*P(H_j)]

        This prevents overconfident wrong-format matches by considering that evidence
        might better match a different format.
        """
        if not isinstance(data, dict):
            return 0.0

        # Evaluate evidence against ALL formats to get proper normalization
        all_confidences = self.get_all_format_confidences(data)

        # Return the confidence for the requested format
        return all_confidences.get(format_type.name, 0.0)

    def get_all_format_confidences(self, data: dict[str, Any]) -> dict[str, float]:
        """Calculate properly normalized confidence scores for ALL formats.

        Uses two-stage hierarchical Bayesian classification:
        1. Stage 1: Validate input represents test management data
        2. Stage 2: Discriminate between specific test formats

        Returns:
            Dictionary mapping format names to their normalized posterior probabilities
        """
        if not isinstance(data, dict):
            return {fmt.name: 0.0 for fmt in self.format_registry.get_all_formats()}

        # Always use hierarchical classification
        result = self.hierarchical_classifier.classify(data)

        # If Stage 1 failed (not test data), return all zeros
        if not result.is_test_data:
            if not self._stage1_warning_emitted:
                logger.warning(
                    "Hierarchical Stage 1 FAILED: Input not recognized as test data "
                    "(confidence=%.3f)",
                    result.test_data_confidence,
                )
                # TODO(post-conversion-log): funnel repeated detection warnings into
                # the upcoming aggregation endpoint instead of console spam.
                self._stage1_warning_emitted = True
            else:
                logger.debug(
                    "Stage 1 failed (confidence=%.3f); suppressing repeat warning",
                    result.test_data_confidence,
                )
            return {fmt.name: 0.0 for fmt in self.format_registry.get_all_formats()}

        # Return Stage 2 posteriors
        return result.format_posteriors

    def get_supported_formats(self) -> list[SupportedFormat]:
        """Get list of supported format types."""
        return list(self.format_registry.get_all_formats().keys())

    def get_format_evidence(
        self, data: dict[str, Any], format_type: SupportedFormat
    ) -> dict[str, Any]:
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


__all__ = ["FormatDetector", "FormatRegistry"]
