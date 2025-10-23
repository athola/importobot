"""Unit tests for the EvidenceCollector utility."""

from __future__ import annotations

import sys
import types
import unittest
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

if TYPE_CHECKING:
    # This is a stub for type checking purposes only
    class FormatDetector:
        """Stub class for type checking."""


# pylint: disable=wrong-import-position
from importobot.medallion.bronze.evidence_collector import (
    EvidenceCollector,
)
from importobot.medallion.bronze.format_models import (
    EvidenceWeight,
    FieldDefinition,
    FormatDefinition,
)
from importobot.medallion.bronze.format_registry import (
    FormatRegistry,
)
from importobot.medallion.interfaces.enums import (
    EvidenceSource,
    SupportedFormat,
)

# Avoid importing heavy optional dependencies when the bronze package is initialised.
if "importobot.medallion.bronze.format_detector" not in sys.modules:
    # Create a proper stub module with correct typing
    class _FormatDetectorStub:
        pass

    stub_module = types.ModuleType("importobot.medallion.bronze.format_detector")
    stub_module.FormatDetector = _FormatDetectorStub  # type: ignore[attr-defined]
    sys.modules["importobot.medallion.bronze.format_detector"] = stub_module

try:
    import numpy

    _ = numpy  # Mark as used to avoid F401
except ImportError as exc:  # pragma: no cover - optional dependency guard
    raise unittest.SkipTest(
        "numpy dependency required for EvidenceCollector tests"
    ) from exc


class TestEvidenceCollectorIntegration(unittest.TestCase):
    """Validate evidence collection against the real format registry."""

    def setUp(self) -> None:
        self.collector = EvidenceCollector(FormatRegistry())
        # Use sample Zephyr test data for evidence collection
        data = {
            "testCase": "Login Test Case",
            "execution": {"id": "EXEC-001", "status": "PASS"},
            "cycle": {"id": "CYCLE-001", "name": "Sprint 1 Testing"},
            "project": "Web Application",
            "version": "v1.0",
        }
        evidence_items, total_weight = self.collector.collect_evidence(
            data, SupportedFormat.ZEPHYR
        )

        assert total_weight > 0
        assert any(
            item.source == EvidenceSource.REQUIRED_KEY for item in evidence_items
        ), "Expected required_key evidence for Zephyr data"

    def test_collect_evidence_returns_empty_for_unknown_format(self) -> None:
        """Unsupported formats should return empty evidence list."""
        # Create a fresh collector to ensure no state from previous tests
        fresh_collector = EvidenceCollector(FormatRegistry())
        evidence_items, total_weight = fresh_collector.collect_evidence(
            {"foo": "bar"}, SupportedFormat.UNKNOWN
        )

        assert evidence_items == []
        assert total_weight == 0


class TestEvidenceCollectorRefresh(unittest.TestCase):
    """Ensure EvidenceCollector rebuilds cached patterns when requested."""

    def setUp(self) -> None:
        self.mock_registry = MagicMock()

        self.initial_definition = FormatDefinition(
            name="Initial",
            format_type=SupportedFormat.UNKNOWN,
            description="Initial mock definition",
            unique_indicators=[
                FieldDefinition(
                    name="initial_key",
                    evidence_weight=EvidenceWeight.UNIQUE,
                    is_required=True,
                )
            ],
        )
        self.updated_definition = FormatDefinition(
            name="Updated",
            format_type=SupportedFormat.UNKNOWN,
            description="Updated mock definition",
            unique_indicators=[
                FieldDefinition(
                    name="updated_key",
                    evidence_weight=EvidenceWeight.UNIQUE,
                    is_required=True,
                )
            ],
        )

        self.mock_registry.get_all_formats.return_value = {
            SupportedFormat.UNKNOWN: self.initial_definition
        }
        self.collector = EvidenceCollector(self.mock_registry)

    def test_patterns_rebuilt_after_refresh(self) -> None:
        """refresh_patterns should rebuild internal cache from the registry."""
        initial_patterns = self.collector.get_patterns(SupportedFormat.UNKNOWN)
        assert "initial_key" in initial_patterns["required_keys"]

        # Update the registry and refresh
        self.mock_registry.get_all_formats.return_value = {
            SupportedFormat.UNKNOWN: self.updated_definition
        }
        self.collector.refresh_patterns()

        refreshed_patterns = self.collector.get_patterns(SupportedFormat.UNKNOWN)
        assert "updated_key" in refreshed_patterns["required_keys"]
        assert "initial_key" not in refreshed_patterns["required_keys"]


if __name__ == "__main__":
    unittest.main()
