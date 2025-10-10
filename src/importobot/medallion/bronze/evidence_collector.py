"""Evidence collection utilities for modular format detection."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Tuple

from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.utils.regex_cache import get_compiled_pattern
from importobot.utils.string_cache import data_to_lower_cached

from .context_searcher import ContextSearcher
from .evidence_accumulator import EvidenceItem
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

    def get_patterns(self, format_type: SupportedFormat) -> Dict[str, Any]:
        """Return the cached pattern definition for the format."""
        return self._format_patterns.get(format_type, {})

    def get_all_patterns(self) -> Dict[SupportedFormat, Dict[str, Any]]:
        """Return patterns for all registered formats."""
        return self._format_patterns

    def collect_evidence(
        self, data: Dict[str, Any], format_type: SupportedFormat
    ) -> Tuple[List[EvidenceItem], float]:
        """Collect evidence for the given format and return items plus total weight."""
        patterns = self.get_patterns(format_type)
        if not patterns:
            return [], 0.0

        data_str = str(data) if data else ""
        data_str_lower = data_to_lower_cached(data_str)

        evidence_items: List[EvidenceItem] = []
        evidence_items.extend(self._collect_required_keys(data_str_lower, patterns))
        evidence_items.extend(self._collect_optional_keys(data_str_lower, patterns))
        evidence_items.extend(
            self._collect_structure_indicators(data_str_lower, patterns)
        )
        evidence_items.extend(
            self._collect_field_patterns(data_str, data_str_lower, patterns)
        )

        total_weight = sum(item.weight for item in evidence_items)
        return evidence_items, total_weight

    def _build_format_patterns(self) -> Dict[SupportedFormat, Dict[str, Any]]:
        """Construct indicator and pattern definitions for each registered format."""
        patterns: Dict[SupportedFormat, Dict[str, Any]] = {}
        for format_type, format_def in self._format_registry.get_all_formats().items():
            all_fields = format_def.get_all_fields()
            patterns[format_type] = {
                "required_keys": [
                    field.name
                    for field in (
                        format_def.unique_indicators + format_def.strong_indicators
                    )
                ],
                "optional_keys": [
                    field.name
                    for field in (
                        format_def.moderate_indicators + format_def.weak_indicators
                    )
                ],
                "structure_indicators": [
                    field.name
                    for field in (
                        format_def.strong_indicators + format_def.moderate_indicators
                    )
                ],
                "field_patterns": {
                    field.name: field.pattern for field in all_fields if field.pattern
                },
            }
        return patterns

    def _collect_required_keys(
        self, data_str_lower: str, patterns: Dict[str, Any]
    ) -> List[EvidenceItem]:
        return self._collect_key_evidence(
            data_str_lower,
            patterns.get("required_keys", []),
            source="required_key",
            weight_category="required",
            template="Required key '{key}' found",
        )

    def _collect_optional_keys(
        self, data_str_lower: str, patterns: Dict[str, Any]
    ) -> List[EvidenceItem]:
        return self._collect_key_evidence(
            data_str_lower,
            patterns.get("optional_keys", []),
            source="optional_key",
            weight_category="optional",
            template="Optional key '{key}' found",
        )

    def _collect_structure_indicators(
        self, data_str_lower: str, patterns: Dict[str, Any]
    ) -> List[EvidenceItem]:
        return self._collect_key_evidence(
            data_str_lower,
            patterns.get("structure_indicators", []),
            source="structure_indicator",
            weight_category="structure",
            template="Structure indicator '{key}' found",
        )

    def _collect_key_evidence(
        self,
        data_str_lower: str,
        keys: Iterable[str],
        *,
        source: str,
        weight_category: str,
        template: str,
    ) -> List[EvidenceItem]:
        evidence: List[EvidenceItem] = []
        for key in keys:
            if key.lower() in data_str_lower:
                weight, confidence = self._context_searcher.get_evidence_weight_for_key(
                    key, weight_category
                )
                evidence.append(
                    EvidenceItem(
                        source=source,
                        weight=weight,
                        confidence=confidence,
                        details=template.format(key=key),
                    )
                )
        return evidence

    def _collect_field_patterns(
        self, data_str: str, data_str_lower: str, patterns: Dict[str, Any]
    ) -> List[EvidenceItem]:
        evidence: List[EvidenceItem] = []
        field_patterns = patterns.get("field_patterns", {})

        for field_name, pattern in field_patterns.items():
            if not pattern or field_name.lower() not in data_str_lower:
                continue

            try:
                compiled_pattern = self._get_compiled_regex(pattern)
            except re.error:
                continue

            if compiled_pattern.search(data_str):
                weight, confidence = self._context_searcher.get_evidence_weight_for_key(
                    field_name, "pattern"
                )
                evidence.append(
                    EvidenceItem(
                        source="field_pattern",
                        weight=weight,
                        confidence=confidence,
                        details=f"Field pattern '{field_name}' matched",
                    )
                )

        return evidence

    @staticmethod
    def _get_compiled_regex(pattern: str) -> re.Pattern[str]:
        """Return a cached, case-insensitive compiled regex."""
        return get_compiled_pattern(pattern, re.IGNORECASE)


__all__ = ["EvidenceCollector"]
