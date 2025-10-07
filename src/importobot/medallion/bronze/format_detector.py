"""Modular format detection facade coordinating specialized detection modules."""

from __future__ import annotations

import re
import threading
import time
from typing import Any, Dict, List

from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.utils.logging import setup_logger
from importobot.utils.regex_cache import get_compiled_pattern
from importobot.utils.string_cache import data_to_lower_cached

from .complexity_analyzer import ComplexityAnalyzer
from .confidence_calculator import ConfidenceCalculator
from .context_searcher import ContextSearcher
from .detection_cache import DetectionCache
from .detection_metrics import PerformanceMonitor
from .evidence_accumulator import EvidenceAccumulator, EvidenceItem
from .evidence_evaluator import EvidenceEvaluator
from .format_registry import FormatRegistry
from .scoring_algorithms import ScoringAlgorithms, ScoringConstants
from .shared_config import PRIORITY_MULTIPLIERS

logger = setup_logger(__name__)


class FormatDetector:
    """Main facade for format detection using modular components."""

    # Priority multipliers for different formats
    # Using shared configuration to avoid duplication

    def __init__(self) -> None:
        """Initialize the modular format detector."""
        # Initialize core components
        self.format_registry = FormatRegistry()
        self.detection_cache = DetectionCache()
        self.confidence_calculator = ConfidenceCalculator(self._build_format_patterns())
        self.evidence_accumulator = EvidenceAccumulator()

        # Thread safety
        self._cache_lock = threading.Lock()

        logger.info(
            "Initialized modular FormatDetector with %d formats",
            len(self.format_registry.get_all_formats()),
        )

    def _build_format_patterns(self) -> Dict[SupportedFormat, Dict[str, Any]]:
        """Build format patterns from registered formats."""
        patterns = {}
        for format_type, format_def in self.format_registry.get_all_formats().items():
            all_fields = format_def.get_all_fields()
            patterns[format_type] = {
                "required_keys": [
                    field.name
                    for field in (
                        format_def.unique_indicators + format_def.strong_indicators
                    )
                ],
                "optional_keys": [
                    field.name
                    for field in (
                        format_def.moderate_indicators + format_def.weak_indicators
                    )
                ],
                "structure_indicators": [
                    field.name
                    for field in (
                        format_def.strong_indicators + format_def.moderate_indicators
                    )
                ],
                "field_patterns": {
                    field.name: field.pattern for field in all_fields if field.pattern
                },
            }
        return patterns

    def detect_format(self, data: Dict[str, Any]) -> SupportedFormat:
        """Detect the format type of the provided test data.

        Args:
            data: The test data to analyze

        Returns:
            The detected format type
        """
        start_time = time.perf_counter()
        result = SupportedFormat.UNKNOWN

        # Estimate data size for performance correlation
        data_size_estimate = len(str(data)) if data else 0

        with PerformanceMonitor(data_size_estimate) as monitor:
            # Check cache first
            cached_result = self.detection_cache.get_cached_detection_result(data)
            if cached_result is not None:
                self.detection_cache.enforce_min_detection_time(start_time, data)
                # Record cached result metrics
                monitor.record_detection(
                    cached_result,
                    1.0,  # Cached results have full confidence
                    fast_path_used=True,
                )
                return cached_result

            if not isinstance(data, dict):
                logger.warning("Data is not a dictionary, cannot detect format")
                self.detection_cache.enforce_min_detection_time(start_time, data)
                monitor.record_detection(result, 0.0)
                return result

            if not data:
                self.detection_cache.enforce_min_detection_time(start_time, data)
                monitor.record_detection(result, 0.0)
                return result

            # Check data complexity - use simplified detection for complex data
            complexity_info = ComplexityAnalyzer.assess_data_complexity(data)
            if complexity_info["too_complex"]:
                logger.warning(
                    "Data complexity exceeds algorithm limits: %s. "
                    "Using simplified detection algorithm. %s",
                    complexity_info["reason"],
                    complexity_info["recommendation"],
                )
                # Use simplified scoring directly
                result = self._quick_format_detection(data)
                self.detection_cache.cache_detection_result(data, result)
                self.detection_cache.enforce_min_detection_time(start_time, data)
                monitor.record_detection(
                    result,
                    self.get_format_confidence(data, result),
                    complexity_assessment=complexity_info,
                )
                return result

            # Check for fast path using strong indicators
            fast_path_result = self._fast_path_if_strong_indicators(data)
            if fast_path_result != SupportedFormat.UNKNOWN:
                result = fast_path_result
                fast_path_used = True
            else:
                # Full detection algorithm
                result = self._full_format_detection(data)
                fast_path_used = False

            # Cache and return result
            self.detection_cache.cache_detection_result(data, result)
            self.detection_cache.enforce_min_detection_time(start_time, data)

            # Record final metrics
            monitor.record_detection(
                result,
                self.get_format_confidence(data, result),
                fast_path_used=fast_path_used,
                complexity_assessment=complexity_info,
            )
            return result

    def _quick_format_detection(self, data: Dict[str, Any]) -> SupportedFormat:
        """Quickly compare format candidates using Bayesian relative scoring.

        Notes:
            The Bayesian penalty model can drive every individual score below
            zero for noisy inputs. Initializing the running maximum to
            ``-inf`` ensures that we still track the highest *relative* score,
            while the final guard below returns ``UNKNOWN`` unless we saw either
            positive evidence or a clear separation between candidates.
        """
        data_str = self.detection_cache.get_data_string_efficient(data)
        format_patterns = self._build_format_patterns()

        # Allow negative scores so we can still spot the best relative candidate.
        best_score = float("-inf")
        second_best_score = float("-inf")
        best_format = SupportedFormat.UNKNOWN

        for format_type, patterns in format_patterns.items():
            score = ScoringAlgorithms.calculate_format_score(data_str, patterns, data)
            multiplier = PRIORITY_MULTIPLIERS.get(format_type, 1.0)
            weighted_score = score * multiplier

            if weighted_score > best_score:
                second_best_score = best_score
                best_score = weighted_score
                best_format = format_type
            elif weighted_score > second_best_score:
                second_best_score = weighted_score

        # Bayesian decision: require meaningful separation between top candidates
        # and at least one positive evidence (score > 0) or clear winner
        confidence_gap = best_score - second_best_score
        has_positive_evidence = best_score > 0
        has_clear_separation = confidence_gap >= 1  # At least 1 point difference

        if has_positive_evidence or (
            has_clear_separation and best_score > float("-inf")
        ):
            return best_format
        return SupportedFormat.UNKNOWN

    def _fast_path_if_strong_indicators(self, data: Dict[str, Any]) -> SupportedFormat:
        """Check for strong format indicators for fast detection."""
        # Strong indicators for each format - check for actual field names
        strong_indicators = {
            SupportedFormat.JIRA_XRAY: ["testExecutions", "testInfo", "evidences"],
            SupportedFormat.ZEPHYR: ["testCase", "execution", "cycle"],
            SupportedFormat.TESTRAIL: ["suite_id", "project_id", "milestone_id"],
            SupportedFormat.TESTLINK: ["testsuites", "testsuite"],
        }

        for format_type, indicators in strong_indicators.items():
            # Check for TOP-LEVEL field names only to avoid false positives
            # from nested structures
            top_level_field_names = (
                set(data.keys()) if isinstance(data, dict) else set()
            )
            matches = sum(
                1 for indicator in indicators if indicator in top_level_field_names
            )
            if matches >= ScoringConstants.MIN_STRONG_INDICATORS_THRESHOLD:
                return format_type

        return SupportedFormat.UNKNOWN

    def _full_format_detection(self, data: Dict[str, Any]) -> SupportedFormat:
        """Full format detection algorithm."""
        data_str = self.detection_cache.get_data_string_efficient(data)
        format_patterns = self._build_format_patterns()

        scores = {}
        for format_type, patterns in format_patterns.items():
            score = ScoringAlgorithms.calculate_format_score(data_str, patterns, data)
            multiplier = PRIORITY_MULTIPLIERS.get(format_type, 1.0)
            scores[format_type] = score * multiplier

        # Find the highest scoring format
        best_format = max(scores.keys(), key=lambda k: scores[k])
        best_score = scores[best_format]

        # Apply evidence evaluation
        if not EvidenceEvaluator.is_sufficient_for_detection(int(best_score)):
            return SupportedFormat.UNKNOWN

        return best_format

    def get_format_confidence(
        self, data: Dict[str, Any], format_type: SupportedFormat
    ) -> float:
        """
        Return confidence estimate for a specific format with Bayesian correction.

        Mathematical foundation:
        Applies Bayesian reasoning where missing required keys significantly
        reduce confidence regardless of other positive evidence.

        Args:
            data: Data sample to analyse
            format_type: Target format to compute confidence for

        Returns:
            A float between 0.0 and 1.0 representing confidence
        """
        if not isinstance(data, dict):
            return 0.0

        data_str = self.detection_cache.get_data_string_efficient(data)
        data_str_lower = data_to_lower_cached(data_str)

        base_confidence = self.confidence_calculator.get_format_confidence(
            data, format_type, data_str, ScoringAlgorithms.calculate_format_score
        )

        # Bayesian correction: apply penalty for missing required keys
        # This ensures mathematical consistency across all data sizes
        patterns = self._build_format_patterns().get(format_type, {})
        required_keys = patterns.get("required_keys", [])

        if required_keys:  # Only apply to formats with required keys
            # Special handling for GENERIC format - treat strong indicators as
            # alternatives
            if format_type == SupportedFormat.GENERIC:
                # For GENERIC, we want at least one of the strong indicators
                # to be present
                # The strong indicators are: 'tests', 'test_cases',
                # 'testcases'
                generic_alternatives = ["tests", "test_cases", "testcases"]
                has_any_alternative = any(
                    alt.lower() in data_str_lower for alt in generic_alternatives
                )

                if has_any_alternative:
                    # If at least one alternative is present, no penalty
                    return base_confidence
                # If none of the alternatives are present, apply heavy penalty
                return base_confidence * 0.01
            # For other formats, use the original logic
            matches = sum(1 for key in required_keys if key.lower() in data_str_lower)
            total_required = len(required_keys)
            required_ratio = matches / total_required

            # Bayesian penalty: confidence should decay exponentially with
            # missing required keys
            # This reflects the multiplicative nature of independent
            # evidence in Bayesian analysis
            # More aggressive penalty for formats missing most/all required keys
            if required_ratio == 0:
                # Missing ALL required keys should result in very low confidence
                bayesian_multiplier = 0.01  # 1% of base confidence
            else:
                # Exponential decay based on missing required keys
                bayesian_multiplier = (
                    required_ratio**1.5
                )  # Stronger penalty than square root
            corrected_confidence = base_confidence * bayesian_multiplier

            return corrected_confidence

        return base_confidence

    def get_supported_formats(self) -> List[SupportedFormat]:
        """Get list of supported format types."""
        return list(self.format_registry.get_all_formats().keys())

    def get_format_evidence(
        self, data: Dict[str, Any], format_type: SupportedFormat
    ) -> Dict[str, Any]:
        """Get detailed evidence for format detection."""
        if (
            not isinstance(data, dict)
            or format_type not in self._build_format_patterns()
        ):
            return {"evidence": [], "total_weight": 0}

        data_str = self.detection_cache.get_data_string_efficient(data)
        patterns = self._build_format_patterns()[format_type]
        data_str_lower = data_to_lower_cached(data_str)

        evidence_items = []

        # Collect evidence from different sources
        evidence_items.extend(
            self._collect_required_keys_evidence(data_str_lower, patterns)
        )
        evidence_items.extend(
            self._collect_optional_keys_evidence(data_str_lower, patterns)
        )
        evidence_items.extend(
            self._collect_structure_indicators_evidence(data_str_lower, patterns)
        )
        evidence_items.extend(
            self._collect_field_patterns_evidence(data_str, data_str_lower, patterns)
        )

        total_weight = sum(item.weight for item in evidence_items)

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

    def _collect_required_keys_evidence(
        self, data_str_lower: str, patterns: Dict[str, Any]
    ) -> List[EvidenceItem]:
        """Collect evidence from required keys."""
        evidence = []
        required_keys = patterns.get("required_keys", [])

        for key in required_keys:
            if key.lower() in data_str_lower:
                weight, confidence = ContextSearcher.get_evidence_weight_for_key(
                    key, "required"
                )
                evidence.append(
                    EvidenceItem(
                        source="required_key",
                        weight=weight,
                        confidence=confidence,
                        details=f"Required key '{key}' found",
                    )
                )

        return evidence

    def _collect_optional_keys_evidence(
        self, data_str_lower: str, patterns: Dict[str, Any]
    ) -> List[EvidenceItem]:
        """Collect evidence from optional keys."""
        evidence = []
        optional_keys = patterns.get("optional_keys", [])

        for key in optional_keys:
            if key.lower() in data_str_lower:
                weight, confidence = ContextSearcher.get_evidence_weight_for_key(
                    key, "optional"
                )
                evidence.append(
                    EvidenceItem(
                        source="optional_key",
                        weight=weight,
                        confidence=confidence,
                        details=f"Optional key '{key}' found",
                    )
                )

        return evidence

    def _collect_structure_indicators_evidence(
        self, data_str_lower: str, patterns: Dict[str, Any]
    ) -> List[EvidenceItem]:
        """Collect evidence from structure indicators."""
        evidence = []
        structure_indicators = patterns.get("structure_indicators", [])

        for indicator in structure_indicators:
            if indicator.lower() in data_str_lower:
                weight, confidence = ContextSearcher.get_evidence_weight_for_key(
                    indicator, "structure"
                )
                evidence.append(
                    EvidenceItem(
                        source="structure_indicator",
                        weight=weight,
                        confidence=confidence,
                        details=f"Structure indicator '{indicator}' found",
                    )
                )

        return evidence

    def _get_compiled_regex(self, pattern: str) -> re.Pattern[str]:
        """Get compiled regex with caching for performance optimization.

        Args:
            pattern: Regular expression pattern string

        Returns:
            Compiled regex pattern with IGNORECASE flag

        Raises:
            re.error: If pattern compilation fails
        """
        return get_compiled_pattern(pattern, re.IGNORECASE)

    def _collect_field_patterns_evidence(
        self, data_str: str, data_str_lower: str, patterns: Dict[str, Any]
    ) -> List[EvidenceItem]:
        """Collect evidence from field patterns."""
        evidence = []
        field_patterns = patterns.get("field_patterns", {})

        for field_name, pattern in field_patterns.items():
            if field_name.lower() in data_str_lower and pattern:
                try:
                    # Use cached compiled regex for performance
                    compiled_pattern = self._get_compiled_regex(pattern)
                    if compiled_pattern.search(data_str):
                        weight, confidence = (
                            ContextSearcher.get_evidence_weight_for_key(
                                field_name, "pattern"
                            )
                        )
                        evidence.append(
                            EvidenceItem(
                                source="field_pattern",
                                weight=weight,
                                confidence=confidence,
                                details=f"Field pattern '{field_name}' matched",
                            )
                        )
                except re.error:
                    # Invalid regex pattern, skip
                    continue

        return evidence


__all__ = ["FormatDetector"]
