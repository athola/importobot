"""Lazy loading utilities for efficient data management."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


class LazyDataLoader:
    """Efficient loader for large data structures with caching."""

    @staticmethod
    @lru_cache(maxsize=32)
    def load_templates(template_type: str) -> Dict[str, Any]:
        """Load templates from external files with caching."""
        data_dir = Path(__file__).parent.parent / "data" / "templates"
        template_file = data_dir / f"{template_type}.json"

        if template_file.exists():
            with open(template_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        return {}

    @staticmethod
    @lru_cache(maxsize=16)
    def load_keyword_mappings(library_type: str) -> Dict[str, Any]:
        """Load keyword mappings from external files."""
        data_dir = Path(__file__).parent.parent / "data" / "keywords"
        mapping_file = data_dir / f"{library_type}_mappings.json"

        if mapping_file.exists():
            with open(mapping_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        return {}

    @staticmethod
    def create_summary_comment(
        data_structure: Dict[str, Any], max_items: int = 3
    ) -> str:
        """Generate summary comments for large data structures."""
        if not data_structure:
            return "# Empty data structure"

        keys = list(data_structure.keys())[:max_items]
        key_summary = ", ".join(keys)
        total_count = len(data_structure)

        if total_count > max_items:
            key_summary += f"... ({total_count} total items)"

        return f"# Data structure with: {key_summary}"
