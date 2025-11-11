"""Centralized validation service consolidating scattered validation logic.

The ValidationService provides:
- Unified validation patterns
- Centralized error handling
- Domain-specific validation strategies
- Performance optimization through caching
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Protocol

from importobot.services.strategies import (
    FileValidationStrategy,
    FormatValidationStrategy,
    JsonValidationStrategy,
)
from importobot.utils.validation_models import ValidationResult, ValidationSeverity


class ValidationStrategy(Protocol):
    """Protocol for domain-specific validation strategies."""

    def validate(self, data: Any, context: dict[str, Any]) -> ValidationResult:
        """Validate data according to strategy."""
        ...  # pylint: disable=unnecessary-ellipsis


class ValidationService:
    """Centralized validation service for all Importobot operations.

    Provides:
    - Consistent validation patterns
    - Centralized error handling
    - Performance optimization through strategy caching
    - Domain-specific validation
    """

    def __init__(self, security_level: str = "standard") -> None:
        """Initialize validation service.

        Args:
            security_level: Security level for validation (standard, strict, etc.)
        """
        self.security_level = security_level
        self._strategy_cache: dict[str, ValidationStrategy] = {}
        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register default validation strategies."""
        self._strategy_cache.update(
            {
                "json": JsonValidationStrategy(),
                "file": FileValidationStrategy(self.security_level),
                "format": FormatValidationStrategy(),
            }
        )

    def register_strategy(self, name: str, strategy: ValidationStrategy) -> None:
        """Register a custom validation strategy."""
        self._strategy_cache[name] = strategy

    def validate(
        self,
        data: Any,
        strategy_name: str = "json",
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Perform validation using specified strategy.

        Args:
            data: Data to validate
            strategy_name: Name of validation strategy to use
            context: Additional context for validation

        Returns:
            ValidationResult with detailed validation information
        """
        context = context or {}

        if strategy_name not in self._strategy_cache:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                messages=[f"Unknown validation strategy: {strategy_name}"],
                context=context,
            )

        strategy = self._strategy_cache[strategy_name]
        return strategy.validate(data, context)

    def validate_multiple(
        self, data: Any, strategies: list[str], context: dict[str, Any] | None = None
    ) -> list[ValidationResult]:
        """Validate data using multiple strategies.

        Args:
            data: Data to validate
            strategies: List of strategy names to apply
            context: Additional context for validation

        Returns:
            List of ValidationResults, one per strategy
        """
        results = []
        for strategy_name in strategies:
            result = self.validate(data, strategy_name, context)
            results.append(result)
        return results

    def is_valid(
        self,
        data: Any,
        strategy_name: str = "json",
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Quick validation check returning boolean result."""
        result = self.validate(data, strategy_name, context)
        return result.is_valid

    def get_validation_summary(self, results: list[ValidationResult]) -> dict[str, Any]:
        """Get summary of multiple validation results."""
        total_results = len(results)
        valid_count = sum(1 for r in results if r.is_valid)

        all_messages = []
        max_severity = ValidationSeverity.INFO

        for result in results:
            all_messages.extend(result.messages)
            if result.severity.value > max_severity.value:
                # Handle different severity types
                if isinstance(result.severity, ValidationSeverity):
                    max_severity = result.severity
                # Map other severity types to ValidationSeverity
                elif result.severity.value >= ValidationSeverity.CRITICAL.value:
                    max_severity = ValidationSeverity.CRITICAL
                elif result.severity.value >= ValidationSeverity.ERROR.value:
                    max_severity = ValidationSeverity.ERROR
                elif result.severity.value >= ValidationSeverity.WARNING.value:
                    max_severity = ValidationSeverity.WARNING

        return {
            "total_validations": total_results,
            "valid_count": valid_count,
            "invalid_count": total_results - valid_count,
            "overall_valid": valid_count == total_results,
            "max_severity": max_severity.value,
            "all_messages": all_messages,
        }

    def cross_validate(
        self,
        data: Any,
        strategies: list[str],
        k_folds: int = 5,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform k-fold cross-validation on data using multiple strategies.

        Assess the reliability and consistency of validation results across
        different data subsets and validation strategies.

        Args:
            data: Data to validate (must be iterable for cross-validation)
            strategies: List of strategy names to apply
            k_folds: Number of folds for cross-validation (default: 5)
            context: Additional validation context

        Returns:
            Dictionary containing cross-validation metrics including:
            - fold_results: Results for each fold
            - strategy_consistency: Consistency scores across folds
            - overall_reliability: Overall validation reliability score
            - confidence_intervals: Statistical confidence intervals

        Raises:
            ValueError: If data is not iterable or k_folds is invalid
        """
        # Validate inputs
        data_list = self._validate_cross_validation_inputs(data, k_folds)

        # Perform k-fold validation
        fold_results, strategy_scores = self._perform_k_fold_validation(
            data_list, strategies, k_folds, context
        )

        # Calculate consistency metrics
        strategy_consistency = self._calculate_strategy_consistency(strategy_scores)

        # Calculate overall reliability
        overall_reliability = self._calculate_overall_reliability(strategy_consistency)

        return {
            "k_folds": k_folds,
            "total_data_size": len(data_list),
            "fold_results": fold_results,
            "strategy_consistency": strategy_consistency,
            "overall_reliability": overall_reliability,
            "recommendation": self._get_cross_validation_recommendation(
                overall_reliability, strategy_consistency
            ),
        }

    def _validate_cross_validation_inputs(self, data: Any, k_folds: int) -> list[Any]:
        """Validate inputs for cross-validation."""
        if not hasattr(data, "__iter__") or isinstance(data, str | bytes):
            raise ValueError("Data must be iterable for cross-validation")

        if k_folds < 2 or k_folds > 10:
            raise ValueError("k_folds must be between 2 and 10")

        data_list = list(data)
        if len(data_list) < k_folds:
            raise ValueError(
                f"Data size ({len(data_list)}) must be >= k_folds ({k_folds})"
            )

        return data_list

    def _perform_k_fold_validation(
        self,
        data_list: list[Any],
        strategies: list[str],
        k_folds: int,
        context: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], dict[str, list[float]]]:
        """Perform k-fold validation and return results."""
        fold_size = len(data_list) // k_folds
        fold_results = []
        strategy_scores: dict[str, list[float]] = {
            strategy: [] for strategy in strategies
        }

        for fold in range(k_folds):
            # Create train/validation split for this fold
            start_idx = fold * fold_size
            end_idx = start_idx + fold_size if fold < k_folds - 1 else len(data_list)

            validation_data = data_list[start_idx:end_idx]
            train_data = data_list[:start_idx] + data_list[end_idx:]

            # Enrich context with fold-specific information
            fold_context = (context or {}).copy()
            fold_context.update(
                {
                    "fold_number": fold + 1,
                    "total_folds": k_folds,
                    "validation_size": len(validation_data),
                    "train_size": len(train_data),
                    "is_cross_validation": True,
                }
            )

            # Validate using each strategy
            fold_strategy_results = {}
            for strategy in strategies:
                results = self.validate_multiple(
                    validation_data, [strategy], fold_context
                )
                valid_ratio = (
                    sum(1 for r in results if r.is_valid) / len(results)
                    if results
                    else 0.0
                )
                fold_strategy_results[strategy] = valid_ratio
                strategy_scores[strategy].append(valid_ratio)

            fold_results.append(
                {
                    "fold": fold + 1,
                    "validation_size": len(validation_data),
                    "train_size": len(train_data),
                    "strategy_scores": fold_strategy_results,
                }
            )

        return fold_results, strategy_scores

    def _calculate_strategy_consistency(
        self, strategy_scores: dict[str, list[float]]
    ) -> dict[str, Any]:
        """Calculate consistency metrics for each strategy."""
        strategy_consistency = {}
        for strategy, scores in strategy_scores.items():
            if len(scores) > 1:
                mean_score = sum(scores) / len(scores)
                variance = sum((s - mean_score) ** 2 for s in scores) / (
                    len(scores) - 1
                )
                std_dev = variance**0.5
                consistency = 1.0 - (
                    std_dev / (mean_score + 1e-10)
                )  # Avoid division by zero
                strategy_consistency[strategy] = {
                    "mean_score": mean_score,
                    "std_deviation": std_dev,
                    "consistency_score": max(0.0, consistency),
                    "confidence_interval_95": self._calculate_confidence_interval(
                        scores, 0.95
                    ),
                }
            else:
                strategy_consistency[strategy] = {
                    "mean_score": scores[0] if scores else 0.0,
                    "std_deviation": 0.0,
                    "consistency_score": 1.0,
                    "confidence_interval_95": [
                        scores[0] if scores else 0.0,
                        scores[0] if scores else 0.0,
                    ],
                }
        return strategy_consistency

    def _calculate_overall_reliability(
        self, strategy_consistency: dict[str, Any]
    ) -> float:
        """Calculate overall reliability score."""
        return (
            sum(
                metrics["consistency_score"] * metrics["mean_score"]
                for metrics in strategy_consistency.values()
            )
            / len(strategy_consistency)
            if strategy_consistency
            else 0.0
        )

    def _calculate_confidence_interval(
        self, values: list[float], confidence: float
    ) -> list[float]:
        """Calculate confidence interval for a list of values using t-distribution.

        Args:
            values: List of numerical values
            confidence: Confidence level (e.g., 0.95 for 95% confidence)

        Returns:
            List containing [lower_bound, upper_bound] of confidence interval
        """
        if not values or len(values) < 2:
            return [0.0, 0.0]

        n = len(values)
        mean = statistics.mean(values)
        std_err = statistics.stdev(values) / math.sqrt(n)

        # Approximate t-value for common confidence levels
        t_values = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        t_value = t_values.get(confidence, 1.96)

        margin_of_error = t_value * std_err
        return [mean - margin_of_error, mean + margin_of_error]

    def _get_cross_validation_recommendation(
        self, reliability: float, consistency: dict[str, Any]
    ) -> str:
        """Generate recommendation based on cross-validation results."""
        if reliability >= 0.9:
            return (
                "HIGH RELIABILITY: Validation results are highly consistent "
                "and reliable."
            )
        if reliability >= 0.7:
            return (
                "GOOD RELIABILITY: Validation results are generally consistent "
                "with minor variations."
            )
        if reliability >= 0.5:
            return (
                "MODERATE RELIABILITY: Validation results show moderate consistency - "
                "consider reviewing strategies."
            )

        inconsistent_strategies = [
            strategy
            for strategy, metrics in consistency.items()
            if metrics["consistency_score"] < 0.5
        ]
        strategies_str = ", ".join(inconsistent_strategies)
        return (
            f"LOW RELIABILITY: Validation results are inconsistent. "
            f"Review strategies: {strategies_str}"
        )
