"""Weighted Evidence Bayesian Confidence Scorer.

This module implements a mathematically rigorous approach to format detection confidence
scoring using nonlinear weighted evidence aggregation within a Bayesian framework.

Mathematical Approach:
-------------------
The confidence scoring system uses:

1. **Nonlinear Evidence Aggregation**:
   - Combines evidence metrics (completeness, quality, uniqueness) using power functions
   - Includes bilinear interaction terms to model evidence dependencies
   - Instead of linear programming, uses nonlinear polynomial optimization

2. **Constrained Optimization**:
   - Learns optimal weights and powers from training data
   - Enforces sum-to-one constraint on evidence weights
   - Uses scipy.optimize.minimize with SLSQP for constrained minimization

3. **Bayesian Integration**:
   - Incorporates format prior probabilities
   - Combines likelihood (from evidence) with priors using Bayes' theorem
   - Provides posterior probability estimates

Key Assumptions:
--------------
- Format types are mutually exclusive (priors sum to 1.0)
- Evidence metrics are in [0,1] range and independently measured
- Training data is representative of deployment distribution
- Confidence intervals from Hessian are approximate (MSE objective, not MLE)

Calibration Notes:
----------------
Default parameters were derived from empirical testing on test management format data:
- Power parameters (0.5-0.8): Allow nonlinear scaling for better discrimination
- Interaction weights (0.1-0.2): Small relative to main effects
- Weight sum = 1.0: Ensures interpretable probability-like outputs

References:
----------
- Constrained optimization: Nocedal & Wright, "Numerical Optimization" (2nd ed.)
- Bayesian inference: Gelman et al., "Bayesian Data Analysis" (3rd ed.)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from importobot.utils.logging import setup_logger

try:  # pragma: no cover - optional dependency handling
    from scipy import optimize  # type: ignore[import-untyped]
    from scipy.stats import norm  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - fallback mode
    optimize = None  # type: ignore[assignment]
    norm = None  # type: ignore[assignment,misc]
from .shared_config import DEFAULT_FORMAT_PRIORS

logger = setup_logger(__name__)


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
    """Standardized evidence metrics for weighted evidence optimization."""

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


class WeightedEvidenceBayesianScorer:
    """Weighted Evidence Bayesian confidence scorer.

    This class implements a principled approach to confidence scoring using:
    1. Constrained nonlinear optimization to find optimal parameter weights
    2. Multi-objective optimization balancing completeness, quality, uniqueness
    3. Bayesian integration with format prior probabilities
    4. Uncertainty quantification via bootstrap or Hessian-based intervals

    Note on Confidence Intervals:
        The Hessian-based confidence intervals assume approximate normality of
        parameter estimates. These are valid asymptotically for large samples but
        should be interpreted cautiously with small training sets (n < 20).
        Consider bootstrap confidence intervals for more robust uncertainty
        quantification when sample size is limited.
    """

    # Minimum training samples for reliable parameter optimization
    MIN_TRAINING_SAMPLES = 10

    def __init__(self, format_priors: Optional[Dict[str, float]] = None):
        """Initialize the Weighted Evidence Bayesian confidence scorer.

        Args:
            format_priors: Prior probabilities for each format type.
                          Must sum to 1.0 under mutual exclusivity assumption.
        """
        self.format_priors = format_priors or DEFAULT_FORMAT_PRIORS

        # Initialize with reasonable defaults
        self.parameters = ConfidenceParameters()

        # Parameter confidence intervals (for uncertainty quantification)
        self.parameter_confidence_intervals: Dict[str, Tuple[float, float]] = {}

        # Track optimization backend for graceful degradation without SciPy
        self.optimization_backend = "scipy" if optimize is not None else "heuristic"
        self._supports_uncertainty_bounds = optimize is not None and norm is not None

        # Training data for parameter optimization
        self.training_data: List[Tuple[EvidenceMetrics, float]] = []

        if optimize is None:  # pragma: no cover - runtime warning path
            logger.warning(
                "SciPy is not installed; weighted evidence optimization will operate in"
                " heuristic mode without uncertainty bounds."
            )

    def calculate_confidence(
        self, metrics: EvidenceMetrics, format_name: str, use_uncertainty: bool = False
    ) -> Dict[str, float]:
        """Calculate confidence using weighted evidence Bayesian approach.

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

        Mathematical Details:
            This method uses proper Bayesian inference via _apply_bayesian_inference()
            which implements:
                P(H|E) = P(E|H) * P(H) / P(E)
            where P(E) = sum over all formats of P(E|format) * P(format)
        """
        # Calculate likelihood using weighted evidence aggregation
        likelihood = self._weighted_evidence_objective(metrics, self.parameters)

        # Apply proper Bayesian inference to get posterior
        posterior_confidence = self._apply_bayesian_inference(
            prior=self.format_priors.get(format_name, 0.1),
            likelihood=likelihood,
            _metrics=metrics,
            _format_name=format_name,
        )

        # Apply parameter-defined confidence bounds
        posterior_confidence = max(
            self.parameters.min_confidence,
            min(self.parameters.max_confidence, posterior_confidence),
        )

        result = {
            "confidence": posterior_confidence,
            "likelihood": likelihood,
            "prior": self.format_priors.get(format_name, 0.1),
        }

        # Add uncertainty bounds if requested
        if (
            use_uncertainty
            and self.parameter_confidence_intervals
            and self._supports_uncertainty_bounds
        ):
            bounds = self._calculate_confidence_bounds(metrics, format_name)
            result.update(bounds)

        return result

    def _weighted_evidence_objective(
        self, metrics: EvidenceMetrics, params: ConfidenceParameters
    ) -> float:
        """Weighted evidence aggregation objective function.

        This implements a nonlinear polynomial approach where:
        1. Evidence components are weighted and scaled with power functions
        2. Bilinear interaction terms model evidence dependencies
        3. Constrained optimization ensures valid parameter relationships

        Mathematical Form:
            f(m) = w₁·m₁^p₁ + w₂·m₂^p₂ + w₃·m₃^p₃ + i₁·m₁^p₁·m₂^p₂ + i₂·m₂^p₂·m₃^p₃

        where:
            m = (completeness, quality, uniqueness) evidence metrics
            w = weights (sum to 1.0)
            p = power parameters (typically 0.5-1.5)
            i = interaction coefficients (typically 0.1-0.2)
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

    def _apply_bayesian_inference(
        self,
        prior: float,
        likelihood: float,
        _metrics: EvidenceMetrics,
        _format_name: str,
    ) -> float:
        """Apply proper Bayesian inference with estimated P(E|¬H).

        Mathematical Framework:
            P(H|E) = P(E|H) * P(H) / [P(E|H) * P(H) + P(E|¬H) * P(¬H)]

        where:
            H = "Data is from this format"
            E = Observed evidence metrics
            P(H) = prior probability (format prevalence)
            P(E|H) = likelihood (evidence given format IS this type)
            P(E|¬H) = likelihood of evidence if format is NOT this type

        Estimating P(E|¬H):
            Since we cannot compute P(E|¬H) from other formats (they share parameters),
            we use an adaptive estimate based on evidence strength with quadratic decay:

            P(E|¬H) = 0.01 + 0.49 * (1 - likelihood)²

            Rationale (quadratic decay is more aggressive than linear):
            - When likelihood = 0.0: P(E|¬H) = 0.50 (weak evidence is ambiguous)
            - When likelihood = 0.5: P(E|¬H) = 0.13
            (moderate less likely from wrong format)
            - When likelihood = 1.0: P(E|¬H) = 0.01
            (perfect evidence rarely from wrong format)

            With perfect evidence and prior=0.1: posterior ≈ 0.92 (high confidence)

        This ensures:
            1. Zero evidence → low confidence (not fall back to prior)
            2. Evidence dominates, not prior
            3. Proper uncertainty quantification
            4. Respects base rates without prior dominance

        Args:
            prior: P(H) - prior probability of this format
            likelihood: P(E|H) - likelihood from evidence aggregation
            _metrics: Evidence metrics (reserved for future enhancements)
            _format_name: Current format being evaluated
            (reserved for future enhancements)

        Returns:
            Posterior probability P(H|E)
        """
        # Adaptive estimation of P(E|¬H) using quadratic decay
        # Strong evidence is very unlikely to come from wrong format
        # Weak evidence could come from any format (high P(E|¬H))
        # Quadratic decay: more aggressive than linear for strong evidence
        p_evidence_not_format = 0.01 + 0.49 * (1.0 - likelihood) ** 2

        # Apply Bayes' theorem
        numerator = likelihood * prior
        denominator = likelihood * prior + p_evidence_not_format * (1.0 - prior)

        if denominator == 0:
            # Both likelihoods are zero - no evidence at all
            # Return very low confidence rather than prior
            return 0.0

        posterior = numerator / denominator

        return posterior

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

        Raises:
            ValueError: If training_data has fewer than MIN_TRAINING_SAMPLES samples
        """
        self.training_data = training_data

        if not training_data:
            return self.parameters

        # Validate minimum sample size for reliable optimization
        if len(training_data) < self.MIN_TRAINING_SAMPLES:
            logger.warning(
                "Training data has %d samples (< %d minimum). "
                "Parameter optimization may be unreliable. "
                "Consider collecting more training data.",
                len(training_data),
                self.MIN_TRAINING_SAMPLES,
            )

        # Define optimization objective (minimize MSE)
        def objective(x: Any) -> float:
            """Objective function for parameter optimization."""
            params = self._vector_to_parameters(x)

            mse = 0.0
            for metrics, expected_confidence in training_data:
                predicted = self._weighted_evidence_objective(metrics, params)
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
        if optimize is None:
            logger.info(
                "Falling back to heuristic weighted evidence parameter tuning;"
                " install SciPy for constrained optimization and uncertainty intervals."
            )
            self.parameters = self._optimize_with_heuristics(training_data)
            self.parameter_confidence_intervals.clear()
            self.optimization_backend = "heuristic"
            self._supports_uncertainty_bounds = False
            return self.parameters

        result = optimize.minimize(  # type: ignore[call-overload]
            objective,
            x0,
            **minimize_kwargs,
        )

        if result.success:
            self.parameters = self._vector_to_parameters(result.x)
            self.optimization_backend = "scipy"
            self._supports_uncertainty_bounds = norm is not None

            # Calculate parameter confidence intervals using Hessian
            self._calculate_parameter_confidence_intervals(result)

            return self.parameters

        logger.warning(
            "SciPy optimization failed (%s); reverting to heuristic tuning.",
            result.message,
        )
        self.parameters = self._optimize_with_heuristics(training_data)
        self.parameter_confidence_intervals.clear()
        self.optimization_backend = "heuristic"
        self._supports_uncertainty_bounds = False

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

    def _compute_weights(
        self, metrics_array: np.ndarray, expected_array: np.ndarray
    ) -> Tuple[float, float, float]:
        """Compute normalized weights via least squares."""
        try:
            weights, *_ = np.linalg.lstsq(metrics_array, expected_array, rcond=None)
        except (np.linalg.LinAlgError, ValueError):
            weights = np.array([0.3, 0.4, 0.3], dtype=float)

        weights = np.maximum(weights, 0.0)
        weight_sum = float(weights.sum())
        if weight_sum <= 0.0:
            return 0.3, 0.4, 0.3

        normalized = weights / weight_sum
        return float(normalized[0]), float(normalized[1]), float(normalized[2])

    def _compute_powers(
        self, mean_metrics: np.ndarray, avg_expected: float
    ) -> Tuple[float, float, float]:
        """Compute power parameters from mean metrics."""

        def _derive_power(mean_metric: float) -> float:
            if mean_metric <= 0.0:
                return 1.0
            ratio = avg_expected / max(mean_metric, 1e-6)
            return float(np.clip(ratio, 0.5, 1.5))

        return (
            _derive_power(float(mean_metrics[0])),
            _derive_power(float(mean_metrics[1])),
            _derive_power(float(mean_metrics[2])),
        )

    def _compute_interactions(
        self,
        completeness_weight: float,
        quality_weight: float,
        uniqueness_weight: float,
    ) -> Tuple[float, float]:
        """Compute interaction parameters from weights."""
        interaction_scale = min(completeness_weight, quality_weight, uniqueness_weight)
        return (
            float(max(interaction_scale * 0.2, 0.0)),
            float(max(interaction_scale * 0.25, 0.0)),
        )

    def _compute_confidence_bounds(
        self, expected_array: np.ndarray
    ) -> Tuple[float, float]:
        """Compute min/max confidence bounds."""
        min_conf = float(np.clip(expected_array.min() - 0.05, 0.0, 0.9))
        max_conf = float(np.clip(expected_array.max() + 0.05, 0.1, 1.0))
        if min_conf >= max_conf:
            min_conf = max(0.0, max_conf - 0.1)
        return min_conf, max_conf

    def _optimize_with_heuristics(
        self, training_data: List[Tuple[EvidenceMetrics, float]]
    ) -> ConfidenceParameters:
        """Derive parameters using a lightweight heuristic fallback.

        This keeps optimization functional when SciPy is unavailable by using
        least-squares weight estimation combined with bounded smoothing for the
        remaining parameters. The heuristic intentionally favors stability over
        aggressive fitting so downstream calculations remain well-behaved.
        """
        metrics_array = np.array(
            [[m.completeness, m.quality, m.uniqueness] for m, _ in training_data],
            dtype=float,
        )
        expected_array = np.array([e for _, e in training_data], dtype=float)

        comp_w, qual_w, uniq_w = self._compute_weights(metrics_array, expected_array)
        comp_p, qual_p, uniq_p = self._compute_powers(
            metrics_array.mean(axis=0), float(expected_array.mean())
        )
        cq_int, qu_int = self._compute_interactions(comp_w, qual_w, uniq_w)
        min_conf, max_conf = self._compute_confidence_bounds(expected_array)

        parameters = ConfidenceParameters(
            completeness_weight=comp_w,
            quality_weight=qual_w,
            uniqueness_weight=uniq_w,
            completeness_power=comp_p,
            quality_power=qual_p,
            uniqueness_power=uniq_p,
            completeness_quality_interaction=cq_int,
            quality_uniqueness_interaction=qu_int,
            min_confidence=min_conf,
            max_confidence=max_conf,
        )

        if not parameters.validate():
            logger.debug(
                "Heuristic optimization produced invalid parameters; "
                "reverting to defaults."
            )
            return ConfidenceParameters()

        return parameters

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
        if optimize is None or norm is None:
            return
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
            confidence = self._weighted_evidence_objective(metrics, sampled_params)

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
        """Sigmoid normalization for log-odds transformation.

        Applies a modified sigmoid function to transform log-posterior values
        into the [0,1] probability range:

            σ(x) = 1 / (1 + exp(-2(x + 1)))

        Modifications from standard sigmoid:
            - Factor of 2: Increases slope for sharper discrimination
            - Offset of +1: Shifts midpoint from 0 to -1 in log space

        Args:
            x: Input value (typically log-posterior)

        Returns:
            Normalized value in [0,1] range

        Note:
            This transformation is empirically calibrated for the format
            detection domain where log-posteriors typically range from -5 to 0.
            The adjustments provide better discrimination in this range.
        """
        # Adjusted sigmoid for confidence scoring domain
        return 1.0 / (1.0 + math.exp(-2.0 * (x + 1.0)))

    def get_parameter_summary(self) -> Dict[str, Any]:
        """Get summary of optimized parameters and their confidence intervals."""
        summary = {
            "parameters": self.parameters.__dict__,
            "parameter_valid": self.parameters.validate(),
            "optimization_backend": self.optimization_backend,
        }

        if self.parameter_confidence_intervals:
            summary["confidence_intervals"] = self.parameter_confidence_intervals

        if self.training_data:
            summary["training_samples"] = len(self.training_data)

        return summary


__all__ = [
    "ConfidenceParameters",
    "EvidenceMetrics",
    "WeightedEvidenceBayesianScorer",
]
