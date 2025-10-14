"""Zephyr for JIRA format definition.

Based on research findings:
- Uses separate data model outside JIRA issues
- Execution cycles with test case references
- Custom fields like customfield_11101 (Zephyr Teststep)
- Uses ZQL for querying
- Up to 20 custom fields for executions, 5 for test steps
"""

from importobot.medallion.bronze.format_models import (
    EvidenceWeight,
    FieldDefinition,
    FormatDefinition,
)
from importobot.medallion.interfaces.enums import SupportedFormat

from .format_constants import UNIQUE_INDICATORS_CONFIDENCE, get_standard_format_kwargs


def create_zephyr_format() -> FormatDefinition:
    """Create Zephyr for JIRA format definition.

    Zephyr's unique characteristics:
    - testCase: Core Zephyr test case structure (UNIQUE)
    - execution: Zephyr execution data (UNIQUE)
    - cycle: Zephyr test cycle management (UNIQUE)
    - Separate data model from JIRA issues
    - Execution-centric workflow
    """
    return FormatDefinition(
        name="Zephyr for JIRA",
        format_type=SupportedFormat.ZEPHYR,
        description=(
            "Zephyr test management with execution cycles and separate data model"
        ),
        # UNIQUE indicators - these are definitive Zephyr identifiers
        unique_indicators=[
            FieldDefinition(
                name="testCase",
                evidence_weight=EvidenceWeight.UNIQUE,
                description="Zephyr-specific test case structure - core identifier",
                is_required=True,
            ),
            FieldDefinition(
                name="execution",
                evidence_weight=EvidenceWeight.UNIQUE,
                description="Zephyr execution data - execution-centric model",
                is_required=True,
            ),
            FieldDefinition(
                name="cycle",
                evidence_weight=EvidenceWeight.UNIQUE,
                description="Zephyr test cycle - execution cycle management",
                is_required=True,
            ),
        ],
        # STRONG indicators - important Zephyr context
        strong_indicators=[
            FieldDefinition(
                name="cycleId",
                evidence_weight=EvidenceWeight.STRONG,
                description="Zephyr cycle identifier - camelCase is Zephyr-specific",
            ),
            FieldDefinition(
                name="executionId",
                evidence_weight=EvidenceWeight.STRONG,
                description="Zephyr execution identifier - camelCase pattern",
            ),
            FieldDefinition(
                name="entityType",
                evidence_weight=EvidenceWeight.STRONG,
                description="Zephyr custom field entity type (EXECUTION/TESTSTEP)",
            ),
            FieldDefinition(
                name="project",
                evidence_weight=EvidenceWeight.STRONG,
                description="Project context in Zephyr",
            ),
            FieldDefinition(
                name="version",
                evidence_weight=EvidenceWeight.STRONG,
                description="Version information in Zephyr cycles",
            ),
        ],
        # MODERATE indicators - supplementary Zephyr features
        moderate_indicators=[
            FieldDefinition(
                name="sprint",
                evidence_weight=EvidenceWeight.MODERATE,
                description="Sprint association in Zephyr",
            ),
        ],
        # WEAK indicators - pattern-based detection
        weak_indicators=[
            FieldDefinition(
                name="testCaseKey",
                evidence_weight=EvidenceWeight.WEAK,
                pattern=r".*test.*case.*",
                description="Test case key pattern matching",
            ),
        ],
        # Standard format metadata and confidence parameters
        **get_standard_format_kwargs(UNIQUE_INDICATORS_CONFIDENCE),
    )
