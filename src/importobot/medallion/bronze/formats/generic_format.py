"""Generic test format definition.

This serves as a default for unstructured, custom, or unsupported test data formats.
Based on Medallion Architecture Bronze layer principles of accepting raw data
and common test management patterns found across systems.

Used when no specific format can be confidently identified.
"""

from importobot.medallion.bronze.format_models import (
    EvidenceWeight,
    FieldDefinition,
    FormatDefinition,
)
from importobot.medallion.interfaces.enums import SupportedFormat


def create_generic_format() -> FormatDefinition:
    """Create Generic test format definition.

    Generic format characteristics:
    - No unique indicators (default when others fail)
    - Common test management field patterns
    - Higher threshold for detection to avoid false positives
    - Suitable for custom or unstructured test data
    """
    return FormatDefinition(
        name="Generic Test Format",
        format_type=SupportedFormat.GENERIC,
        description="Default format for unstructured, custom, or unrecognized test",
        # UNIQUE indicators - none for generic (this is the default)
        unique_indicators=[],
        # STRONG indicators - common test collection patterns
        strong_indicators=[
            FieldDefinition(
                name="tests",
                evidence_weight=EvidenceWeight.STRONG,
                pattern=r"^tests$",
                description="Generic test collection",
            ),
            FieldDefinition(
                name="test_cases",
                evidence_weight=EvidenceWeight.STRONG,
                description="Test cases collection (underscore naming)",
            ),
            FieldDefinition(
                name="testcases",
                evidence_weight=EvidenceWeight.STRONG,
                description="Test cases collection (compound naming)",
            ),
        ],
        # MODERATE indicators - common test structure elements
        moderate_indicators=[
            FieldDefinition(
                name="steps",
                evidence_weight=EvidenceWeight.MODERATE,
                pattern=r"^steps$",
                description="Test steps or procedures",
            ),
            FieldDefinition(
                name="test",
                evidence_weight=EvidenceWeight.MODERATE,
                description="Single test reference",
            ),
            FieldDefinition(
                name="case",
                evidence_weight=EvidenceWeight.MODERATE,
                description="Single case reference",
            ),
        ],
        # WEAK indicators - very common fields that might indicate test data
        weak_indicators=[
            FieldDefinition(
                name="name",
                evidence_weight=EvidenceWeight.WEAK,
                description="Generic name field",
            ),
            FieldDefinition(
                name="description",
                evidence_weight=EvidenceWeight.WEAK,
                description="Generic description field",
            ),
            FieldDefinition(
                name="title",
                evidence_weight=EvidenceWeight.WEAK,
                description="Generic title field",
            ),
            FieldDefinition(
                name="id",
                evidence_weight=EvidenceWeight.WEAK,
                description="Generic identifier field",
            ),
        ],
        # Confidence parameters - higher threshold since this is the default option
        confidence_boost_threshold=0.67,  # Require strong evidence for confidence boost
        confidence_boost_factor=0.6,  # Lower boost factor
        min_score_threshold=6,  # Higher threshold to avoid false positives
        # Metadata
        version="1.0",
        author="Bronze Layer Format Detection System",
        created_date="2025-09-23",
    )
