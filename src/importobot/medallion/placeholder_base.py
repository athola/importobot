"""Base functionality for medallion layer placeholder implementations.

This module provides common placeholder functionality for Silver and Gold layers
to eliminate code duplication while maintaining clear API contracts.
"""

from __future__ import annotations

from typing import Any

from importobot.medallion.interfaces.data_models import DataLineage
from importobot.medallion.interfaces.records import BronzeRecord, RecordMetadata


class PlaceholderMixin:
    """Mixin providing common placeholder functionality for unimplemented layers."""

    def _not_implemented_error(
        self, method_name: str, milestone: str
    ) -> NotImplementedError:
        """Create a consistent NotImplementedError for placeholder methods."""
        return NotImplementedError(
            f"{self.__class__.__name__} {method_name} pending {milestone}"
        )

    def _placeholder_record_metadata(self, _record_id: str) -> RecordMetadata | None:
        """Return placeholder implementation for get_record_metadata."""
        return None

    def _placeholder_record_lineage(self, _record_id: str) -> DataLineage | None:
        """Return placeholder implementation for get_record_lineage."""
        return None

    def _placeholder_validate_bronze_data(
        self, _data: dict[str, Any], layer_name: str, milestone: str
    ) -> dict[str, Any]:
        """Return placeholder implementation for validate_bronze_data."""
        return {
            "is_valid": False,
            "error_count": 0,
            "warning_count": 1,
            "issues": [f"{layer_name} layer validation pending {milestone}"],
            "quality_score": 0.0,
            "completeness_score": 0.0,
            "consistency_score": 0.0,
            "validity_score": 0.0,
        }

    def _placeholder_get_bronze_records(
        self,
        _filter_criteria: dict[str, Any] | None = None,
        _limit: int | None = None,
    ) -> list[BronzeRecord]:
        """Return placeholder implementation for get_bronze_records."""
        return []


__all__ = ["PlaceholderMixin"]
