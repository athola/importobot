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
