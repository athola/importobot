"""Test case complexity analysis for enhanced Bayesian evidence scoring.

This module implements complexity-aware evidence analysis that considers:
- Test case structural complexity (steps, nestedness, data richness)
- Evidence diversity and uniqueness
- Information content and discriminative potential

Mathematical Foundation:
Complexity Score = α₁·step_count + α₂·nestedness + α₃·data_richness +
        α₄·evidence_diversity
Where α₁..α₄ are empirically determined weighting factors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from importobot.utils.logging import get_logger

logger = get_logger()


@dataclass
class ComplexityMetrics:
    """Metrics representing test case complexity and information content."""

    # Structural complexity factors
    step_count: int = 0  # Number of test steps/actions
    nested_structure_depth: int = 0  # Maximum nesting depth
    field_count: int = 0  # Total number of fields/properties
    array_count: int = 0  # Number of arrays/lists
    object_count: int = 0  # Number of nested objects

    # Evidence diversity factors
    unique_field_patterns: int = 0  # Number of unique field naming patterns
    format_specific_indicators: int = 0  # Format-specific keywords/structures
    conditional_logic_elements: int = 0  # Branches, conditions, loops

    # Information richness factors
    total_text_length: int = 0  # Total text content length
    parameter_count: int = 0  # Number of parameters/variables
    relationship_count: int = 0  # Cross-references between fields

    @property
    def complexity_score(self) -> float:
        """Calculate overall complexity score (0.0 to 1.0)."""
        # Normalize individual components
        step_score = min(self.step_count / 10.0, 1.0)  # Normalize to 10 steps max
        nesting_score = min(self.nested_structure_depth / 4.0, 1.0)  # 4 levels max
        field_score = min(self.field_count / 20.0, 1.0)  # 20 fields max
        data_score = min(
            (self.array_count + self.object_count) / 8.0, 1.0
        )  # 8 containers max

        # Evidence diversity scoring
        pattern_score = min(self.unique_field_patterns / 8.0, 1.0)  # 8 patterns max
        indicator_score = min(
            self.format_specific_indicators / 5.0, 1.0
        )  # 5 indicators max
        conditional_score = min(
            self.conditional_logic_elements / 6.0, 1.0
        )  # 6 elements max

        # Information richness scoring
        text_score = min(self.total_text_length / 1000.0, 1.0)  # 1000 chars max
        param_score = min(self.parameter_count / 10.0, 1.0)  # 10 params max
        relationship_score = min(
            self.relationship_count / 5.0, 1.0
        )  # 5 relationships max

        # Weighted combination (empirically determined weights)
        complexity = (
            0.20 * step_score  # 20% - structural complexity
            + 0.15 * nesting_score  # 15% - nested structure depth
            + 0.10 * field_score  # 10% - field count
            + 0.08 * data_score  # 8%  - data structures
            + 0.15 * pattern_score  # 15% - field pattern diversity
            + 0.10 * indicator_score  # 10% - format indicators
            + 0.05 * conditional_score  # 5%  - conditional logic
            + 0.07 * text_score  # 7%  - information richness
            + 0.05 * param_score  # 5%  - parameters
            + 0.05 * relationship_score  # 5%  - relationships
        )

        return min(complexity, 1.0)

    @property
    def information_content(self) -> float:
        """Calculate information content score (0.0 to 1.0)."""
        # Focus on discriminative information
        discriminative_factors = [
            self.format_specific_indicators / 5.0,
            self.unique_field_patterns / 8.0,
            self.conditional_logic_elements / 6.0,
            self.relationship_count / 5.0,
        ]

        return min(sum(discriminative_factors) / 4.0, 1.0)

    def validate(self) -> bool:
        """Validate complexity metrics are reasonable."""
        return (
            self.step_count >= 0
            and self.nested_structure_depth >= 0
            and self.field_count >= 0
            and self.unique_field_patterns >= 0
            and 0.0 <= self.complexity_score <= 1.0
            and 0.0 <= self.information_content <= 1.0
        )


class TestCaseComplexityAnalyzer:
    """Analyzer for test case complexity and information content.

    This analyzer extracts complexity metrics from test case data to enable
    complexity-aware evidence weighting and confidence scaling.
    """

    def __init__(self) -> None:
        """Initialize the complexity analyzer."""
        self.logger = get_logger()

    def analyze_complexity(self, test_data: dict[str, Any]) -> ComplexityMetrics:
        """Analyze test case complexity and return complexity metrics.

        Args:
            test_data: Dictionary representing test case data

        Returns:
            ComplexityMetrics with calculated complexity scores
        """
        metrics = ComplexityMetrics()

        # Extract structural complexity
        self._analyze_structure(test_data, metrics)

        # Extract evidence diversity
        self._analyze_evidence_diversity(test_data, metrics)

        # Extract information richness
        self._analyze_information_richness(test_data, metrics)

        # Validate metrics
        if not metrics.validate():
            self.logger.warning("Invalid complexity metrics detected")

        return metrics

    def _analyze_structure(
        self, data: Any, metrics: ComplexityMetrics, depth: int = 0
    ) -> None:
        """Analyze structural complexity of test data."""
        if isinstance(data, dict):
            # Update depth tracking
            metrics.nested_structure_depth = max(metrics.nested_structure_depth, depth)
            metrics.field_count += len(data)

            # Count arrays and objects
            for value in data.values():
                if isinstance(value, list):
                    metrics.array_count += 1
                    metrics.step_count += len(value)  # Likely test steps
                    self._analyze_structure(value, metrics, depth + 1)
                elif isinstance(value, dict):
                    metrics.object_count += 1
                    self._analyze_structure(value, metrics, depth + 1)
                elif isinstance(value, str):
                    metrics.total_text_length += len(value)

        elif isinstance(data, list):
            for item in data:
                self._analyze_structure(item, metrics, depth + 1)

    def _analyze_evidence_diversity(
        self, test_data: dict[str, Any], metrics: ComplexityMetrics
    ) -> None:
        """Analyze evidence diversity and format-specific indicators."""
        if not isinstance(test_data, dict):
            return

        # Extract field names for pattern analysis
        all_keys = self._extract_all_keys(test_data)

        # Analyze unique field patterns
        metrics.unique_field_patterns = self._count_unique_patterns(all_keys)

        # Count format-specific indicators
        metrics.format_specific_indicators = self._count_format_indicators(test_data)

        # Count conditional logic elements
        metrics.conditional_logic_elements = self._count_conditional_elements(test_data)

    def _count_unique_patterns(self, all_keys: list[str]) -> int:
        """Count unique field naming patterns."""
        patterns = set()
        for key in all_keys:
            patterns.update(self._extract_patterns_from_key(key))
        return len(patterns)

    def _extract_patterns_from_key(self, key: str) -> set[str]:
        """Extract patterns from a single key."""
        patterns = set()
        key_lower = key.lower()

        pattern_mappings = {
            "identifier_pattern": "id",
            "naming_pattern": "name",
            "status_pattern": "status",
            "test_pattern": "test",
            "execution_pattern": "execution",
            "cycle_pattern": "cycle",
            "issue_pattern": "issue",
        }

        for pattern_name, pattern_text in pattern_mappings.items():
            if pattern_text in key_lower:
                patterns.add(pattern_name)

        if "step" in key_lower or "action" in key_lower:
            patterns.add("step_pattern")

        return patterns

    def _count_format_indicators(self, test_data: dict[str, Any]) -> int:
        """Count format-specific indicators."""
        format_indicators = 0

        # Define format field mappings
        format_fields = {
            "zephyr": ["testCase", "execution", "cycle"],
            "jira": ["issues", "testExecutions", "xrayInfo"],
            "testlink": ["testsuites", "testsuite", "testcase"],
            "testrail": ["cases", "suite", "run", "results"],
        }

        for fields in format_fields.values():
            for field in fields:
                if field in test_data:
                    format_indicators += 1

        return format_indicators

    def _count_conditional_elements(self, test_data: dict[str, Any]) -> int:
        """Count conditional logic elements."""
        conditional_patterns = ["if", "else", "when", "then", "condition", "branch"]
        text_content = str(test_data).lower()

        count = 0
        for pattern in conditional_patterns:
            count += text_content.count(pattern)

        return count

    def _analyze_information_richness(
        self, test_data: dict[str, Any], metrics: ComplexityMetrics
    ) -> None:
        """Analyze information richness and relationships."""
        if not isinstance(test_data, dict):
            return

        # Count parameters (heuristic: values that look like variables)
        parameter_patterns = ["${", "${", "{{", "}}", "%(", ")%", "param", "var"]
        text_content = str(test_data)
        for pattern in parameter_patterns:
            metrics.parameter_count += text_content.count(pattern)

        # Count relationships (cross-references between fields)
        relationships = 0
        if "execution" in test_data and "testCase" in test_data:
            relationships += 1  # execution references testCase
        if "cycle" in test_data and "execution" in test_data:
            relationships += 1  # execution references cycle
        if "issues" in test_data and "testExecutions" in test_data:
            relationships += 1  # testExecutions references issues

        metrics.relationship_count = relationships

    def _extract_all_keys(self, data: Any) -> list[str]:
        """Extract all keys from nested dictionary structure."""
        keys = []

        if isinstance(data, dict):
            for key, value in data.items():
                keys.append(key)
                keys.extend(self._extract_all_keys(value))
        elif isinstance(data, list):
            for item in data:
                keys.extend(self._extract_all_keys(item))

        return keys

    def calculate_complexity_amplification(self, metrics: ComplexityMetrics) -> float:
        """Calculate complexity-based amplification factor.

        Args:
            metrics: Complexity metrics for the test case

        Returns:
            Amplification factor (1.0 to 1.5) for likelihood adjustment
        """
        complexity = metrics.complexity_score
        info_content = metrics.information_content

        # Base amplification from complexity
        base_amplification = 1.0 + (0.3 * complexity)  # Max 1.3x from complexity

        # Additional amplification from information content
        info_amplification = 1.0 + (0.2 * info_content)  # Max 1.2x from info content

        # Combined amplification (capped at 1.5x)
        total_amplification = base_amplification * info_amplification
        return min(total_amplification, 1.5)

    def get_complexity_summary(self, test_data: dict[str, Any]) -> dict[str, Any]:
        """Get comprehensive complexity analysis summary.

        Args:
            test_data: Dictionary representing test case data

        Returns:
            Dictionary with complexity analysis summary
        """
        metrics = self.analyze_complexity(test_data)
        amplification = self.calculate_complexity_amplification(metrics)

        return {
            "complexity_score": metrics.complexity_score,
            "information_content": metrics.information_content,
            "complexity_amplification": amplification,
            "structural_metrics": {
                "step_count": metrics.step_count,
                "nested_depth": metrics.nested_structure_depth,
                "field_count": metrics.field_count,
                "data_structures": metrics.array_count + metrics.object_count,
            },
            "evidence_metrics": {
                "unique_patterns": metrics.unique_field_patterns,
                "format_indicators": metrics.format_specific_indicators,
                "conditional_elements": metrics.conditional_logic_elements,
            },
            "information_metrics": {
                "text_length": metrics.total_text_length,
                "parameter_count": metrics.parameter_count,
                "relationships": metrics.relationship_count,
            },
            "complexity_level": self._classify_complexity(metrics.complexity_score),
        }

    def _classify_complexity(self, score: float) -> str:
        """Classify complexity level based on score."""
        if score < 0.2:
            return "Very Low"
        if score < 0.4:
            return "Low"
        if score < 0.6:
            return "Medium"
        if score < 0.8:
            return "High"
        return "Very High"


__all__ = ["ComplexityMetrics", "TestCaseComplexityAnalyzer"]
