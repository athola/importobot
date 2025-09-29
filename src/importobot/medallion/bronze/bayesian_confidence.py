"""
Proper Bayesian confidence scoring for format detection.

Based on research from:
- Bayesian scaling laws for in-context learning (arXiv:2410.16531)
- Evidence accumulation in Bayesian systems
- Preference learning with weighted parameters
- Uncertainty scaling in deep learning

This implementation addresses the mathematical issues in the previous approach:
1. Proper log-probability evidence accumulation
2. Bayesian evidence combination with independence considerations
3. Parameter scaling based on evidence type preferences
4. Normalization across competing format hypotheses
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .format_models import EvidenceWeight
from .shared_config import DEFAULT_EVIDENCE_PREFERENCES, DEFAULT_FORMAT_PRIORS


@dataclass
class BayesianEvidence:
    """Single piece of evidence with proper Bayesian representation."""

    source_type: str  # "required_key", "pattern_match", "structure_indicator"
    evidence_strength: EvidenceWeight
    likelihood_ratio: float  # P(evidence|format) / P(evidence|¬format)
    confidence: float  # Confidence in the evidence observation itself
    description: str = ""

    @property
    def log_bayes_factor(self) -> float:
        """Calculate log Bayes factor for this evidence."""
        # Adjust for observation confidence
        adjusted_lr = 1.0 + (self.likelihood_ratio - 1.0) * self.confidence
        return math.log(max(adjusted_lr, 1e-10))  # Avoid log(0)


@dataclass
class FormatHypothesis:
    """Bayesian representation of a format hypothesis."""

    format_name: str
    prior_log_prob: float
    evidence_items: List[BayesianEvidence]

    @property
    def log_posterior(self) -> float:
        """Calculate log posterior probability."""
        # Start with prior
        log_post = self.prior_log_prob

        # Add evidence using proper Bayesian accumulation
        # For independent evidence: log P(H|E1,E2,...) = log P(H) + Σ log BF_i
        total_log_bf = sum(
            evidence.log_bayes_factor for evidence in self.evidence_items
        )

        return log_post + total_log_bf

    @property
    def evidence_strength_distribution(self) -> Dict[EvidenceWeight, int]:
        """Count evidence by strength type."""
        counts: Dict[EvidenceWeight, int] = {}
        for weight in EvidenceWeight:
            counts[weight] = 0
        for evidence in self.evidence_items:
            counts[evidence.evidence_strength] += 1
        return counts


class BayesianFormatDetector:
    """
    Proper Bayesian format detection with evidence accumulation.

    Implements research-based approaches:
    - Log-probability evidence accumulation
    - Likelihood ratio calculations with parameter preferences
    - Proper normalization across hypotheses
    - Uncertainty quantification
    """

    def __init__(self) -> None:
        """Initialize Bayesian format detector with default priors."""
        self.hypotheses: Dict[str, FormatHypothesis] = {}

        # Prior probabilities based on format prevalence
        # These should sum to 1.0 across all possible formats
        self._format_priors = DEFAULT_FORMAT_PRIORS.copy()

        # Evidence type preferences based on research
        # Higher values indicate stronger preference for this evidence type
        self._evidence_preferences = DEFAULT_EVIDENCE_PREFERENCES.copy()

        # Likelihood ratio parameters for different evidence strengths
        # Based on research on Bayesian scaling with parameter preferences
        self._base_likelihood_ratios = {
            EvidenceWeight.UNIQUE: 50.0,  # Very strong evidence
            EvidenceWeight.STRONG: 10.0,  # Strong evidence
            EvidenceWeight.MODERATE: 4.0,  # Moderate evidence
            EvidenceWeight.WEAK: 2.0,  # Weak evidence
            EvidenceWeight.NONE: 1.0,  # No evidence
        }

    def initialize_hypothesis(self, format_name: str) -> None:
        """Initialize a format hypothesis with proper prior."""
        prior_prob = self._format_priors.get(format_name, 0.01)
        prior_log_prob = math.log(prior_prob)

        self.hypotheses[format_name] = FormatHypothesis(
            format_name=format_name, prior_log_prob=prior_log_prob, evidence_items=[]
        )

    def add_evidence(  # pylint: disable=too-many-positional-arguments
        self,
        format_name: str,
        evidence_type: str,
        evidence_strength: EvidenceWeight,
        observation_confidence: float = 1.0,
        description: str = "",
    ) -> None:
        """Add evidence using proper Bayesian likelihood ratios."""
        if format_name not in self.hypotheses:
            self.initialize_hypothesis(format_name)

        # Calculate likelihood ratio with parameter preferences
        base_lr = self._base_likelihood_ratios[evidence_strength]
        type_preference = self._evidence_preferences.get(evidence_type, 1.0)

        # Apply preference scaling based on research on weighted parameters
        likelihood_ratio = base_lr * type_preference

        evidence = BayesianEvidence(
            source_type=evidence_type,
            evidence_strength=evidence_strength,
            likelihood_ratio=likelihood_ratio,
            confidence=observation_confidence,
            description=description,
        )

        self.hypotheses[format_name].evidence_items.append(evidence)

    def calculate_posterior_probabilities(self) -> Dict[str, float]:
        """Calculate normalized posterior probabilities for all hypotheses."""
        if not self.hypotheses:
            return {}

        # Calculate log posteriors
        log_posteriors = {}
        for format_name, hypothesis in self.hypotheses.items():
            log_posteriors[format_name] = hypothesis.log_posterior

        # Normalize using log-sum-exp trick for numerical stability
        max_log_post = max(log_posteriors.values())

        # Convert to probabilities
        posteriors = {}
        log_sum = 0.0

        for format_name, log_post in log_posteriors.items():
            adjusted_log_post = log_post - max_log_post
            posteriors[format_name] = math.exp(adjusted_log_post)
            log_sum += posteriors[format_name]

        # Normalize
        if log_sum > 0:
            for format_name in posteriors:
                posteriors[format_name] /= log_sum

        return posteriors

    def get_confidence_with_uncertainty(self, format_name: str) -> Dict[str, float]:
        """
        Get confidence with uncertainty quantification.

        Based on research on scaling laws for uncertainty in Bayesian systems.
        """
        if format_name not in self.hypotheses:
            return {
                "confidence": 0.0,
                "uncertainty": 1.0,
                "evidence_count": 0,
                "unique_evidence_ratio": 0.0,
            }

        # Get normalized posterior probabilities
        posteriors = self.calculate_posterior_probabilities()
        confidence = posteriors.get(format_name, 0.0)

        # Calculate uncertainty using entropy
        # H = -Σ p_i * log(p_i)
        entropy = 0.0
        for prob in posteriors.values():
            if prob > 1e-10:
                entropy -= prob * math.log(prob)

        # Normalize entropy by maximum possible entropy
        max_entropy = math.log(len(posteriors)) if len(posteriors) > 1 else 1.0
        uncertainty = entropy / max_entropy if max_entropy > 0 else 1.0

        # Calculate evidence quality metrics
        hypothesis = self.hypotheses[format_name]
        evidence_count = len(hypothesis.evidence_items)

        strength_dist = hypothesis.evidence_strength_distribution
        unique_evidence_ratio = (
            strength_dist[EvidenceWeight.UNIQUE] / evidence_count
            if evidence_count > 0
            else 0.0
        )

        return {
            "confidence": confidence,
            "uncertainty": uncertainty,
            "evidence_count": evidence_count,
            "unique_evidence_ratio": unique_evidence_ratio,
            "posterior_entropy": entropy,
        }

    def get_best_hypothesis_with_reasoning(self) -> Tuple[str, float, dict[str, Any]]:
        """
        Get best hypothesis with detailed reasoning.

        Returns format name, confidence, and reasoning breakdown.
        """
        posteriors = self.calculate_posterior_probabilities()

        if not posteriors:
            return "unknown", 0.0, {"reason": "No evidence accumulated"}

        # Find best hypothesis
        best_format = max(posteriors.keys(), key=lambda k: posteriors[k])
        best_confidence = posteriors[best_format]

        # Build reasoning
        if best_format in self.hypotheses:
            hypothesis = self.hypotheses[best_format]
            evidence_breakdown: dict[str, Any] = {
                "total_evidence": len(hypothesis.evidence_items),
                "evidence_by_type": {},
                "evidence_by_strength": hypothesis.evidence_strength_distribution,
                "prior_contribution": math.exp(hypothesis.prior_log_prob),
                "evidence_contribution": math.exp(
                    sum(e.log_bayes_factor for e in hypothesis.evidence_items)
                ),
            }

            # Group evidence by type
            for evidence in hypothesis.evidence_items:
                if evidence.source_type not in evidence_breakdown["evidence_by_type"]:
                    evidence_breakdown["evidence_by_type"][evidence.source_type] = []
                evidence_breakdown["evidence_by_type"][evidence.source_type].append(
                    {
                        "strength": evidence.evidence_strength.name,
                        "likelihood_ratio": evidence.likelihood_ratio,
                        "confidence": evidence.confidence,
                        "description": evidence.description,
                    }
                )
        else:
            evidence_breakdown = {"error": "Hypothesis not found"}

        # Check for ties
        sorted_posteriors = sorted(posteriors.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_posteriors) > 1:
            second_best_conf = sorted_posteriors[1][1]
            confidence_margin = best_confidence - second_best_conf
            evidence_breakdown["confidence_margin"] = confidence_margin
            evidence_breakdown["is_decisive"] = confidence_margin > 0.1

        reasoning = {
            "all_posteriors": posteriors,
            "evidence_breakdown": evidence_breakdown,
            "method": "proper_bayesian_accumulation",
        }

        return best_format, best_confidence, reasoning

    def clear(self) -> None:
        """Clear all hypotheses for new detection."""
        self.hypotheses.clear()
