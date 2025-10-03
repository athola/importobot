"""TestRail format definition.

Based on research findings:
- Independent test management platform with comprehensive API
- Hierarchical structure: Projects → Suites → Sections → Cases → Runs → Tests → Results
- Unique identifiers: runs, cases, suite_id, case_id, project_id
- JSON API with UTF-8 encoding
- Custom fields with system_name pattern: custom_{system_name}
"""

from importobot.medallion.bronze.format_models import (
    EvidenceWeight,
    FieldDefinition,
    FormatDefinition,
)
from importobot.medallion.interfaces.enums import SupportedFormat

from .format_constants import UNIQUE_INDICATORS_CONFIDENCE, get_standard_format_kwargs


def create_testrail_format() -> FormatDefinition:
    """Create TestRail format definition.

    TestRail's unique characteristics:
    - runs: TestRail test runs (UNIQUE)
    - cases: TestRail test cases (UNIQUE)
    - Hierarchical entity relationships
    - Independent platform (not JIRA-based)
    - Comprehensive API with pagination
    """
    return FormatDefinition(
        name="TestRail",
        format_type=SupportedFormat.TESTRAIL,
        description="TestRail independent test management platform with hierarchical",
        # UNIQUE indicators - definitive TestRail identifiers
        unique_indicators=[
            FieldDefinition(
                name="runs",
                evidence_weight=EvidenceWeight.UNIQUE,
                pattern=r".*run.*",
                description="TestRail test runs - core execution concept",
                is_required=False,
            ),
            FieldDefinition(
                name="cases",
                evidence_weight=EvidenceWeight.UNIQUE,
                description="TestRail test cases - distinct from other systems",
                is_required=False,
            ),
            FieldDefinition(
                name="results",
                evidence_weight=EvidenceWeight.UNIQUE,
                description="TestRail test results - execution outcomes",
                is_required=False,
            ),
        ],
        # STRONG indicators - TestRail hierarchy and identification
        strong_indicators=[
            FieldDefinition(
                name="suite_id",
                evidence_weight=EvidenceWeight.STRONG,
                description="TestRail suite identifier - hierarchical structure",
            ),
            FieldDefinition(
                name="case_id",
                evidence_weight=EvidenceWeight.STRONG,
                description="TestRail case identifier - unique entity ID",
            ),
            FieldDefinition(
                name="tests",
                evidence_weight=EvidenceWeight.STRONG,
                pattern=r".*test.*",
                description="TestRail test instances (different from cases)",
            ),
        ],
        # MODERATE indicators - TestRail organizational features
        moderate_indicators=[
            FieldDefinition(
                name="project_id",
                evidence_weight=EvidenceWeight.MODERATE,
                description="TestRail project identifier",
            ),
            FieldDefinition(
                name="milestone_id",
                evidence_weight=EvidenceWeight.MODERATE,
                description="TestRail milestone association",
            ),
            FieldDefinition(
                name="run_id",
                evidence_weight=EvidenceWeight.MODERATE,
                description="TestRail run identifier reference",
            ),
            FieldDefinition(
                name="status_id",
                evidence_weight=EvidenceWeight.MODERATE,
                description="TestRail status identifier",
            ),
        ],
        # WEAK indicators - common but less specific
        weak_indicators=[
            FieldDefinition(
                name="assignedto_id",
                evidence_weight=EvidenceWeight.WEAK,
                description="TestRail assignment",
            ),
            FieldDefinition(
                name="refs",
                evidence_weight=EvidenceWeight.WEAK,
                description="TestRail references",
            ),
        ],
        # Standard format metadata and confidence parameters
        **get_standard_format_kwargs(UNIQUE_INDICATORS_CONFIDENCE),
    )
