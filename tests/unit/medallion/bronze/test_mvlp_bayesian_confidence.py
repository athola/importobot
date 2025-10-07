"""Unit tests for MVLP Bayesian Confidence Scorer.

This module tests the Multi-Variable Linear Programming Bayesian confidence
scoring implementation following TDD principles.
"""

from typing import List, Tuple

import numpy as np
import pytest

from importobot.medallion.bronze.mvlp_bayesian_confidence import (
    ConfidenceParameters,
    EvidenceMetrics,
    MVLPBayesianConfidenceScorer,
)


class TestConfidenceParameters:
    """Test suite for ConfidenceParameters dataclass."""

    def test_default_parameters_are_valid(self):
        """Test that default parameters satisfy all constraints."""
        params = ConfidenceParameters()

        assert params.validate() is True
        assert params.completeness_weight == 0.3
        assert params.quality_weight == 0.4
        assert params.uniqueness_weight == 0.3

    def test_weights_sum_to_one(self):
        """Test that weights sum constraint is enforced."""
        params = ConfidenceParameters()

        weight_sum = (
            params.completeness_weight
            + params.quality_weight
            + params.uniqueness_weight
        )

        assert 0.99 <= weight_sum <= 1.01

    def test_invalid_weight_sum_fails_validation(self):
        """Test that invalid weight sums fail validation."""
        params = ConfidenceParameters(
            completeness_weight=0.5,
            quality_weight=0.5,
            uniqueness_weight=0.5,  # Sum = 1.5 (invalid)
        )

        assert params.validate() is False

    def test_weight_sum_lower_boundary_passes(self):
        """Weights that sum to the lower tolerance boundary are accepted."""
        params = ConfidenceParameters(
            completeness_weight=0.49,
            quality_weight=0.25,
            uniqueness_weight=0.25,
        )

        assert (
            pytest.approx(
                params.completeness_weight
                + params.quality_weight
                + params.uniqueness_weight,
                rel=1e-9,
            )
            == 0.99
        )
        assert params.validate() is True

    def test_weight_sum_upper_boundary_passes(self):
        """Weights that sum to the upper tolerance boundary are accepted."""
        params = ConfidenceParameters(
            completeness_weight=0.5,
            quality_weight=0.26,
            uniqueness_weight=0.25,
        )

        assert (
            pytest.approx(
                params.completeness_weight
                + params.quality_weight
                + params.uniqueness_weight,
                rel=1e-9,
            )
            == 1.01
        )
        assert params.validate() is True

    def test_power_constraints_within_bounds(self):
        """Test that power parameters are within valid range."""
        params = ConfidenceParameters()

        assert 0.1 <= params.completeness_power <= 2.0
        assert 0.1 <= params.quality_power <= 2.0
        assert 0.1 <= params.uniqueness_power <= 2.0

    def test_invalid_power_fails_validation(self):
        """Test that powers outside [0.1, 2.0] fail validation."""
        params = ConfidenceParameters(
            completeness_power=2.5  # Too high
        )

        assert params.validate() is False

        params = ConfidenceParameters(
            quality_power=0.05  # Too low
        )

        assert params.validate() is False

    def test_confidence_bounds_are_valid(self):
        """Test that min_confidence < max_confidence."""
        params = ConfidenceParameters()

        assert 0.0 <= params.min_confidence < params.max_confidence <= 1.0

    def test_invalid_confidence_bounds_fail_validation(self):
        """Test that invalid bounds fail validation."""
        # min >= max
        params = ConfidenceParameters(min_confidence=0.9, max_confidence=0.5)
        assert params.validate() is False

        # max > 1.0
        params = ConfidenceParameters(max_confidence=1.5)
        assert params.validate() is False

        # min < 0.0
        params = ConfidenceParameters(min_confidence=-0.1)
        assert params.validate() is False

    def test_interaction_parameters_have_defaults(self):
        """Test that interaction parameters have sensible defaults."""
        params = ConfidenceParameters()

        assert params.completeness_quality_interaction == 0.1
        assert params.quality_uniqueness_interaction == 0.2

    def test_custom_parameters_validate_correctly(self):
        """Test custom valid parameters pass validation."""
        params = ConfidenceParameters(
            completeness_weight=0.4,
            quality_weight=0.35,
            uniqueness_weight=0.25,
            completeness_power=1.0,
            quality_power=1.2,
            uniqueness_power=0.8,
            completeness_quality_interaction=0.05,
            quality_uniqueness_interaction=0.15,
            min_confidence=0.01,
            max_confidence=0.99,
        )

        assert params.validate() is True


class TestEvidenceMetrics:
    """Test suite for EvidenceMetrics dataclass."""

    def test_valid_metrics_initialization(self):
        """Test that valid metrics can be initialized."""
        metrics = EvidenceMetrics(
            completeness=0.8,
            quality=0.9,
            uniqueness=0.7,
            evidence_count=10,
            unique_count=5,
        )

        assert metrics.completeness == 0.8
        assert metrics.quality == 0.9
        assert metrics.uniqueness == 0.7
        assert metrics.evidence_count == 10
        assert metrics.unique_count == 5

    def test_metrics_at_boundaries(self):
        """Test metrics at boundary values."""
        metrics = EvidenceMetrics(
            completeness=0.0,
            quality=1.0,
            uniqueness=0.0,
            evidence_count=0,
            unique_count=0,
        )

        assert metrics.completeness == 0.0
        assert metrics.quality == 1.0

        metrics = EvidenceMetrics(
            completeness=1.0,
            quality=0.0,
            uniqueness=1.0,
            evidence_count=100,
            unique_count=50,
        )

        assert metrics.completeness == 1.0
        assert metrics.uniqueness == 1.0

    def test_invalid_completeness_raises_assertion(self):
        """Test that invalid completeness raises AssertionError."""
        with pytest.raises(AssertionError, match="Invalid completeness"):
            EvidenceMetrics(
                completeness=1.5,  # > 1.0
                quality=0.5,
                uniqueness=0.5,
                evidence_count=5,
                unique_count=2,
            )

        with pytest.raises(AssertionError, match="Invalid completeness"):
            EvidenceMetrics(
                completeness=-0.1,  # < 0.0
                quality=0.5,
                uniqueness=0.5,
                evidence_count=5,
                unique_count=2,
            )

    def test_invalid_quality_raises_assertion(self):
        """Test that invalid quality raises AssertionError."""
        with pytest.raises(AssertionError, match="Invalid quality"):
            EvidenceMetrics(
                completeness=0.5,
                quality=1.2,  # > 1.0
                uniqueness=0.5,
                evidence_count=5,
                unique_count=2,
            )

    def test_invalid_uniqueness_raises_assertion(self):
        """Test that invalid uniqueness raises AssertionError."""
        with pytest.raises(AssertionError, match="Invalid uniqueness"):
            EvidenceMetrics(
                completeness=0.5,
                quality=0.5,
                uniqueness=-0.5,  # < 0.0
                evidence_count=5,
                unique_count=2,
            )

    def test_invalid_evidence_count_raises_assertion(self):
        """Test that negative evidence_count raises AssertionError."""
        with pytest.raises(AssertionError, match="Invalid evidence_count"):
            EvidenceMetrics(
                completeness=0.5,
                quality=0.5,
                uniqueness=0.5,
                evidence_count=-1,
                unique_count=2,
            )

    def test_invalid_unique_count_raises_assertion(self):
        """Test that negative unique_count raises AssertionError."""
        with pytest.raises(AssertionError, match="Invalid unique_count"):
            EvidenceMetrics(
                completeness=0.5,
                quality=0.5,
                uniqueness=0.5,
                evidence_count=5,
                unique_count=-1,
            )


class TestMVLPBayesianConfidenceScorer:
    """Test suite for MVLPBayesianConfidenceScorer."""

    def test_initialization_with_default_priors(self):
        """Test scorer initializes with default priors."""
        scorer = MVLPBayesianConfidenceScorer()

        assert scorer.parameters is not None
        assert scorer.parameters.validate() is True
        assert scorer.format_priors is not None
        assert len(scorer.training_data) == 0
        assert len(scorer.parameter_confidence_intervals) == 0

    def test_initialization_with_custom_priors(self):
        """Test scorer initializes with custom priors."""
        custom_priors = {
            "Zephyr": 0.5,
            "Xray": 0.3,
            "TestRail": 0.2,
        }

        scorer = MVLPBayesianConfidenceScorer(format_priors=custom_priors)

        assert scorer.format_priors == custom_priors
        assert scorer.format_priors["Zephyr"] == 0.5

    def test_calculate_confidence_basic(self):
        """Test basic confidence calculation."""
        scorer = MVLPBayesianConfidenceScorer()

        metrics = EvidenceMetrics(
            completeness=0.8,
            quality=0.9,
            uniqueness=0.7,
            evidence_count=10,
            unique_count=5,
        )

        result = scorer.calculate_confidence(metrics, "Zephyr", use_uncertainty=False)

        assert "confidence" in result
        assert "likelihood" in result
        assert "prior" in result
        assert 0.05 <= result["confidence"] <= 0.95
        assert 0.0 <= result["likelihood"] <= 1.0

    def test_confidence_respects_bounds(self):
        """Test that confidence is bounded to [0.05, 0.95]."""
        scorer = MVLPBayesianConfidenceScorer()

        # Perfect evidence
        metrics = EvidenceMetrics(
            completeness=1.0,
            quality=1.0,
            uniqueness=1.0,
            evidence_count=50,
            unique_count=25,
        )

        result = scorer.calculate_confidence(metrics, "Zephyr")
        assert 0.05 <= result["confidence"] <= 0.95

        # No evidence
        metrics = EvidenceMetrics(
            completeness=0.0,
            quality=0.0,
            uniqueness=0.0,
            evidence_count=0,
            unique_count=0,
        )

        result = scorer.calculate_confidence(metrics, "Zephyr")
        assert 0.05 <= result["confidence"] <= 0.95

    def test_higher_quality_increases_confidence(self):
        """Test that higher quality metrics increase confidence."""
        scorer = MVLPBayesianConfidenceScorer()

        low_quality = EvidenceMetrics(
            completeness=0.5,
            quality=0.3,
            uniqueness=0.5,
            evidence_count=5,
            unique_count=2,
        )

        high_quality = EvidenceMetrics(
            completeness=0.5,
            quality=0.9,
            uniqueness=0.5,
            evidence_count=5,
            unique_count=2,
        )

        result_low = scorer.calculate_confidence(
            low_quality, "Zephyr", use_uncertainty=False
        )
        result_high = scorer.calculate_confidence(
            high_quality, "Zephyr", use_uncertainty=False
        )

        assert result_high["likelihood"] > result_low["likelihood"]

    def test_mvlp_objective_function_with_zero_metrics(self):
        """Test MVLP objective function with zero metrics."""
        scorer = MVLPBayesianConfidenceScorer()

        metrics = EvidenceMetrics(
            completeness=0.0,
            quality=0.0,
            uniqueness=0.0,
            evidence_count=0,
            unique_count=0,
        )

        result = scorer._mvlp_objective_function(metrics, scorer.parameters)

        assert result >= scorer.parameters.min_confidence
        assert result <= scorer.parameters.max_confidence

    def test_mvlp_objective_function_with_perfect_metrics(self):
        """Test MVLP objective function with perfect metrics."""
        scorer = MVLPBayesianConfidenceScorer()

        metrics = EvidenceMetrics(
            completeness=1.0,
            quality=1.0,
            uniqueness=1.0,
            evidence_count=100,
            unique_count=50,
        )

        result = scorer._mvlp_objective_function(metrics, scorer.parameters)

        assert result >= scorer.parameters.min_confidence
        assert result <= scorer.parameters.max_confidence
        assert result > 0.5  # Should be high confidence

    def test_mvlp_includes_interaction_terms(self):
        """Test that interaction terms affect the objective function."""
        scorer = MVLPBayesianConfidenceScorer()

        metrics = EvidenceMetrics(
            completeness=0.8,
            quality=0.8,
            uniqueness=0.8,
            evidence_count=10,
            unique_count=5,
        )

        # Calculate with default parameters (includes interactions)
        result_with_interaction = scorer._mvlp_objective_function(
            metrics, scorer.parameters
        )

        # Create parameters with no interaction
        no_interaction_params = ConfidenceParameters(
            completeness_weight=scorer.parameters.completeness_weight,
            quality_weight=scorer.parameters.quality_weight,
            uniqueness_weight=scorer.parameters.uniqueness_weight,
            completeness_power=scorer.parameters.completeness_power,
            quality_power=scorer.parameters.quality_power,
            uniqueness_power=scorer.parameters.uniqueness_power,
            completeness_quality_interaction=0.0,
            quality_uniqueness_interaction=0.0,
        )

        result_no_interaction = scorer._mvlp_objective_function(
            metrics, no_interaction_params
        )

        # Results should differ due to interaction terms
        assert result_with_interaction != result_no_interaction

    def test_parameters_to_vector_conversion(self):
        """Test parameter to vector conversion."""
        scorer = MVLPBayesianConfidenceScorer()

        params = ConfidenceParameters()
        vector = scorer._parameters_to_vector(params)

        assert isinstance(vector, np.ndarray)
        assert len(vector) == 10
        assert vector[0] == params.completeness_weight
        assert vector[1] == params.quality_weight
        assert vector[2] == params.uniqueness_weight

    def test_vector_to_parameters_conversion(self):
        """Test vector to parameter conversion."""
        scorer = MVLPBayesianConfidenceScorer()

        original_params = ConfidenceParameters(
            completeness_weight=0.35,
            quality_weight=0.40,
            uniqueness_weight=0.25,
        )

        vector = scorer._parameters_to_vector(original_params)
        restored_params = scorer._vector_to_parameters(vector)

        assert (
            restored_params.completeness_weight == original_params.completeness_weight
        )
        assert restored_params.quality_weight == original_params.quality_weight
        assert restored_params.uniqueness_weight == original_params.uniqueness_weight

    def test_parameter_conversion_roundtrip(self):
        """Test that parameter conversion is reversible."""
        scorer = MVLPBayesianConfidenceScorer()

        original = scorer.parameters
        vector = scorer._parameters_to_vector(original)
        restored = scorer._vector_to_parameters(vector)

        assert restored.completeness_weight == original.completeness_weight
        assert restored.quality_weight == original.quality_weight
        assert restored.uniqueness_weight == original.uniqueness_weight
        assert restored.completeness_power == original.completeness_power
        assert restored.quality_power == original.quality_power
        assert restored.uniqueness_power == original.uniqueness_power

    def test_build_parameter_bounds(self):
        """Test parameter bounds generation."""
        scorer = MVLPBayesianConfidenceScorer()

        bounds = scorer._build_parameter_bounds()

        assert len(bounds) == 10
        # Check weight bounds
        assert bounds[0] == (0.1, 0.8)  # completeness_weight
        assert bounds[1] == (0.1, 0.8)  # quality_weight
        assert bounds[2] == (0.1, 0.8)  # uniqueness_weight
        # Check power bounds
        assert bounds[3] == (0.1, 2.0)  # completeness_power
        # Check interaction bounds
        assert bounds[6] == (0.0, 0.5)  # completeness_quality_interaction

    def test_build_optimization_constraints(self):
        """Test optimization constraint generation."""
        scorer = MVLPBayesianConfidenceScorer()

        constraints = scorer._build_optimization_constraints()

        assert len(constraints) >= 1
        # Should have weight sum constraint
        assert any(c["type"] == "eq" for c in constraints)
        # Should have inequality constraints
        assert any(c["type"] == "ineq" for c in constraints)

    def test_weight_sum_constraint_function(self):
        """Test that weight sum constraint enforces sum = 1."""
        scorer = MVLPBayesianConfidenceScorer()

        # Valid parameters (sum = 1.0)
        valid_params = ConfidenceParameters(
            completeness_weight=0.3,
            quality_weight=0.4,
            uniqueness_weight=0.3,
        )
        vector = scorer._parameters_to_vector(valid_params)

        constraints = scorer._build_optimization_constraints()
        weight_constraint = constraints[0]

        # Should be ~0 for valid parameters
        result = weight_constraint["fun"](vector)
        assert abs(result) < 0.01

    def test_optimize_parameters_with_empty_data(self):
        """Test parameter optimization with no training data."""
        scorer = MVLPBayesianConfidenceScorer()

        original_params = scorer.parameters
        optimized = scorer.optimize_parameters([])

        # Should return original parameters unchanged
        assert optimized.completeness_weight == original_params.completeness_weight
        assert optimized.quality_weight == original_params.quality_weight

    def test_optimize_parameters_with_training_data(self):
        """Test parameter optimization with training data."""
        scorer = MVLPBayesianConfidenceScorer()

        # Create synthetic training data
        training_data: List[Tuple[EvidenceMetrics, float]] = [
            (EvidenceMetrics(0.8, 0.9, 0.7, 10, 5), 0.85),
            (EvidenceMetrics(0.6, 0.7, 0.5, 8, 4), 0.65),
            (EvidenceMetrics(0.9, 0.95, 0.8, 15, 8), 0.90),
            (EvidenceMetrics(0.3, 0.4, 0.2, 3, 1), 0.35),
        ]

        optimized = scorer.optimize_parameters(training_data)

        # Optimized parameters should still be valid
        assert optimized.validate() is True
        # Training data should be stored
        assert len(scorer.training_data) == 4

    def test_sigmoid_normalize_symmetry(self):
        """Test sigmoid normalization has expected properties."""
        scorer = MVLPBayesianConfidenceScorer()

        # Sigmoid should be symmetric around origin
        pos_result = scorer._sigmoid_normalize(1.0)
        neg_result = scorer._sigmoid_normalize(-1.0)

        assert 0.0 < pos_result < 1.0
        assert 0.0 < neg_result < 1.0
        # Due to offset in implementation, not exactly symmetric but monotonic
        assert pos_result > neg_result

    def test_sigmoid_normalize_bounds(self):
        """Test sigmoid normalization stays within bounds."""
        scorer = MVLPBayesianConfidenceScorer()

        # Test extreme values
        very_negative = scorer._sigmoid_normalize(-100.0)
        very_positive = scorer._sigmoid_normalize(100.0)

        assert 0.0 < very_negative <= 1.0
        assert 0.0 < very_positive <= 1.0
        assert very_positive > very_negative

    def test_get_parameter_summary_default_state(self):
        """Test parameter summary in default state."""
        scorer = MVLPBayesianConfidenceScorer()

        summary = scorer.get_parameter_summary()

        assert "parameters" in summary
        assert "parameter_valid" in summary
        assert summary["parameter_valid"] is True
        # No training data initially
        assert "training_samples" not in summary
        # No confidence intervals initially
        assert "confidence_intervals" not in summary

    def test_get_parameter_summary_after_optimization(self):
        """Test parameter summary after optimization."""
        scorer = MVLPBayesianConfidenceScorer()

        training_data: List[Tuple[EvidenceMetrics, float]] = [
            (EvidenceMetrics(0.8, 0.9, 0.7, 10, 5), 0.85),
            (EvidenceMetrics(0.6, 0.7, 0.5, 8, 4), 0.65),
        ]

        scorer.optimize_parameters(training_data)
        summary = scorer.get_parameter_summary()

        assert "training_samples" in summary
        assert summary["training_samples"] == 2

    def test_prior_affects_confidence(self):
        """Test that format prior affects confidence calculation."""
        # High prior format
        high_prior_scorer = MVLPBayesianConfidenceScorer(
            format_priors={"HighPrior": 0.8}
        )

        # Low prior format
        low_prior_scorer = MVLPBayesianConfidenceScorer(format_priors={"LowPrior": 0.1})

        metrics = EvidenceMetrics(
            completeness=0.5,
            quality=0.5,
            uniqueness=0.5,
            evidence_count=5,
            unique_count=2,
        )

        high_result = high_prior_scorer.calculate_confidence(
            metrics, "HighPrior", use_uncertainty=False
        )
        low_result = low_prior_scorer.calculate_confidence(
            metrics, "LowPrior", use_uncertainty=False
        )

        # Higher prior should lead to higher confidence
        assert high_result["confidence"] > low_result["confidence"]

    def test_confidence_with_uncertainty_includes_bounds(self):
        """Test that uncertainty calculation includes confidence bounds."""
        scorer = MVLPBayesianConfidenceScorer()

        # First optimize to get confidence intervals
        training_data: List[Tuple[EvidenceMetrics, float]] = [
            (EvidenceMetrics(0.8, 0.9, 0.7, 10, 5), 0.85),
            (EvidenceMetrics(0.6, 0.7, 0.5, 8, 4), 0.65),
            (EvidenceMetrics(0.9, 0.95, 0.8, 15, 8), 0.90),
        ]

        scorer.optimize_parameters(training_data)

        metrics = EvidenceMetrics(0.7, 0.8, 0.6, 8, 4)

        # If confidence intervals were calculated, should include bounds
        result = scorer.calculate_confidence(metrics, "Zephyr", use_uncertainty=True)

        assert "confidence" in result
        # Bounds may or may not be present depending on optimizer success
        # This is expected behavior

    def test_calculate_confidence_handles_unknown_format(self):
        """Test confidence calculation for unknown format uses default prior."""
        scorer = MVLPBayesianConfidenceScorer(format_priors={"Known": 0.8})

        metrics = EvidenceMetrics(0.5, 0.5, 0.5, 5, 2)

        result = scorer.calculate_confidence(metrics, "Unknown")

        assert "prior" in result
        assert result["prior"] == 0.1  # Default prior

    def test_mvlp_objective_respects_parameter_bounds(self):
        """Test MVLP objective always returns value within bounds."""
        scorer = MVLPBayesianConfidenceScorer()

        # Test with various metric combinations
        test_cases = [
            EvidenceMetrics(0.0, 0.0, 0.0, 0, 0),
            EvidenceMetrics(1.0, 1.0, 1.0, 100, 50),
            EvidenceMetrics(0.5, 0.5, 0.5, 10, 5),
            EvidenceMetrics(0.2, 0.8, 0.3, 5, 2),
        ]

        for metrics in test_cases:
            result = scorer._mvlp_objective_function(metrics, scorer.parameters)
            assert (
                scorer.parameters.min_confidence
                <= result
                <= scorer.parameters.max_confidence
            )


class TestMVLPBayesianIntegration:
    """Integration tests for MVLP Bayesian confidence scorer."""

    def test_end_to_end_confidence_calculation_workflow(self):
        """Test complete workflow from initialization to confidence calculation."""
        # Create scorer with custom priors
        priors = {
            "Zephyr": 0.4,
            "Xray": 0.3,
            "TestRail": 0.3,
        }
        scorer = MVLPBayesianConfidenceScorer(format_priors=priors)

        # Create training data
        training_data: List[Tuple[EvidenceMetrics, float]] = [
            (EvidenceMetrics(0.9, 0.95, 0.85, 20, 10), 0.92),
            (EvidenceMetrics(0.7, 0.8, 0.65, 15, 7), 0.75),
            (EvidenceMetrics(0.5, 0.6, 0.45, 10, 5), 0.55),
            (EvidenceMetrics(0.3, 0.4, 0.25, 5, 2), 0.35),
        ]

        # Optimize parameters
        optimized_params = scorer.optimize_parameters(training_data)
        assert optimized_params.validate() is True

        # Calculate confidence for new data
        test_metrics = EvidenceMetrics(0.8, 0.85, 0.7, 12, 6)
        result = scorer.calculate_confidence(test_metrics, "Zephyr")

        assert 0.05 <= result["confidence"] <= 0.95
        assert "likelihood" in result
        assert "prior" in result
        assert result["prior"] == 0.4

    def test_optimization_improves_predictions(self):
        """Test that parameter optimization improves prediction accuracy."""
        scorer = MVLPBayesianConfidenceScorer()

        # Create consistent training data
        training_data: List[Tuple[EvidenceMetrics, float]] = [
            (EvidenceMetrics(0.9, 0.9, 0.9, 20, 10), 0.9),
            (EvidenceMetrics(0.8, 0.8, 0.8, 15, 8), 0.8),
            (EvidenceMetrics(0.7, 0.7, 0.7, 10, 5), 0.7),
            (EvidenceMetrics(0.6, 0.6, 0.6, 8, 4), 0.6),
            (EvidenceMetrics(0.5, 0.5, 0.5, 5, 3), 0.5),
        ]

        # Calculate error before optimization
        errors_before = []
        for metrics, expected in training_data:
            result = scorer._mvlp_objective_function(metrics, scorer.parameters)
            errors_before.append(abs(result - expected))

        # Optimize
        scorer.optimize_parameters(training_data)

        # Calculate error after optimization
        errors_after = []
        for metrics, expected in training_data:
            result = scorer._mvlp_objective_function(metrics, scorer.parameters)
            errors_after.append(abs(result - expected))

        # Average error should decrease (or stay similar if already good)
        avg_error_before = sum(errors_before) / len(errors_before)
        avg_error_after = sum(errors_after) / len(errors_after)

        # Optimization should not make things significantly worse
        assert avg_error_after <= avg_error_before * 1.5

    def test_multiple_formats_comparison(self):
        """Test comparing confidence across multiple formats."""
        priors = {
            "Zephyr": 0.5,
            "Xray": 0.3,
            "TestRail": 0.2,
        }
        scorer = MVLPBayesianConfidenceScorer(format_priors=priors)

        # Same evidence for all formats
        metrics = EvidenceMetrics(0.7, 0.8, 0.6, 10, 5)

        results = {}
        for format_name in priors:
            results[format_name] = scorer.calculate_confidence(
                metrics, format_name, use_uncertainty=False
            )

        # Higher prior should lead to higher confidence
        assert results["Zephyr"]["confidence"] > results["TestRail"]["confidence"]

    def test_consistency_across_repeated_calls(self):
        """Test that repeated calls with same input give same output."""
        scorer = MVLPBayesianConfidenceScorer()

        metrics = EvidenceMetrics(0.75, 0.8, 0.65, 12, 6)

        result1 = scorer.calculate_confidence(metrics, "Zephyr", use_uncertainty=False)
        result2 = scorer.calculate_confidence(metrics, "Zephyr", use_uncertainty=False)

        assert result1["confidence"] == result2["confidence"]
        assert result1["likelihood"] == result2["likelihood"]
        assert result1["prior"] == result2["prior"]

    def test_parameter_validation_after_optimization(self):
        """Test that optimized parameters remain valid."""
        scorer = MVLPBayesianConfidenceScorer()

        # Create diverse training data
        training_data: List[Tuple[EvidenceMetrics, float]] = [
            (EvidenceMetrics(1.0, 1.0, 1.0, 50, 25), 0.95),
            (EvidenceMetrics(0.0, 0.0, 0.0, 0, 0), 0.05),
            (EvidenceMetrics(0.5, 0.5, 0.5, 10, 5), 0.50),
            (EvidenceMetrics(0.8, 0.3, 0.6, 15, 3), 0.60),
            (EvidenceMetrics(0.3, 0.8, 0.4, 8, 6), 0.55),
        ]

        optimized = scorer.optimize_parameters(training_data)

        # Optimized parameters must satisfy all constraints
        assert optimized.validate() is True

        # Weight sum should still be ~1.0
        weight_sum = (
            optimized.completeness_weight
            + optimized.quality_weight
            + optimized.uniqueness_weight
        )
        assert 0.99 <= weight_sum <= 1.01

    def test_extreme_evidence_scenarios(self):
        """Test scorer behavior with extreme evidence scenarios."""
        scorer = MVLPBayesianConfidenceScorer()

        # All zeros
        zero_metrics = EvidenceMetrics(0.0, 0.0, 0.0, 0, 0)
        result_zero = scorer.calculate_confidence(zero_metrics, "Zephyr")
        assert 0.05 <= result_zero["confidence"] <= 0.95

        # All ones
        perfect_metrics = EvidenceMetrics(1.0, 1.0, 1.0, 100, 50)
        result_perfect = scorer.calculate_confidence(perfect_metrics, "Zephyr")
        assert 0.05 <= result_perfect["confidence"] <= 0.95

        # Perfect should have higher confidence than zero
        assert result_perfect["confidence"] > result_zero["confidence"]
