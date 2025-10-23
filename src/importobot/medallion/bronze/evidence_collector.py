"""Evidence collection utilities for modular format detection."""

from __future__ import annotations

import contextlib
import re
from typing import Any

from importobot.medallion.interfaces.enums import EvidenceSource, SupportedFormat
from importobot.utils.regex_cache import get_compiled_pattern

from .context_searcher import ContextSearcher
from .evidence_accumulator import EvidenceItem
from .format_models import EvidenceWeight
from .format_registry import FormatRegistry


class EvidenceCollector:
    """Collect and score evidence for format detection."""

    def __init__(
        self,
        format_registry: FormatRegistry,
        context_searcher: type[ContextSearcher] = ContextSearcher,
    ) -> None:
        """Initialize the EvidenceCollector.

        Args:
            format_registry: Registry containing format definitions
            context_searcher: Type for context searching (default: ContextSearcher)
        """
        self._format_registry = format_registry
        self._context_searcher = context_searcher
        self._format_patterns = self._build_format_patterns()

    def refresh_patterns(self) -> None:
        """Rebuild cached format patterns from the registry."""
        self._format_patterns = self._build_format_patterns()

    def get_patterns(self, format_type: SupportedFormat) -> dict[str, Any]:
        """Return the cached pattern definition for the format."""
        return self._format_patterns.get(format_type, {})

    def get_all_patterns(self) -> dict[SupportedFormat, dict[str, Any]]:
        """Return patterns for all registered formats."""
        return self._format_patterns

    def collect_evidence(
        self, data: dict[str, Any], format_type: SupportedFormat
    ) -> tuple[list[EvidenceItem], float]:
        """Collect evidence for the given format and return items plus total weight.

        Uses proper structural matching: checks for actual keys in the dict
        structure, not substring matches in stringified representation.

        UNIQUE indicators use case-sensitive matching to prevent false positives
        (e.g., "testCase" vs "testcase"). Other indicators use
        case-insensitive matching.
        """
        patterns = self.get_patterns(format_type)
        if not patterns:
            return [], 0.0

        # Extract all keys from nested dict structure (preserve original case)
        all_keys = self._extract_all_keys(data)

        evidence_items: list[EvidenceItem] = []
        # Pass original keys; methods convert to lowercase when needed
        evidence_items.extend(self._collect_required_keys(all_keys, patterns))
        evidence_items.extend(self._collect_optional_keys(all_keys, patterns))
        evidence_items.extend(self._collect_structure_indicators(all_keys, patterns))
        self._collect_field_patterns(evidence_items, all_keys, data, patterns)

        total_weight = sum(item.weight.value for item in evidence_items)
        return evidence_items, total_weight

    def _extract_all_keys(self, data: Any, keys: set[str] | None = None) -> set[str]:
        """Recursively extract all keys from nested dict structure.

        This ensures we check for actual field presence, not substring matches.
        """
        if keys is None:
            keys = set()

        if isinstance(data, dict):
            for key, value in data.items():
                keys.add(key)
                self._extract_all_keys(value, keys)
        elif isinstance(data, list):
            for item in data:
                self._extract_all_keys(item, keys)

        return keys

    def _build_format_patterns(self) -> dict[SupportedFormat, dict[str, Any]]:
        """Construct indicator and pattern definitions for each registered format.

        Stores full field information including weights from format definitions,
        not just field names. This ensures discriminative evidence weighting.
        """
        patterns: dict[SupportedFormat, dict[str, Any]] = {}
        for format_type, format_def in self._format_registry.get_all_formats().items():
            all_fields = format_def.get_all_fields()

            # Store fields with their weights, not just names
            patterns[format_type] = {
                "required_keys": [
                    field.name
                    for field in format_def.unique_indicators
                    + format_def.strong_indicators
                ],
                "optional_keys": [
                    field.name
                    for field in format_def.moderate_indicators
                    + format_def.weak_indicators
                ],
                "required_fields": format_def.unique_indicators
                + format_def.strong_indicators,
                "optional_fields": format_def.moderate_indicators
                + format_def.weak_indicators,
                "structure_fields": format_def.strong_indicators
                + format_def.moderate_indicators,
                "pattern_fields": [field for field in all_fields if field.pattern],
            }
        return patterns

    def _collect_required_keys(
        self, all_keys: set[str], patterns: dict[str, Any]
    ) -> list[EvidenceItem]:
        return self._collect_field_evidence(
            all_keys,
            patterns.get("required_fields", []),
            source=EvidenceSource.REQUIRED_KEY,
            template="Required key '{key}' found",
        )

    def _collect_optional_keys(
        self, all_keys: set[str], patterns: dict[str, Any]
    ) -> list[EvidenceItem]:
        return self._collect_field_evidence(
            all_keys,
            patterns.get("optional_fields", []),
            source=EvidenceSource.OPTIONAL_KEY,
            template="Optional key '{key}' found",
        )

    def _collect_structure_indicators(
        self, all_keys: set[str], patterns: dict[str, Any]
    ) -> list[EvidenceItem]:
        return self._collect_field_evidence(
            all_keys,
            patterns.get("structure_fields", []),
            source=EvidenceSource.STRUCTURE_INDICATOR,
            template="Structure indicator '{key}' found",
        )

    def _collect_field_evidence(
        self,
        all_keys: set[str],
        fields: list[Any],  # List of FieldDefinition objects
        *,
        source: EvidenceSource,
        template: str,
    ) -> list[EvidenceItem]:
        """Collect evidence using actual field definitions with proper weights.

        Uses the EvidenceWeight from format definitions (UNIQUE=5, STRONG=3, etc.)
        instead of hardcoded generic weights. This ensures discriminative evidence.

        Case Sensitivity Strategy (based on format research):
        - UNIQUE indicators: Always case-sensitive (format-specific)
        - STRONG indicators with format-specific patterns: Case-sensitive
          (camelCase like "cycleId", underscores like "suite_id", etc.)
        - Generic indicators (name, status, description): Case-insensitive
        """
        evidence: list[EvidenceItem] = []
        # Only process string keys - non-string keys indicate invalid test data
        all_keys_lower = {k.lower() for k in all_keys if isinstance(k, str)}

        # Generic field names that should use case-insensitive matching
        generic_fields = {
            "name",
            "status",
            "description",
            "priority",
            "version",
            "time",
            "date",
            "user",
            "comment",
            "notes",
            "summary",
        }

        for field in fields:
            field_name_lower = field.name.lower()
            is_generic = field_name_lower in generic_fields

            matched = False

            # Use case-sensitive matching for format-specific indicators
            if field.evidence_weight == EvidenceWeight.UNIQUE or not is_generic:
                if field.name in all_keys:
                    evidence.append(
                        EvidenceItem(
                            source=source,
                            weight=field.evidence_weight,
                            confidence=1.0,
                            details=template.format(key=field.name),
                        )
                    )
                    matched = True
            # Use case-insensitive matching only for truly generic fields
            elif field_name_lower in all_keys_lower:
                evidence.append(
                    EvidenceItem(
                        source=source,
                        weight=field.evidence_weight,
                        confidence=1.0,
                        details=template.format(key=field.name),
                    )
                )
                matched = True

            if not matched and getattr(field, "is_required", False):
                evidence.append(
                    EvidenceItem(
                        source=EvidenceSource.missing_variant(source),
                        weight=field.evidence_weight,
                        confidence=0.0,
                        details=f"Required key '{field.name}' missing",
                    )
                )
        return evidence

    def _collect_field_patterns(
        self,
        evidence_items: list[EvidenceItem],
        all_keys: set[str],
        data: dict[str, Any],
        patterns: dict[str, Any],
    ) -> None:
        """Collect pattern-based evidence using field definitions.

        First checks if the field key exists in the data, then validates
        the pattern. Uses actual field weights from format definitions.
        """
        pattern_fields = patterns.get("pattern_fields", [])
        # Only process string keys - non-string keys indicate invalid test data
        all_keys_lower = {k.lower() for k in all_keys if isinstance(k, str)}
        data_str = str(data) if data else ""

        for field in pattern_fields:
            # First check if the field actually exists (case-insensitive for patterns)
            if not field.pattern or field.name.lower() not in all_keys_lower:
                continue

            existing_item = self._find_evidence_item(evidence_items, field.name)
            normalized_pattern = field.pattern.strip("^").strip("$").lower()
            if normalized_pattern == field.name.lower():
                matched = True
                compiled_pattern = None
            else:
                try:
                    compiled_pattern = self._get_compiled_regex(field.pattern)
                except re.error:
                    continue
                field_values = self._extract_field_values(data, field.name)
                matched = any(
                    isinstance(value, str) and compiled_pattern.fullmatch(value)
                    for value in field_values
                )

            if matched or (compiled_pattern and compiled_pattern.search(data_str)):
                if existing_item:
                    existing_item.confidence = max(existing_item.confidence, 1.0)
                evidence_items.append(
                    EvidenceItem(
                        source=EvidenceSource.FIELD_PATTERN,
                        weight=field.evidence_weight,
                        confidence=1.0,  # Pattern matched
                        details=f"Field pattern '{field.name}' matched",
                    )
                )
            else:
                if existing_item:
                    with contextlib.suppress(ValueError):
                        evidence_items.remove(existing_item)
                evidence_items.append(
                    EvidenceItem(
                        source=EvidenceSource.FIELD_PATTERN_MISMATCH,
                        weight=field.evidence_weight,
                        confidence=0.0,
                        details=f"Field pattern '{field.name}' mismatch",
                    )
                )

    @staticmethod
    def _get_compiled_regex(pattern: str) -> re.Pattern[str]:
        """Return a cached, case-insensitive compiled regex."""
        return get_compiled_pattern(pattern, re.IGNORECASE)

    @staticmethod
    def _find_evidence_item(
        evidence_items: list[EvidenceItem], field_name: str
    ) -> EvidenceItem | None:
        """Find an existing evidence item associated with the given field."""
        target = f"'{field_name}'"
        for item in reversed(evidence_items):
            if target in item.details:
                return item
        return None

    def _extract_field_values(self, data: Any, field_name: str) -> list[Any]:
        """Extract all values associated with a given field name."""
        values: list[Any] = []

        if isinstance(data, dict):
            for key, value in data.items():
                if key == field_name:
                    values.append(value)
                values.extend(self._extract_field_values(value, field_name))
        elif isinstance(data, list):
            for item in data:
                values.extend(self._extract_field_values(item, field_name))

        return values


__all__ = ["EvidenceCollector"]
