"""Xray for JIRA format definition.

Based on research findings:
- Tests stored as native JIRA issues (4 issue types: Test, Test Set, Test Execution,
- Uses JQL for searching with extended capabilities
- Evidence attachments for test artifacts
- testExecutions, testInfo, evidences as unique identifiers
- Integration with JIRA's native issue schema
"""

from importobot.medallion.bronze.format_models import (
    EvidenceWeight,
    FieldDefinition,
    FormatDefinition,
)
from importobot.medallion.interfaces.enums import SupportedFormat


def create_xray_format() -> FormatDefinition:
    """Create Xray for JIRA format definition.

    Xray's unique characteristics:
    - testExecutions: Xray-specific execution structure (UNIQUE)
    - testInfo: Xray test information structure (UNIQUE)
    - evidences: Xray evidence attachments (UNIQUE)
    - Tests as native JIRA issues with full JIRA integration
    - 4 specific issue types for test management
    """
    return FormatDefinition(
        name="Xray for JIRA",
        format_type=SupportedFormat.JIRA_XRAY,
        description="Xray test management storing tests as native JIRA issues with",
        # UNIQUE indicators - definitive Xray identifiers
        unique_indicators=[
            FieldDefinition(
                name="testExecutions",
                evidence_weight=EvidenceWeight.UNIQUE,
                description="Xray-specific test execution structure",
                is_required=True,
            ),
            FieldDefinition(
                name="testInfo",
                evidence_weight=EvidenceWeight.UNIQUE,
                description="Xray test information structure",
                is_required=True,
            ),
            FieldDefinition(
                name="evidences",
                evidence_weight=EvidenceWeight.UNIQUE,
                description="Xray evidence attachments - unique to Xray",
                is_required=False,
            ),
        ],
        # STRONG indicators - JIRA integration markers
        strong_indicators=[
            FieldDefinition(
                name="xrayInfo",
                evidence_weight=EvidenceWeight.STRONG,
                description="Xray info object - Xray-specific metadata structure",
            ),
            FieldDefinition(
                name="testExecutionKey",
                evidence_weight=EvidenceWeight.STRONG,
                description="Xray test execution key - unique "
                "to Xray JSON import format",
            ),
            FieldDefinition(
                name="testPlanKey",
                evidence_weight=EvidenceWeight.STRONG,
                description="Xray test plan key - Xray-specific planning structure",
            ),
            FieldDefinition(
                name="testKey",
                evidence_weight=EvidenceWeight.STRONG,
                description="Xray test key within execution results",
            ),
            FieldDefinition(
                name="testEnvironments",
                evidence_weight=EvidenceWeight.STRONG,
                description="Xray test environments array - Xray-specific field",
            ),
            FieldDefinition(
                name="issues",
                evidence_weight=EvidenceWeight.STRONG,
                description="JIRA issues structure - Xray uses native JIRA issues",
            ),
            FieldDefinition(
                name="key",
                evidence_weight=EvidenceWeight.STRONG,
                pattern=r"^[A-Z]+-\d+$",
                description="JIRA issue key pattern (PROJECT-123)",
            ),
            FieldDefinition(
                name="fields",
                evidence_weight=EvidenceWeight.STRONG,
                description="JIRA fields structure - Xray extends JIRA fields",
            ),
        ],
        # MODERATE indicators - JIRA system features
        moderate_indicators=[
            FieldDefinition(
                name="issuetype",
                evidence_weight=EvidenceWeight.MODERATE,
                description=(
                    "JIRA issue type - Xray adds Test, Test Set, Test Execution"
                ),
            ),
            FieldDefinition(
                name="customfield",
                evidence_weight=EvidenceWeight.MODERATE,
                pattern=r"customfield_\d+",
                description="JIRA custom field pattern",
            ),
        ],
        # WEAK indicators - general JIRA features
        weak_indicators=[
            FieldDefinition(
                name="expand",
                evidence_weight=EvidenceWeight.WEAK,
                description="JIRA expand parameter for API responses",
            ),
            FieldDefinition(
                name="schema",
                evidence_weight=EvidenceWeight.WEAK,
                description="JIRA schema information",
            ),
            FieldDefinition(
                name="names",
                evidence_weight=EvidenceWeight.WEAK,
                description="JIRA field names metadata",
            ),
        ],
        # Confidence parameters - unique indicators provide strong confidence
        confidence_boost_threshold=0.33,  # Single unique indicator sufficient
        confidence_boost_factor=0.9,  # Higher boost due to strong JIRA integration
        min_score_threshold=4,
        # Metadata
        version="1.0",
        author="Bronze Layer Format Detection System",
        created_date="2025-09-23",
    )
