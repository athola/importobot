"""Shared configuration constants for bronze layer components.

This module centralizes configuration values to eliminate code duplication
across format detection and confidence scoring modules.
"""

from ..interfaces.enums import SupportedFormat

# Format prior probabilities based on prevalence in test management systems
#
# MATHEMATICAL ASSUMPTION: MUTUAL EXCLUSIVITY
# -------------------------------------------
# These priors sum to 1.0 (within floating-point tolerance), which encodes
# the assumption that format types are MUTUALLY EXCLUSIVE and EXHAUSTIVE.
#
# This means:
# 1. A test data file can only be ONE format type at a time
# 2. Every test data file must fall into one of these categories
#
# If your data can be:
# - Hybrid formats (e.g., JIRA export with TestRail fields)
# - Ambiguous (could be multiple formats)
# - Truly unknown (not in this enumeration)
#
# Then this prior configuration may need adjustment or you may need
# multi-label classification instead of single-label.
#
# Calibration Source:
# ------------------
# Prior values adjusted for Bayesian evidence accumulation (2025):
# Higher priors for well-defined formats improve confidence with strong evidence
# while maintaining mathematical rigor via Bayes' theorem.
#
# - JIRA/Xray: 30% (most common in enterprise, strong indicators)
# - TestRail: 25% (common in QA-focused teams, distinct patterns)
# - TestLink: 20% (legacy systems, unique XML structure)
# - Zephyr: 20% (cloud/modern, Jira-specific patterns)
# - Generic: 4% (custom exports, catch-all)
# - Unknown: 1% (rare/malformed formats)
#
# Total: 1.00 (enforces mutual exclusivity)
DEFAULT_FORMAT_PRIORS = {
    "JIRA_XRAY": 0.30,
    "TESTRAIL": 0.25,
    "TESTLINK": 0.20,
    "ZEPHYR": 0.20,
    "GENERIC": 0.04,
    "UNKNOWN": 0.01,
}

# Evidence type preferences for Bayesian scoring
DEFAULT_EVIDENCE_PREFERENCES = {
    "required_key": 1.0,  # Standard baseline
    "unique_indicator": 3.0,  # Strong preference for unique evidence
    "pattern_match": 2.0,  # Good preference for pattern validation
    "structure_indicator": 1.5,  # Moderate preference
    "optional_key": 0.8,  # Slight preference reduction
}

# Common field sets for format detection
TESTRAIL_COMMON_FIELDS = {
    "runs",
    "cases",
    "results",
    "suite_id",
    "project_id",
}

TESTLINK_COMMON_FIELDS = {
    "section_id",
    "template_id",
    "type_id",
    "priority_id",
    "milestone_id",
}

# Priority multipliers for confidence scoring
PRIORITY_MULTIPLIERS = {
    SupportedFormat.JIRA_XRAY: 1.0,
    SupportedFormat.ZEPHYR: 1.0,
    SupportedFormat.TESTRAIL: 1.0,
    SupportedFormat.TESTLINK: 1.0,
    SupportedFormat.GENERIC: 0.8,
    SupportedFormat.UNKNOWN: 0.6,
}

# P(E|¬H) Estimation Configuration
# --------------------------------
# Controls how P(E|¬H) (probability of evidence given NOT the hypothesis) is estimated
# in Bayesian inference.
#
# Modes:
# - "hardcoded": Use the empirically validated quadratic decay formula
#   P(E|¬H) = 0.01 + 0.49 * (1 - L) ** 2
#
# - "learned": Use parameters learned from cross-format training data
#   P(E|¬H) = a + b * (1 - L) ** c where (a, b, c) are learned
#
# Default: "hardcoded" (proven to work well, mathematically rigorous)
P_E_NOT_H_MODE = "hardcoded"

# Hardcoded P(E|¬H) parameters (quadratic decay)
# These were empirically validated and mathematically proven to satisfy:
# - Strong evidence (L>0.9) → confidence >0.8
# - Zero evidence (L=0) → very low confidence
# - Perfect evidence (L=1.0) with prior=0.1 → posterior ≈0.92
P_E_NOT_H_HARDCODED = {
    "a": 0.01,  # Minimum P(E|¬H) for perfect evidence
    "b": 0.49,  # Scale factor
    "c": 2.0,  # Quadratic decay exponent
}

# Learned P(E|¬H) parameters (populated by training)
# When P_E_NOT_H_MODE="learned", these parameters are used instead
# To train: run scripts/src/importobot_scripts/train_p_e_not_h.py
P_E_NOT_H_LEARNED = {
    "a": 0.01,  # Will be updated by training
    "b": 0.49,  # Will be updated by training
    "c": 2.0,  # Will be updated by training
    "training_mse": None,  # Mean squared error on training data
    "improvement_over_hardcoded": None,  # Percentage improvement
}
