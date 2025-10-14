"""TestLink format definition.

Based on research findings:
- XML-based test management system
- testsuite and testsuites structure
- testcase elements within suites
- Often exported to JSON from XML structure
- Traditional suite-based organization
"""

from importobot.medallion.bronze.format_models import (
    EvidenceWeight,
    FieldDefinition,
    FormatDefinition,
)
from importobot.medallion.interfaces.enums import SupportedFormat


def create_testlink_format() -> FormatDefinition:
    """Create TestLink format definition.

    TestLink's unique characteristics:
    - testsuites: TestLink suite collection (UNIQUE)
    - testsuite: TestLink individual suite (UNIQUE)
    - XML-based origin with JSON exports
    - Suite-centric organization model
    """
    return FormatDefinition(
        name="TestLink",
        format_type=SupportedFormat.TESTLINK,
        description="TestLink XML-based test management system with suite-centric",
        # UNIQUE indicators - definitive TestLink identifiers
        unique_indicators=[
            FieldDefinition(
                name="testsuites",
                evidence_weight=EvidenceWeight.UNIQUE,
                description="TestLink test suites collection - XML origin",
                is_required=False,
            ),
            FieldDefinition(
                name="testsuite",
                evidence_weight=EvidenceWeight.UNIQUE,
                pattern=r"^testsuite$",
                description="TestLink individual test suite structure",
                is_required=True,
            ),
        ],
        # STRONG indicators - TestLink structure elements
        strong_indicators=[
            FieldDefinition(
                name="internalid",
                evidence_weight=EvidenceWeight.STRONG,
                description="TestLink internal ID attribute - XML-specific",
            ),
            FieldDefinition(
                name="externalid",
                evidence_weight=EvidenceWeight.STRONG,
                description="TestLink external identifier - unique to TestLink",
            ),
            FieldDefinition(
                name="node_order",
                evidence_weight=EvidenceWeight.STRONG,
                description="TestLink node ordering - XML hierarchy indicator",
            ),
            FieldDefinition(
                name="execution_type",
                evidence_weight=EvidenceWeight.STRONG,
                description="TestLink execution type (1=manual, 2=automated)",
            ),
            FieldDefinition(
                name="testcase",
                evidence_weight=EvidenceWeight.STRONG,
                pattern=r"^testcase$",
                description="TestLink test case within suite - lowercase pattern",
            ),
        ],
        # MODERATE indicators - common test management features
        moderate_indicators=[
            FieldDefinition(
                name="name",
                evidence_weight=EvidenceWeight.MODERATE,
                description="Suite or test name",
            ),
            FieldDefinition(
                name="tests",
                evidence_weight=EvidenceWeight.MODERATE,
                pattern=r"^tests$",
                description="Test collection reference",
            ),
        ],
        # WEAK indicators - supplementary information
        weak_indicators=[
            FieldDefinition(
                name="time",
                evidence_weight=EvidenceWeight.WEAK,
                description="Execution time information",
            ),
        ],
        # Confidence parameters - unique indicators provide strong evidence
        confidence_boost_threshold=0.5,  # Require higher evidence due to XML heritage
        confidence_boost_factor=0.8,
        min_score_threshold=4,
        # Metadata
        version="1.0",
        author="Bronze Layer Format Detection System",
        created_date="2025-09-23",
    )
