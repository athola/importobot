"""Unknown format definition.

This represents data that cannot be identified as any known test management format.
Used by the Bronze layer to handle completely unrecognized data structures
while maintaining data lineage and allowing future format identification.

In Medallion Architecture, the Bronze layer should accept all data,
even if it cannot be categorized or structured.
"""

from importobot.medallion.bronze.format_models import (
    EvidenceWeight,
    FieldDefinition,
    FormatDefinition,
)
from importobot.medallion.interfaces.enums import SupportedFormat


def create_unknown_format() -> FormatDefinition:
    """Create Unknown format definition for unidentifiable data.

    Unknown format characteristics:
    - No indicators at all - this is assigned when detection fails
    - Zero confidence by design
    - Allows Bronze layer to ingest any data with UNKNOWN classification
    - Maintains data lineage for future analysis
    """
    return FormatDefinition(
        name="Unknown Format",
        format_type=SupportedFormat.UNKNOWN,
        description="Unidentifiable data format - assigned when no other format",
        # No indicators - this format is assigned by exclusion
        unique_indicators=[],
        strong_indicators=[],
        moderate_indicators=[],
        weak_indicators=[],
        # Configuration parameters - designed to never match during detection
        confidence_boost_threshold=1.0,  # Impossible to reach
        confidence_boost_factor=0.0,  # No boost
        min_score_threshold=999,  # Impossible to reach through scoring
        # Metadata
        version="1.0",
        author="Bronze Layer Format Detection System",
        created_date="2025-09-23",
    )


def create_placeholder_format(name: str, description: str = "") -> FormatDefinition:
    """Create a placeholder format definition for future implementation.

    This allows teams to define new formats that will be supported later
    without breaking the detection system.

    Args:
        name: Format name for logging and identification
        description: Optional description of the format

    Returns:
        A minimal format definition that can be extended later
    """
    return FormatDefinition(
        name=f"Placeholder: {name}",
        format_type=SupportedFormat.UNKNOWN,  # Will need updating when
        description=(
            f"Placeholder for future format: {description}"
            if description
            else f"Placeholder for {name}"
        ),
        # Minimal structure - to be filled in when implementing
        unique_indicators=[
            FieldDefinition(
                name="__placeholder__",
                evidence_weight=EvidenceWeight.NONE,
                description="Placeholder field - replace with actual format indicators",
            )
        ],
        strong_indicators=[],
        moderate_indicators=[],
        weak_indicators=[],
        # Conservative parameters
        confidence_boost_threshold=0.5,
        confidence_boost_factor=0.5,
        min_score_threshold=10,  # High threshold until properly implemented
        # Metadata
        version="0.1.0-placeholder",
        author="Format Placeholder System",
        created_date="2025-09-23",
    )
