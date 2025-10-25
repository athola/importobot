"""Format definitions for test management systems.

This package contains pluggable format definitions that allow the Bronze layer
to identify and handle diverse test management data sources without code changes.

Each format definition includes:
- Unique indicators (highest confidence)
- Strong indicators (system-specific features)
- Moderate indicators (common patterns)
- Weak indicators (supplementary evidence)

Format definitions are based on research into:
- Zephyr for JIRA (execution cycles, separate data model)
- Xray for JIRA (tests as JIRA issues, evidence attachments)
- TestRail (hierarchical structure, independent platform)
- TestLink (XML-based, suite-centric)
- Generic (default for unsupported formats)
"""

from .generic_format import create_generic_format
from .testlink_format import create_testlink_format
from .testrail_format import create_testrail_format
from .unknown_format import create_placeholder_format, create_unknown_format
from .xray_format import create_xray_format
from .zephyr_format import create_zephyr_format

__all__ = [
    "create_generic_format",
    "create_placeholder_format",
    "create_testlink_format",
    "create_testrail_format",
    "create_unknown_format",
    "create_xray_format",
    "create_zephyr_format",
]
