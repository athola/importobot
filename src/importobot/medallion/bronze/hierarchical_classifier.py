"""Hierarchical Bayesian classification for multi-stage format detection.

This module implements a two-stage Bayesian classification approach:

Stage 1 (Tier 1): Test Data Validation Gate
    - Determines if input represents ANY test management format vs random/invalid data
    - Uses completeness and structural quality metrics
    - Mathematical gate: P(is_test_data|E) >= threshold

Stage 2 (Tier 2): Format-Specific Discrimination
    - Only executes if Stage 1 passes
    - Uses format-specific UNIQUE indicators to discriminate between specific formats
    - Applies multi-class Bayesian normalization: P(H_i|E, is_test_data)

This tiered approach prevents incorrect high-confidence classification of non-test data
while maintaining discriminative power for distinguishing between actual test formats.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from importobot.utils.logging import get_logger

from ..interfaces.enums import EvidenceSource
from .evidence_accumulator import EvidenceAccumulator, EvidenceItem
from .evidence_collector import EvidenceCollector
from .format_models import EvidenceWeight
from .format_registry import FormatRegistry

logger = get_logger()


@dataclass
class HierarchicalClassificationResult:
    """Result from hierarchical classification including both stages."""

    # Stage 1: Test data validation
    is_test_data: bool
    test_data_confidence: float
    test_data_evidence: dict[str, Any]

    # Stage 2: Format-specific discrimination (only if Stage 1 passes)
    format_posteriors: dict[str, float]  # P(format|E, is_test_data)
    format_likelihoods: dict[str, float]  # P(E|format) for analysis

    @property
    def best_format(self) -> str | None:
        """Return format with highest posterior, or None if no test data."""
        if not self.is_test_data or not self.format_posteriors:
            return None
        return max(self.format_posteriors.items(), key=lambda x: x[1])[0]

    @property
    def best_format_confidence(self) -> float:
        """Return confidence of best format, or 0.0 if no test data."""
        if not self.is_test_data or not self.format_posteriors:
            return 0.0
        return max(self.format_posteriors.values())


class HierarchicalClassifier:
    """Two-stage hierarchical Bayesian classifier for format detection.

    This classifier implements a hierarchical approach:
    1. First validates that input represents test management data
    2. Then discriminates between specific test management formats

    This prevents the system from confidently classifying random data as a
    specific format while maintaining discrimination between actual formats.

    Fast paths are integrated at both stages while maintaining mathematical rigor:
    - Stage 1 fast path: Check for strong test data indicators
    - Stage 2 fast path: Check for unique format-specific field combinations
    """

    # Stage 1 thresholds
    MIN_TEST_DATA_CONFIDENCE = 0.50  # Minimum P(is_test_data|E) to proceed to Stage 2
    FAST_PATH_TEST_DATA_INDICATORS = 3  # Number of indicators for Stage 1 fast pass

    # Stage 2 requirements
    MIN_DISCRIMINATIVE_RATIO = 2.0  # P(correct|E) / P(wrong|E) >= 2.0 for confidence
    FAST_PATH_UNIQUE_INDICATORS = 2  # Number of UNIQUE indicators for Stage 2 fast pass

    # Format-specific unique field combinations (for Stage 2 fast path)
    FORMAT_UNIQUE_COMBINATIONS: ClassVar[dict[str, list[set[str]]]] = {
        "ZEPHYR": [{"testCase", "execution", "cycle"}],
        "JIRA_XRAY": [{"testExecutions", "xrayInfo"}, {"issues", "testInfo"}],
        "TESTLINK": [{"testsuites", "testsuite"}],
        "TESTRAIL": [{"suite_id", "project_id"}],
    }

    # Test data validation indicators (generic across all test formats)
    TEST_DATA_INDICATORS: ClassVar[list[str]] = [
        # Test identification fields (common to all formats)
        "test",
        "testcase",
        "testCase",
        "test_case",
        "suite",
        "testsuite",
        # Execution/result fields (common to all formats)
        "status",
        "result",
        "execution",
        "run",
        "pass",
        "fail",
        # Metadata fields (common to all formats)
        "priority",
        "description",
        "steps",
        "expected",
        "actual",
        # Project/organization fields (common to all formats)
        "project",
        "version",
        "cycle",
        "sprint",
        "milestone",
    ]

    def __init__(
        self,
        format_registry: FormatRegistry,
        evidence_collector: EvidenceCollector,
        evidence_accumulator: EvidenceAccumulator,
    ):
        """Initialize hierarchical classifier with existing components."""
        self.format_registry = format_registry
        self.evidence_collector = evidence_collector
        self.evidence_accumulator = evidence_accumulator
        self._stage1_indicator_tokens = self._build_stage1_indicator_tokens()
        self._stage1_notice_emitted = False

    def classify(self, data: dict[str, Any]) -> HierarchicalClassificationResult:
        """Perform two-stage hierarchical classification with fast paths.

        Stage 1: Validate input represents test management data
        Stage 2: Discriminate between specific test formats (if Stage 1 passes)

        Fast paths maintain mathematical rigor by only short-circuiting when
        evidence is strong.

        Args:
            data: Input data to classify

        Returns:
            HierarchicalClassificationResult with both stage results
        """
        # Stage 1 Fast Path: Check for strong test data indicators
        all_keys = self._extract_all_keys(data)
        all_key_tokens = self._collect_key_tokens(all_keys)
        # Only process string keys - non-string keys indicate invalid test data
        all_keys_lower = {k.lower() for k in all_keys if isinstance(k, str)}

        fast_pass_stage1 = self._check_stage1_fast_path(all_key_tokens)
        if fast_pass_stage1:
            logger.debug("Stage 1 FAST PATH: Strong test data indicators detected")
            test_confidence = 1.0
            test_evidence = {"fast_path": True, "strong_indicators": True}
            is_test_data = True
        else:
            # Stage 1: Full test data validation
            is_test_data, test_confidence, test_evidence = (
                self._stage1_validate_test_data(data)
            )

        if not is_test_data:
            if not self._stage1_notice_emitted:
                logger.info(
                    "Stage 1 FAILED: Input does not appear to be test data "
                    "(confidence=%.3f < %s)",
                    test_confidence,
                    self.MIN_TEST_DATA_CONFIDENCE,
                )
                # TODO(post-conversion-log): consolidate repeated classifier noise into
                # the dedicated log stream being planned for ingestion summaries.
                self._stage1_notice_emitted = True
            else:
                logger.debug(
                    "Stage 1 failed (confidence=%.3f); suppressing duplicate notice",
                    test_confidence,
                )
            return HierarchicalClassificationResult(
                is_test_data=False,
                test_data_confidence=test_confidence,
                test_data_evidence=test_evidence,
                format_posteriors={},
                format_likelihoods={},
            )

        logger.debug(
            "Stage 1 PASSED: Validated as test data (confidence=%.3f)", test_confidence
        )

        # Stage 2 Fast Path: Check for unique format-specific combinations
        fast_format = self._check_stage2_fast_path(all_keys_lower)
        if fast_format:
            logger.debug(
                "Stage 2 FAST PATH: Unique %s indicators detected", fast_format
            )
            # Calculate likelihoods for all formats for transparency
            format_likelihoods, format_posteriors = self._stage2_discriminate_formats(
                data
            )
            # Boost confidence for fast-path detected format to reflect high certainty
            format_posteriors = self._boost_fast_path_confidence(
                format_posteriors, fast_format
            )
        else:
            # Stage 2: Full format-specific discrimination
            format_likelihoods, format_posteriors = self._stage2_discriminate_formats(
                data
            )

        return HierarchicalClassificationResult(
            is_test_data=True,
            test_data_confidence=test_confidence,
            test_data_evidence=test_evidence,
            format_posteriors=format_posteriors,
            format_likelihoods=format_likelihoods,
        )

    def _boost_fast_path_confidence(
        self, format_posteriors: dict[str, float], fast_format: str
    ) -> dict[str, float]:
        """Boost confidence for fast-path detected format.

        When unique combos are found, we should have high confidence (>= 0.9).
        This method redistributes probability mass to achieve this target.

        Args:
            format_posteriors: Current posterior probabilities
            fast_format: Format detected by fast path

        Returns:
            Updated format posteriors with boosted confidence for fast_format
        """
        if fast_format not in format_posteriors:
            return format_posteriors

        current_confidence = format_posteriors[fast_format]
        if current_confidence >= 0.9:
            return format_posteriors

        # Redistribute probability mass to boost fast-path format
        boost_amount = 0.9 - current_confidence
        other_formats = [f for f in format_posteriors if f != fast_format]

        if other_formats:
            total_other = sum(format_posteriors[f] for f in other_formats)
            if total_other > 0:
                for fmt in other_formats:
                    reduction = (format_posteriors[fmt] / total_other) * boost_amount
                    format_posteriors[fmt] = max(
                        0.0, format_posteriors[fmt] - reduction
                    )

        format_posteriors[fast_format] = 0.9
        return format_posteriors

    def _stage1_validate_test_data(
        self, data: dict[str, Any]
    ) -> tuple[bool, float, dict[str, Any]]:
        """Stage 1: Validate that input represents test management data.

        This stage checks for generic test data indicators that are common
        across test management formats, not format-specific patterns.

        Returns:
            Tuple of (is_test_data, confidence, evidence_dict)
        """
        if not isinstance(data, dict) or not data:
            return False, 0.0, {"reason": "Not a dictionary or empty"}

        # Extract all keys from nested structure
        all_keys = self._extract_all_keys(data)
        key_tokens = self._collect_key_tokens(all_keys)

        # Check for generic test data indicators
        # Generic indicators provide moderate evidence for test data
        evidence_items: list[EvidenceItem] = [
            EvidenceItem(
                source=EvidenceSource.TEST_DATA_INDICATOR,
                weight=EvidenceWeight.MODERATE,
                confidence=1.0,
                details=f"Found test data indicator: {indicator}",
            )
            for indicator in self._stage1_indicator_tokens
            if indicator in key_tokens
        ]

        # Calculate completeness: how many indicators found?
        total_indicators = len(self._stage1_indicator_tokens)
        found_indicators = len(evidence_items)
        completeness = (
            found_indicators / total_indicators if total_indicators > 0 else 0.0
        )

        # Calculate structural quality: depth, breadth, complexity
        structure_score = self._assess_structural_quality(data)

        # Check for strong test data indicators that should bypass strict completeness
        strong_test_indicators = {
            "tests",
            "testcases",
            "testcase",
            "testsuite",
            "testsuites",
        }
        has_strong_indicators = any(
            indicator in key_tokens for indicator in strong_test_indicators
        )

        if has_strong_indicators:
            # For data with clear test indicators, be more lenient
            # Structure quality becomes more important than completeness
            test_data_confidence = 0.3 * completeness + 0.7 * structure_score
        else:
            # For ambiguous data, require higher completeness
            test_data_confidence = 0.7 * completeness + 0.3 * structure_score

        evidence_dict = {
            "found_indicators": found_indicators,
            "total_indicators": total_indicators,
            "completeness": completeness,
            "structure_score": structure_score,
            "evidence_items": [
                {
                    "source": item.source,
                    "details": item.details,
                    "weight": item.weight.value,
                }
                for item in evidence_items
            ],
        }

        is_test_data = test_data_confidence >= self.MIN_TEST_DATA_CONFIDENCE

        return is_test_data, test_data_confidence, evidence_dict

    def _stage2_discriminate_formats(
        self, data: dict[str, Any]
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Stage 2: Discriminate between specific test management formats.

        This stage uses format-specific indicators and multi-class
        Bayesian normalization to discriminate between formats.

        Returns:
            Tuple of (format_likelihoods, format_posteriors)
        """
        format_likelihoods: dict[str, float] = {}

        # Collect evidence and calculate likelihoods for all formats
        for format_type in self.format_registry.get_all_formats():
            evidence_items, total_weight = self.evidence_collector.collect_evidence(
                data, format_type
            )

            format_name = format_type.name

            # Clear previous evidence for this format
            if format_name in self.evidence_accumulator.evidence_profiles:
                del self.evidence_accumulator.evidence_profiles[format_name]

            # Add evidence to accumulator
            for item in evidence_items:
                self.evidence_accumulator.add_evidence(format_name, item)
            self.evidence_accumulator.set_total_possible_weight(
                format_name, total_weight
            )

            # Calculate likelihood P(E|H_i)
            if format_name in self.evidence_accumulator.evidence_profiles:
                profile = self.evidence_accumulator.evidence_profiles[format_name]
                metrics = self.evidence_accumulator._profile_to_metrics(profile)
                bayesian_scorer = self.evidence_accumulator.bayesian_scorer

                # Use calculate_likelihood for Independent Bayesian Scorer
                likelihood = bayesian_scorer.calculate_likelihood(metrics)
                format_likelihoods[format_name] = likelihood
            else:
                format_likelihoods[format_name] = 0.0

        # Apply proper multi-class Bayesian normalization
        format_posteriors = self.evidence_accumulator.calculate_multi_class_confidence(
            format_likelihoods
        )

        return format_likelihoods, format_posteriors

    def _extract_all_keys(self, data: Any, keys: set[str] | None = None) -> set[str]:
        """Recursively extract all keys from nested dict structure."""
        if keys is None:
            keys = set()

        if isinstance(data, dict):
            for key, value in data.items():
                keys.add(key)
                self._extract_all_keys(value, keys)
        elif isinstance(data, list):
            for item in data:
                self._extract_all_keys(item, keys)

        return keys

    def _collect_key_tokens(self, keys: set[str]) -> set[str]:
        """Collect normalized token representations for a set of keys."""
        tokens: set[str] = set()
        for key in keys:
            tokens.update(self._tokenize_key(key))
        return tokens

    def _build_stage1_indicator_tokens(self) -> set[str]:
        """Build comprehensive indicator tokens for Stage 1 validation."""
        indicator_tokens = {
            indicator.lower() for indicator in self.TEST_DATA_INDICATORS
        }

        # Include format-specific field indicators to avoid brittle Stage 1 gating
        for format_def in self.format_registry.get_all_formats().values():
            for field in format_def.get_all_fields():
                for token in self._tokenize_key(field.name):
                    if len(token) >= 3:  # Skip generic tokens like "id"
                        indicator_tokens.add(token)

        return indicator_tokens

    @staticmethod
    def _tokenize_key(key: Any) -> set[str]:
        """Tokenize a key into lowercase components for indicator matching."""
        if not isinstance(key, str):
            return set()

        token_set: set[str] = set()
        # Base lowercase key
        lower_key = key.lower()
        token_set.add(lower_key)

        # Split snake_case or kebab-case segments
        normalized = re.sub(r"[-\s]+", "_", key)
        for segment in normalized.split("_"):
            stripped_segment = segment.strip()
            if stripped_segment:
                token_set.add(stripped_segment.lower())

        # Split camelCase or PascalCase segments
        camel_parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", key)
        for part in camel_parts:
            clean_part = part.strip()
            if clean_part:
                token_set.add(clean_part.lower())

        return token_set

    def _assess_structural_quality(self, data: dict[str, Any]) -> float:
        """Assess structural quality of data for test management format.

        Test data typically has:
        - Moderate depth (2-4 levels of nesting)
        - Multiple fields at each level
        - Mix of scalar and structured values

        Returns:
            Quality score in [0.0, 1.0]
        """
        depth = self._calculate_depth(data)
        breadth = len(data) if isinstance(data, dict) else 0

        # Optimal depth for test data: 2-4 levels
        if 2 <= depth <= 4:
            depth_score = 1.0
        elif depth in (1, 5):
            depth_score = 0.7
        elif depth == 0 or depth >= 6:
            depth_score = 0.3
        else:
            depth_score = 0.5

        # Optimal breadth: 3-10 top-level fields
        if 3 <= breadth <= 10:
            breadth_score = 1.0
        elif 2 <= breadth <= 15:
            breadth_score = 0.7
        else:
            breadth_score = 0.3

        # Weighted average: depth matters more for test data
        return 0.6 * depth_score + 0.4 * breadth_score

    def _calculate_depth(self, data: Any, current_depth: int = 0) -> int:
        """Calculate maximum depth of nested structure."""
        if not isinstance(data, dict | list):
            return current_depth

        if isinstance(data, dict):
            if not data:
                return current_depth
            return max(
                self._calculate_depth(value, current_depth + 1)
                for value in data.values()
            )
        # list case
        if not data:
            return current_depth
        return max(self._calculate_depth(item, current_depth + 1) for item in data)

    def _check_stage1_fast_path(self, key_tokens: set[str]) -> bool:
        """Check if Stage 1 can fast-pass based on strong test data indicators.

        Fast path activates when multiple strong test data indicators are present.

        Args:
            key_tokens: Set of normalized tokens derived from keys in the data

        Returns:
            True if fast path should activate (strong test data evidence)
        """
        # Count how many test data indicators are present
        indicator_count = sum(
            1 for indicator in self._stage1_indicator_tokens if indicator in key_tokens
        )

        # Fast pass if we have at least N strong indicators
        return indicator_count >= self.FAST_PATH_TEST_DATA_INDICATORS

    def _check_stage2_fast_path(self, all_keys_lower: set[str]) -> str | None:
        """Check if Stage 2 can fast-pass based on unique format combinations.

        Fast path activates when a format's unique field combination is present.

        Args:
            all_keys_lower: Set of all lowercased keys in the data

        Returns:
            Format name if fast path detected, None otherwise
        """
        for format_name, combinations in self.FORMAT_UNIQUE_COMBINATIONS.items():
            for combo in combinations:
                # Check if all fields in this combination are present (case-insensitive)
                combo_lower = {field.lower() for field in combo}
                if combo_lower.issubset(all_keys_lower):
                    logger.debug(
                        "Fast path detected for %s: found unique combination %s",
                        format_name,
                        combo,
                    )
                    return format_name

        return None


__all__ = ["HierarchicalClassificationResult", "HierarchicalClassifier"]
