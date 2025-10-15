"""Enums for Medallion architecture."""

from enum import Enum


class SupportedFormat(Enum):
    """Supported test format types."""

    ZEPHYR = "zephyr"
    TESTLINK = "testlink"
    JIRA_XRAY = "jira_xray"
    TESTRAIL = "testrail"
    GENERIC = "generic"
    UNKNOWN = "unknown"


class DataQuality(Enum):
    """Data quality assessment levels for medallion layers."""

    EXCELLENT = "excellent"  # >95% quality score
    GOOD = "good"  # 80-95% quality score
    FAIR = "fair"  # 60-80% quality score
    POOR = "poor"  # <60% quality score
    UNKNOWN = "unknown"  # Unable to assess


class ProcessingStatus(Enum):
    """Processing status for layer operations."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EvidenceSource(str, Enum):
    """Evidence source types for format detection."""

    REQUIRED_KEY = "required_key"
    OPTIONAL_KEY = "optional_key"
    STRUCTURE_INDICATOR = "structure_indicator"
    FIELD_PATTERN = "field_pattern"
    FIELD_PATTERN_MISMATCH = "field_pattern_mismatch"
    TEST_DATA_INDICATOR = "test_data_indicator"

    # Missing variants
    REQUIRED_KEY_MISSING = "required_key_missing"
    OPTIONAL_KEY_MISSING = "optional_key_missing"
    STRUCTURE_INDICATOR_MISSING = "structure_indicator_missing"

    def is_missing(self) -> bool:
        """Check if this source indicates a missing required field."""
        return self.value.endswith("_missing")

    @classmethod
    def missing_variant(cls, base_source: "EvidenceSource") -> "EvidenceSource":
        """Create the missing variant of a base evidence source."""
        missing_map = {
            cls.REQUIRED_KEY: cls.REQUIRED_KEY_MISSING,
            cls.OPTIONAL_KEY: cls.OPTIONAL_KEY_MISSING,
            cls.STRUCTURE_INDICATOR: cls.STRUCTURE_INDICATOR_MISSING,
        }
        return missing_map.get(base_source, base_source)
