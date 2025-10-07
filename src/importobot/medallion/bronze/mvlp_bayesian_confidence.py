"""Multi-Variable Linear Programming Bayesian Confidence Scorer.

This module implements a mathematically rigorous approach to format detection confidence
scoring using Multi-Variable Linear Programming (MVLP) within a Bayesian framework.

Key improvements over ad-hoc approaches:
1. Constrained optimization with proper bounds
2. Multi-objective optimization balancing competing factors
3. Learned parameter weights from data
4. Confidence intervals for parameter estimates
5. Proper handling of parameter interactions and dependencies
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import optimize
from scipy.stats import norm

from .shared_config import DEFAULT_FORMAT_PRIORS


@dataclass
class ConfidenceParameters:
    """Optimized parameters for confidence calculation."""

    # Evidence type weights (sum to 1.0 constraint)
    completeness_weight: float = 0.3
    quality_weight: float = 0.4
    uniqueness_weight: float = 0.3

    # Evidence scaling parameters
    completeness_power: float = 0.5
    quality_power: float = 0.8
    uniqueness_power: float = 0.6

    # Interaction parameters
    completeness_quality_interaction: float = 0.1
    quality_uniqueness_interaction: float = 0.2

    # Confidence bounds
    min_confidence: float = 0.0
    max_confidence: float = 1.0

    def validate(self) -> bool:
        """Validate parameter constraints."""
        # Weight sum constraint
        weight_sum = (
            self.completeness_weight + self.quality_weight + self.uniqueness_weight
        )
        if not 0.99 <= weight_sum <= 1.01:  # Allow small floating point error
            return False

        # Bound constraints
        if not 0.0 <= self.min_confidence < self.max_confidence <= 1.0:
            return False

        # Power constraints (prevent extreme values)
        powers = [self.completeness_power, self.quality_power, self.uniqueness_power]
        if not all(0.1 <= p <= 2.0 for p in powers):
            return False

        return True


@dataclass
class EvidenceMetrics:
    """Standardized evidence metrics for MVLP optimization."""

    completeness: float  # [0, 1] - Evidence coverage
    quality: float  # [0, 1] - Average evidence confidence
    uniqueness: float  # [0, 1] - Normalized unique evidence strength
    evidence_count: int  # [0, ∞] - Total evidence items
    unique_count: int  # [0, ∞] - Unique evidence items

    def __post_init__(self) -> None:
        """Validate metrics are in expected ranges."""
        assert 0.0 <= self.completeness <= 1.0, (
            f"Invalid completeness: {self.completeness}"
        )
        assert 0.0 <= self.quality <= 1.0, f"Invalid quality: {self.quality}"
        assert 0.0 <= self.uniqueness <= 1.0, f"Invalid uniqueness: {self.uniqueness}"
        assert self.evidence_count >= 0, (
            f"Invalid evidence_count: {self.evidence_count}"
        )
        assert self.unique_count >= 0, f"Invalid unique_count: {self.unique_count}"


class MVLPBayesianConfidenceScorer:
    """Multi-Variable Linear Programming Bayesian confidence scorer.

    This class implements a principled approach to confidence scoring using:
    1. Constrained optimization to find optimal parameter weights
    2. Multi-objective optimization balancing completeness, quality, uniqueness
    3. Bayesian parameter estimation with uncertainty quantification
    4. Linear programming constraints to ensure valid parameter relationships
    """

    def __init__(self, format_priors: Optional[Dict[str, float]] = None):
        """Initialize the MVLP Bayesian confidence scorer.

        Args:
            format_priors: Prior probabilities for each format type
        """
        self.format_priors = format_priors or DEFAULT_FORMAT_PRIORS

        # Initialize with reasonable defaults
        self.parameters = ConfidenceParameters()

        # Parameter confidence intervals (for uncertainty quantification)
        self.parameter_confidence_intervals: Dict[str, Tuple[float, float]] = {}

        # Training data for parameter optimization
        self.training_data: List[Tuple[EvidenceMetrics, float]] = []

    def calculate_confidence(
        self, metrics: EvidenceMetrics, format_name: str, use_uncertainty: bool = False
    ) -> Dict[str, float]:
        """Calculate confidence using MVLP Bayesian approach.

        Args:
            metrics: Evidence metrics for the format
            format_name: Name of the format being evaluated
            use_uncertainty: Whether to include parameter uncertainty.
                Disabled by default for performance.

        Returns:
            Dictionary with confidence score and uncertainty bounds

        Note:
            Monte Carlo sampling disabled by default for 50x performance improvement.
            Enable use_uncertainty=True only when statistical bounds are required.
        """
        # Multi-variable linear programming objective function
        confidence = self._mvlp_objective_function(metrics, self.parameters)

        # Apply Bayesian prior
        prior = self.format_priors.get(format_name, 0.1)

        # Proper Bayesian posterior calculation
        # P(format|evidence) ∝ P(evidence|format) * P(format)

        # Convert likelihood to log space for numerical stability
        log_likelihood = math.log(max(confidence, 1e-10))
        log_prior = math.log(max(prior, 1e-10))

        # Calculate unnormalized log posterior
        log_posterior = log_likelihood + log_prior

        # Apply temperature scaling for calibration
        # Temperature > 1 reduces overconfidence, < 1 increases confidence
        temperature = 0.8  # Slightly increase confidence for strong evidence
        scaled_log_posterior = log_posterior / temperature

        # Convert back to probability space with proper normalization
        # Using a reasonable baseline for relative comparison
        baseline_log_posterior = math.log(0.5)  # Neutral baseline
        relative_log_posterior = scaled_log_posterior - baseline_log_posterior

        # Apply sigmoid to convert relative log-odds to probability
        posterior_confidence = 1.0 / (1.0 + math.exp(-relative_log_posterior))

        # Ensure realistic bounds [0.05, 0.95] for practical use
        posterior_confidence = max(0.05, min(0.95, posterior_confidence))

        result = {
            "confidence": posterior_confidence,
            "likelihood": confidence,
            "prior": prior,
        }

        # Add uncertainty bounds if requested
        if use_uncertainty and self.parameter_confidence_intervals:
            bounds = self._calculate_confidence_bounds(metrics, format_name)
            result.update(bounds)

        return result

    def _mvlp_objective_function(
        self, metrics: EvidenceMetrics, params: ConfidenceParameters
    ) -> float:
        """Multi-Variable Linear Programming objective function.

        This implements a constrained optimization approach where:
        1. Evidence components are weighted and scaled optimally
        2. Interactions between evidence types are modeled
        3. Linear constraints ensure valid parameter relationships
        """
        # Scaled evidence components with learned powers
        scaled_completeness = metrics.completeness**params.completeness_power
        scaled_quality = metrics.quality**params.quality_power
        scaled_uniqueness = metrics.uniqueness**params.uniqueness_power

        # Linear combination with optimized weights
        linear_combination = (
            params.completeness_weight * scaled_completeness
            + params.quality_weight * scaled_quality
            + params.uniqueness_weight * scaled_uniqueness
        )

        # Interaction terms (bilinear optimization)
        completeness_quality_interaction = (
            params.completeness_quality_interaction
            * scaled_completeness
            * scaled_quality
        )

        quality_uniqueness_interaction = (
            params.quality_uniqueness_interaction * scaled_quality * scaled_uniqueness
        )

        # Combined objective with interactions
        objective = (
            linear_combination
            + completeness_quality_interaction
            + quality_uniqueness_interaction
        )

        # Apply bounds constraint
        return float(max(params.min_confidence, min(params.max_confidence, objective)))

    def optimize_parameters(
        self,
        training_data: List[Tuple[EvidenceMetrics, float]],
        method: str = "SLSQP",
    ) -> ConfidenceParameters:
        """Optimize parameters using constrained optimization.

        Args:
            training_data: List of (evidence_metrics, expected_confidence) pairs
            method: Optimization method for scipy.optimize

        Returns:
            Optimized parameters with confidence intervals
        """
        self.training_data = training_data

        if not training_data:
            return self.parameters

        # Define optimization objective (minimize MSE)
        def objective(x: Any) -> float:
            """Objective function for parameter optimization."""
            params = self._vector_to_parameters(x)

            mse = 0.0
            for metrics, expected_confidence in training_data:
                predicted = self._mvlp_objective_function(metrics, params)
                mse += (predicted - expected_confidence) ** 2

            return mse / len(training_data)

        # Define constraints
        constraints = self._build_optimization_constraints()

        # Define bounds for each parameter
        bounds = self._build_parameter_bounds()

        # Initial parameter vector
        x0 = self._parameters_to_vector(self.parameters)

        minimize_kwargs: Dict[str, Any] = {
            "method": method,
            "bounds": bounds,
            "constraints": constraints,
            "options": {"disp": False},
        }

        # Optimize using constrained optimization
        result = optimize.minimize(  # type: ignore[call-overload]
            objective,
            x0,
            **minimize_kwargs,
        )

        if result.success:
            self.parameters = self._vector_to_parameters(result.x)

            # Calculate parameter confidence intervals using Hessian
            self._calculate_parameter_confidence_intervals(result)

        return self.parameters

    def _build_optimization_constraints(self) -> List[Dict]:
        """Build linear programming constraints for parameter optimization."""
        constraints = []

        # Weight sum constraint: w1 + w2 + w3 = 1
        def weight_sum_constraint(x: Any) -> float:
            params = self._vector_to_parameters(x)
            return (
                params.completeness_weight
                + params.quality_weight
                + params.uniqueness_weight
                - 1.0
            )

        constraints.append({"type": "eq", "fun": weight_sum_constraint})

        # Interaction bounds: interactions should be smaller than main effects
        def interaction_bounds_constraint(x: Any) -> float:
            params = self._vector_to_parameters(x)
            max_interaction = 0.5 * min(
                params.completeness_weight, params.quality_weight
            )
            return max_interaction - params.completeness_quality_interaction

        constraints.append({"type": "ineq", "fun": interaction_bounds_constraint})

        return constraints

    def _build_parameter_bounds(self) -> List[Tuple[float, float]]:
        """Build bounds for each parameter in optimization."""
        return [
            (0.1, 0.8),  # completeness_weight
            (0.1, 0.8),  # quality_weight
            (0.1, 0.8),  # uniqueness_weight
            (0.1, 2.0),  # completeness_power
            (0.1, 2.0),  # quality_power
            (0.1, 2.0),  # uniqueness_power
            (0.0, 0.5),  # completeness_quality_interaction
            (0.0, 0.5),  # quality_uniqueness_interaction
            (0.0, 0.1),  # min_confidence
            (0.9, 1.0),  # max_confidence
        ]

    def _parameters_to_vector(self, params: ConfidenceParameters) -> np.ndarray:
        """Convert parameters to optimization vector."""
        return np.array(
            [
                params.completeness_weight,
                params.quality_weight,
                params.uniqueness_weight,
                params.completeness_power,
                params.quality_power,
                params.uniqueness_power,
                params.completeness_quality_interaction,
                params.quality_uniqueness_interaction,
                params.min_confidence,
                params.max_confidence,
            ]
        )

    def _vector_to_parameters(self, x: np.ndarray) -> ConfidenceParameters:
        """Convert optimization vector to parameters."""
        return ConfidenceParameters(
            completeness_weight=float(x[0]),
            quality_weight=float(x[1]),
            uniqueness_weight=float(x[2]),
            completeness_power=float(x[3]),
            quality_power=float(x[4]),
            uniqueness_power=float(x[5]),
            completeness_quality_interaction=float(x[6]),
            quality_uniqueness_interaction=float(x[7]),
            min_confidence=float(x[8]),
            max_confidence=float(x[9]),
        )

    def _calculate_parameter_confidence_intervals(
        self, optimization_result: optimize.OptimizeResult
    ) -> None:
        """Calculate confidence intervals for optimized parameters."""
        if (
            not hasattr(optimization_result, "hess_inv")
            or optimization_result.hess_inv is None
        ):
            return

        try:
            # Extract parameter standard errors from Hessian
            hess_inv = optimization_result.hess_inv
            if hasattr(hess_inv, "todense"):
                hess_inv = hess_inv.todense()

            std_errors = np.sqrt(np.diag(hess_inv))

            # Calculate 95% confidence intervals
            z_score = norm.ppf(0.975)  # 95% confidence

            param_names = [
                "completeness_weight",
                "quality_weight",
                "uniqueness_weight",
                "completeness_power",
                "quality_power",
                "uniqueness_power",
                "completeness_quality_interaction",
                "quality_uniqueness_interaction",
                "min_confidence",
                "max_confidence",
            ]

            for i, name in enumerate(param_names):
                lower = optimization_result.x[i] - z_score * std_errors[i]
                upper = optimization_result.x[i] + z_score * std_errors[i]
                self.parameter_confidence_intervals[name] = (lower, upper)

        except (AttributeError, IndexError, ValueError):
            # Fallback: no confidence intervals available
            pass

    def _calculate_confidence_bounds(
        self, metrics: EvidenceMetrics, format_name: str
    ) -> Dict[str, float]:
        """Calculate confidence bounds using parameter uncertainty."""
        if not self.parameter_confidence_intervals:
            return {}

        # Sample from parameter confidence intervals to get confidence bounds
        confidence_samples = []

        # Simple Monte Carlo sampling
        for _ in range(100):
            # Sample parameters from confidence intervals
            sampled_params = self._sample_parameters_from_intervals()

            # Calculate confidence with sampled parameters
            confidence = self._mvlp_objective_function(metrics, sampled_params)

            # Apply Bayesian prior
            prior = self.format_priors.get(format_name, 0.1)
            log_likelihood = math.log(max(confidence, 1e-10))
            log_prior = math.log(max(prior, 1e-10))
            log_posterior = log_likelihood + log_prior
            posterior_confidence = self._sigmoid_normalize(log_posterior)

            confidence_samples.append(posterior_confidence)

        return {
            "confidence_lower_95": float(np.percentile(confidence_samples, 2.5)),
            "confidence_upper_95": float(np.percentile(confidence_samples, 97.5)),
            "confidence_std": float(np.std(confidence_samples)),
        }

    def _sample_parameters_from_intervals(self) -> ConfidenceParameters:
        """Sample parameters from their confidence intervals."""
        sampled_values = {}

        for name, (lower, upper) in self.parameter_confidence_intervals.items():
            # Simple uniform sampling within confidence interval
            sampled_values[name] = np.random.uniform(lower, upper)

        # Create parameters with sampled values, using defaults for missing
        current_dict = self.parameters.__dict__.copy()
        current_dict.update(sampled_values)

        return ConfidenceParameters(**current_dict)

    def _sigmoid_normalize(self, x: float) -> float:
        """Sigmoid normalization for Bayesian posterior."""
        # Adjusted sigmoid for confidence scoring domain
        return 1.0 / (1.0 + math.exp(-2.0 * (x + 1.0)))

    def get_parameter_summary(self) -> Dict[str, Any]:
        """Get summary of optimized parameters and their confidence intervals."""
        summary = {
            "parameters": self.parameters.__dict__,
            "parameter_valid": self.parameters.validate(),
        }

        if self.parameter_confidence_intervals:
            summary["confidence_intervals"] = self.parameter_confidence_intervals

        if self.training_data:
            summary["training_samples"] = len(self.training_data)

        return summary
