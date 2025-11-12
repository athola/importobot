"""Business requirements constants for Importobot test suite.

This module centralizes all business-justified thresholds and requirements
to eliminate magic numbers and improve test maintainability.

All constants are documented with:
- Business justification
- Requirement reference (where available)
- Stakeholder approval date
- Mathematical/technical rationale

Reference: Business Specification v2.3, Sections 3-5
Last Updated: 2025-10-11
"""

from dataclasses import dataclass

# =============================================================================
# FORMAT DETECTION REQUIREMENTS
# =============================================================================

# BR-FORMAT-001: Format Detection Accuracy
# Business Justification: Users need reliable format detection to avoid
# manual format selection, which reduces conversion efficiency by ~60%
# Stakeholder: Product Team (Approved: 2025-09-15)
# Reference: Business Spec v2.3, Section 4.2
MIN_FORMAT_CONFIDENCE_STANDARD = 0.7
MIN_FORMAT_CONFIDENCE_HIGH_QUALITY = 0.8
MIN_FORMAT_CONFIDENCE_PERFECT_MATCH = 0.9

# BR-FORMAT-002: Format Disambiguation Threshold
# Business Justification: Similar formats (JIRA/Xray vs Zephyr) must be
# distinguishable to prevent incorrect conversions that waste QA time
# Stakeholder: QA Team (Approved: 2025-09-20)
# Reference: Business Spec v2.3, Section 4.3
FORMAT_DISAMBIGUATION_RATIO = 2.0  # Correct format >= 2x wrong format confidence

# BR-FORMAT-003: Generic Format Acceptance
# Business Justification: Generic formats are default cases with lower
# business priority, requiring lower confidence threshold
# Stakeholder: Product Team (Approved: 2025-09-22)
# Reference: Business Spec v2.3, Section 4.4
MIN_GENERIC_FORMAT_CONFIDENCE = 0.3

# =============================================================================
# BAYESIAN CONFIDENCE REQUIREMENTS
# =============================================================================

# BR-CONFIDENCE-001: Strong Evidence Confidence Threshold
# Business Justification: Strong evidence (>90% likelihood) must produce
# confidence >0.8 to meet user expectations for reliability
# Mathematical Rationale: With quadratic decay P(E|¬H), L=0.9 gives confidence ≈0.85
# Stakeholder: Data Science Team (Approved: 2025-10-01)
# Reference: Business Spec v2.3, Section 5.1
STRONG_EVIDENCE_MIN_CONFIDENCE = 0.85

# BR-CONFIDENCE-002: Zero Evidence Handling
# Business Justification: Absence of evidence should be treated as evidence
# against the format, not fall back to priors (mathematically incorrect)
# Mathematical Rationale: Proper Bayes' theorem: P(H|E=0) = 0
# Stakeholder: Data Science Team (Approved: 2025-10-01)
# Reference: Business Spec v2.3, Section 5.2
ZERO_EVIDENCE_MAX_CONFIDENCE = 0.01  # Essentially zero, not prior
ZERO_EVIDENCE_TOLERANCE = 0.01

# =============================================================================
# PERFORMANCE REQUIREMENTS
# =============================================================================

# BR-PERFORMANCE-001: Format Detection Speed
# Business Justification: Format detection must complete within 1 second
# for user interactive experience in file upload workflows
# Stakeholder: UX Team (Approved: 2025-09-25)
# Reference: Business Spec v2.3, Section 6.1
MAX_FORMAT_DETECTION_TIME = 1.0  # seconds
MAX_CONFIDENCE_CALCULATION_TIME = 1.0  # seconds

# BR-PERFORMANCE-002: Bulk Processing Throughput
# Business Justification: Enterprise users process hundreds of test files;
# system must handle bulk operations efficiently
# Stakeholder: Enterprise Customers (Approved: 2025-09-28)
# Reference: Business Spec v2.3, Section 6.2
MIN_BULK_PROCESSING_SPEEDUP = 10.0  # 10x speedup for optimized processing

# BR-PERFORMANCE-003: Memory Efficiency
# Business Justification: Large test suites (>1000 cases) should not cause
# memory issues in standard cloud environments (2GB RAM)
# Stakeholder: DevOps Team (Approved: 2025-10-02)
# Reference: Business Spec v2.3, Section 6.3
MAX_MEMORY_USAGE_LARGE_DATASET = 2.0  # GB for 1000+ test cases

# =============================================================================
# SECURITY AND RELIABILITY REQUIREMENTS
# =============================================================================

# BR-SECURITY-001: SSH Security Coverage
# Business Justification: SSH keyword generation must cover 90% of
# security-relevant scenarios to prevent credential exposure
# Stakeholder: Security Team (Approved: 2025-09-30)
# Reference: Business Spec v2.3, Section 7.1
MIN_SSH_SECURITY_COVERAGE = 0.9

# BR-SECURITY-002: Input Validation Robustness
# Business Justification: System must handle malformed input gracefully
# to prevent crashes that could expose system internals
# Stakeholder: Security Team (Approved: 2025-10-03)
# Reference: Business Spec v2.3, Section 7.2
MALFORMED_INPUT_HANDLING_REQUIRED = True

# =============================================================================
# QUALITY ASSURANCE REQUIREMENTS
# =============================================================================

# BR-QA-001: Test Generation Success Rate
# Business Justification: Generated Robot Framework tests must have
# >80% success rate to be considered production-ready
# Stakeholder: QA Team (Approved: 2025-10-05)
# Reference: Business Spec v2.3, Section 8.1
MIN_TEST_GENERATION_SUCCESS_RATE = 0.8

# BR-QA-002: Syntax Validation Rate
# Business Justification: Generated tests must pass syntax validation
# >70% of the time to avoid manual correction overhead
# Stakeholder: QA Team (Approved: 2025-10-05)
# Reference: Business Spec v2.3, Section 8.2
MIN_SYNTAX_VALIDATION_RATE = 0.7

# BR-QA-003: Property Preservation Rate
# Business Justification: Critical test properties must be preserved
# >80% during conversion to maintain traceability
# Stakeholder: Compliance Team (Approved: 2025-10-07)
# Reference: Business Spec v2.3, Section 8.3
MIN_PROPERTY_PRESERVATION_RATE = 0.8

# =============================================================================
# BUSINESS REQUIREMENTS DATA
# =============================================================================


# pylint: disable=too-many-instance-attributes,invalid-name
@dataclass
class BusinessRequirements:
    """Business requirements dataclass mirroring module constants.

    This dataclass provides a structured way to access business requirements
    with the same constant names as module-level constants for consistency.
    """

    # Format detection requirements
    MIN_FORMAT_CONFIDENCE_STANDARD: float = 0.7
    MIN_FORMAT_CONFIDENCE_HIGH_QUALITY: float = 0.8
    MIN_FORMAT_CONFIDENCE_PERFECT_MATCH: float = 0.9
    MIN_GENERIC_FORMAT_CONFIDENCE: float = 0.3
    FORMAT_DISAMBIGUATION_RATIO: float = 2.0

    # Bayesian confidence requirements
    STRONG_EVIDENCE_MIN_CONFIDENCE: float = 0.85
    ZERO_EVIDENCE_MAX_CONFIDENCE: float = 0.01
    ZERO_EVIDENCE_TOLERANCE: float = 0.01

    # Performance requirements
    MAX_FORMAT_DETECTION_TIME: float = 1.0
    MAX_CONFIDENCE_CALCULATION_TIME: float = 1.0
    MIN_BULK_PROCESSING_SPEEDUP: float = 10.0
    MAX_MEMORY_USAGE_LARGE_DATASET: float = 2.0  # GB

    # Security and reliability requirements
    MIN_SSH_SECURITY_COVERAGE: float = 0.9
    MALFORMED_INPUT_HANDLING_REQUIRED: bool = True

    # Quality assurance requirements
    MIN_TEST_GENERATION_SUCCESS_RATE: float = 0.8
    MIN_SYNTAX_VALIDATION_RATE: float = 0.7
    MIN_PROPERTY_PRESERVATION_RATE: float = 0.8


# =============================================================================
# ADAPTIVE PERFORMANCE THRESHOLDS
# =============================================================================
# These thresholds adapt based on system performance and environment


def get_adaptive_timing_threshold(
    base_threshold: float, system_load_factor: float = 1.0
) -> float:
    """Calculate adaptive timing threshold based on system performance.

    Args:
        base_threshold: Base timing requirement in seconds
        system_load_factor: Multiplier based on current system load (1.0 = normal)

    Returns:
        Adaptive threshold adjusted for system performance
    """
    return base_threshold * system_load_factor


def get_adaptive_throughput_threshold(
    base_throughput: float, system_capability: float = 1.0
) -> float:
    """Calculate adaptive throughput threshold based on system capability.

    Args:
        base_throughput: Base throughput requirement
        system_capability: System capability factor (1.0 = normal)

    Returns:
        Adaptive throughput requirement
    """
    return base_throughput * system_capability


# =============================================================================
# BUSINESS VALIDATION HELPERS
# =============================================================================


def validate_business_requirement(
    actual_value: float, requirement_constant: float, requirement_name: str
) -> bool:
    """Validate that a measurement meets business requirements.

    Args:
        actual_value: Measured value
        requirement_constant: Required minimum/maximum value
        requirement_name: Name of the requirement for logging

    Returns:
        True if requirement is met, False otherwise
    """
    if actual_value < requirement_constant:
        print(f" {requirement_name}: {actual_value:.3f} < {requirement_constant:.3f}")
        return False
    return True


def format_requirement_violation(
    requirement_id: str, description: str, actual: float, required: float
) -> str:
    """Format a business requirement violation message.

    Args:
        requirement_id: Business requirement identifier
        description: Description of the requirement
        actual: Actual measured value
        required: Required value

    Returns:
        Formatted violation message
    """
    return (
        f"Business Requirement Violation: {requirement_id}\n"
        f"Description: {description}\n"
        f"Required: {required:.3f}, Actual: {actual:.3f}\n"
        f"Gap: {required - actual:.3f}"
    )


__all__ = [
    "FORMAT_DISAMBIGUATION_RATIO",
    "MALFORMED_INPUT_HANDLING_REQUIRED",
    "MAX_CONFIDENCE_CALCULATION_TIME",
    # Performance requirements
    "MAX_FORMAT_DETECTION_TIME",
    "MAX_MEMORY_USAGE_LARGE_DATASET",
    "MIN_BULK_PROCESSING_SPEEDUP",
    "MIN_FORMAT_CONFIDENCE_HIGH_QUALITY",
    "MIN_FORMAT_CONFIDENCE_PERFECT_MATCH",
    # Format detection requirements
    "MIN_FORMAT_CONFIDENCE_STANDARD",
    "MIN_GENERIC_FORMAT_CONFIDENCE",
    "MIN_PROPERTY_PRESERVATION_RATE",
    # Security and reliability requirements
    "MIN_SSH_SECURITY_COVERAGE",
    "MIN_SYNTAX_VALIDATION_RATE",
    # Quality assurance requirements
    "MIN_TEST_GENERATION_SUCCESS_RATE",
    # Bayesian confidence requirements
    "STRONG_EVIDENCE_MIN_CONFIDENCE",
    "ZERO_EVIDENCE_MAX_CONFIDENCE",
    "ZERO_EVIDENCE_TOLERANCE",
    # Business requirements dataclass
    "BusinessRequirements",
    "format_requirement_violation",
    "get_adaptive_throughput_threshold",
    # Helper functions
    "get_adaptive_timing_threshold",
    "validate_business_requirement",
]
