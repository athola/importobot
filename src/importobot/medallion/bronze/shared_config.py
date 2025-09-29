"""Shared configuration constants for bronze layer components.

This module centralizes configuration values to eliminate code duplication
across format detection and confidence scoring modules.
"""

from ..interfaces.enums import SupportedFormat

# Format prior probabilities based on prevalence in test management systems
DEFAULT_FORMAT_PRIORS = {
    "jira_xray": 0.25,
    "testrail": 0.20,
    "testlink": 0.15,
    "zephyr": 0.15,
    "generic": 0.20,
    "unknown": 0.05,
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
