"""Data complexity analysis for format detection optimization."""

from __future__ import annotations

from typing import Any


class ComplexityAnalyzer:
    """Analyzes data complexity to optimize detection algorithms."""

    # Complexity thresholds and limits
    MAX_DATA_SIZE_CHARS = 50000  # Maximum data size in characters
    MAX_NESTING_DEPTH = 25  # Maximum nesting depth for data structures
    MAX_KEY_COUNT = 2000  # Maximum estimated key count
    MIN_UNIQUENESS_RATIO = 0.1  # Minimum uniqueness ratio for large data
    LARGE_DATA_THRESHOLD = 10000  # Threshold for considering data "large"
    SAMPLE_SIZE_FOR_DEPTH_CHECK = 5000  # Characters to sample for depth analysis
    MAX_RECURSION_DEPTH = 10  # Maximum recursion depth for text counting
    DEFAULT_MAX_NESTING_DEPTH = 100  # Default max depth for nesting calculation

    @classmethod
    def assess_data_complexity(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Assess data complexity and provide detailed reasoning.

        This method evaluates data complexity for algorithm selection.
        """
        try:
            # Quick heuristics to identify complex data with detailed reasons
            data_str = str(data)
            data_size = len(data_str)

            if data_size > cls.MAX_DATA_SIZE_CHARS:  # Very large data
                return {
                    "too_complex": True,
                    "reason": (
                        f"Data size ({data_size:,} chars) exceeds limit "
                        f"({cls.MAX_DATA_SIZE_CHARS:,} chars)"
                    ),
                    "recommendation": "Consider breaking data into smaller chunks",
                }

            # Count nesting levels quickly (limit check to prevent hangs)
            max_depth = 0
            current_depth = 0
            # Only check first N chars to prevent hangs
            for char in data_str[: cls.SAMPLE_SIZE_FOR_DEPTH_CHECK]:
                if char in "{[":
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif char in "}]":
                    current_depth -= 1
                if max_depth > cls.MAX_NESTING_DEPTH:  # Very deep nesting
                    return {
                        "too_complex": True,
                        "reason": (
                            f"Nesting depth ({max_depth}) exceeds limit "
                            f"({cls.MAX_NESTING_DEPTH} levels)"
                        ),
                        "recommendation": (
                            "Flatten data structure for better performance"
                        ),
                    }

            # Count total keys (approximate)
            key_count = data_str.count('"') // 2  # Rough estimate
            if key_count > cls.MAX_KEY_COUNT:  # Too many keys
                return {
                    "too_complex": True,
                    "reason": (
                        f"Estimated key count (~{key_count}) exceeds limit "
                        f"({cls.MAX_KEY_COUNT:,} keys)"
                    ),
                    "recommendation": "Reduce data complexity or use batch processing",
                }

            # Check for potential circular references or repetitive patterns
            unique_content_ratio = len(set(data_str.split())) / max(
                1, len(data_str.split())
            )
            # Check for very repetitive data patterns
            is_large = len(data_str) > cls.LARGE_DATA_THRESHOLD
            is_repetitive = unique_content_ratio < cls.MIN_UNIQUENESS_RATIO
            if is_large and is_repetitive:
                return {
                    "too_complex": True,
                    "reason": (
                        f"Highly repetitive data pattern "
                        f"(uniqueness ratio: {unique_content_ratio:.2%})"
                    ),
                    "recommendation": (
                        "Use deduplicated or summarized data representation"
                    ),
                }

            return {
                "too_complex": False,
                "reason": "Data complexity within acceptable limits",
                "stats": {
                    "size": data_size,
                    "max_depth": max_depth,
                    "estimated_keys": key_count,
                    "uniqueness_ratio": unique_content_ratio,
                },
            }

        except Exception as e:
            # If we can't even assess complexity, it's too complex
            return {
                "too_complex": True,
                "reason": f"Unable to assess complexity due to error: {e!s}",
                "recommendation": "Check data format and structure",
            }

    @classmethod
    def calculate_max_nesting_depth(
        cls, data: Any, max_depth: int | None = None
    ) -> int:
        """Calculate maximum nesting depth of data structure."""
        if max_depth is None:
            max_depth = cls.DEFAULT_MAX_NESTING_DEPTH
        if max_depth <= 0:
            return 0

        if isinstance(data, dict):
            if not data:
                return 1
            return 1 + max(
                cls.calculate_max_nesting_depth(v, max_depth - 1) for v in data.values()
            )
        if isinstance(data, list):
            if not data:
                return 1
            return 1 + max(
                cls.calculate_max_nesting_depth(v, max_depth - 1) for v in data
            )
        return 0

    @classmethod
    def calculate_value_type_diversity(cls, data: dict[str, Any]) -> float:
        """Calculate diversity of value types in the data."""
        try:
            all_types = cls._count_types_recursive(data)
            # Normalize: more types = higher diversity (0.0 to 1.0)
            return min(len(all_types) / 10.0, 1.0)
        except (RecursionError, MemoryError):
            return 0.0  # Very complex structure

    @classmethod
    def _count_types_recursive(
        cls, obj: Any, depth: int = 0, visited: set[int] | None = None
    ) -> dict[str, int]:
        """Recursively count types in data structure."""
        if visited is None:
            visited = set()

        # Prevent infinite recursion
        obj_id = id(obj)
        if obj_id in visited or depth > cls.MAX_RECURSION_DEPTH:
            return {}

        visited.add(obj_id)
        type_counts: dict[str, int] = {}

        if isinstance(obj, dict):
            cls._count_dict_types(obj, type_counts, depth, visited)
        elif isinstance(obj, list):
            cls._count_list_types(obj, type_counts, depth, visited)
        else:
            cls._count_simple_type(obj, type_counts)

        return type_counts

    @classmethod
    def _count_dict_types(
        cls,
        obj: dict[str, Any],
        type_counts: dict[str, int],
        depth: int,
        visited: set[int],
    ) -> None:
        """Count types in dictionary values."""
        type_counts["dict"] = type_counts.get("dict", 0) + 1
        for value in obj.values():
            child_counts = cls._count_types_recursive(value, depth + 1, visited.copy())
            cls._merge_type_counts(type_counts, child_counts)

    @classmethod
    def _count_list_types(
        cls, obj: list[Any], type_counts: dict[str, int], depth: int, visited: set[int]
    ) -> None:
        """Count types in list items."""
        type_counts["list"] = type_counts.get("list", 0) + 1
        for item in obj:
            child_counts = cls._count_types_recursive(item, depth + 1, visited.copy())
            cls._merge_type_counts(type_counts, child_counts)

    @classmethod
    def _count_simple_type(cls, obj: Any, type_counts: dict[str, int]) -> None:
        """Count simple (non-container) type."""
        type_name = type(obj).__name__
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

    @classmethod
    def _merge_type_counts(cls, target: dict[str, int], source: dict[str, int]) -> None:
        """Merge type counts from source into target."""
        for type_name, count in source.items():
            target[type_name] = target.get(type_name, 0) + count

    @classmethod
    def calculate_text_density(cls, data: dict[str, Any]) -> float:
        """Calculate the ratio of text content to total data size."""
        try:
            text_chars, total_chars = cls._count_text_recursive(data)
            return text_chars / max(total_chars, 1)
        except (RecursionError, MemoryError):
            return 0.0  # Very complex structure

    @classmethod
    def _count_text_recursive(
        cls, obj: Any, depth: int = 0, visited: set[int] | None = None
    ) -> tuple[int, int]:
        """Recursively count text characters in data structure."""
        if visited is None:
            visited = set()

        # Prevent infinite recursion
        obj_id = id(obj)
        if obj_id in visited or depth > cls.MAX_RECURSION_DEPTH:
            return 0, 0

        visited.add(obj_id)

        if isinstance(obj, str):
            text_len = len(obj)
            return text_len, text_len
        if isinstance(obj, dict):
            return cls._count_dict_chars(obj, depth, visited)
        if isinstance(obj, list):
            return cls._count_list_chars(obj, depth, visited)
        return cls._count_other_chars(obj)

    @classmethod
    def _count_dict_chars(
        cls, obj: dict[str, Any], depth: int, visited: set[int]
    ) -> tuple[int, int]:
        """Count characters in dictionary."""
        text_chars = 0
        total_chars = 0
        for key, value in obj.items():
            key_text, key_total = cls._count_text_recursive(
                str(key), depth + 1, visited.copy()
            )
            val_text, val_total = cls._count_text_recursive(
                value, depth + 1, visited.copy()
            )
            text_chars += key_text + val_text
            total_chars += key_total + val_total
        return text_chars, total_chars

    @classmethod
    def _count_list_chars(
        cls, obj: list[Any], depth: int, visited: set[int]
    ) -> tuple[int, int]:
        """Count characters in list."""
        text_chars = 0
        total_chars = 0
        for item in obj:
            item_text, item_total = cls._count_text_recursive(
                item, depth + 1, visited.copy()
            )
            text_chars += item_text
            total_chars += item_total
        return text_chars, total_chars

    @staticmethod
    def _count_other_chars(obj: Any) -> tuple[int, int]:
        """Count characters in other types."""
        str_repr = str(obj)
        total_chars = len(str_repr)
        # Numbers and simple types don't count as text
        if isinstance(obj, int | float | bool) or obj is None:
            text_chars = 0
        else:
            text_chars = len(str_repr)
        return text_chars, total_chars

    @classmethod
    def calculate_structural_complexity(cls, data: dict[str, Any]) -> float:
        """Calculate overall structural complexity score (0.0 to 1.0)."""
        try:
            # Combine multiple complexity metrics
            nesting_depth = cls.calculate_max_nesting_depth(data)
            type_diversity = cls.calculate_value_type_diversity(data)
            text_density = cls.calculate_text_density(data)

            # Weight the metrics (more nesting = more complex)
            depth_score = min(nesting_depth / 20.0, 1.0)  # Normalize to 0-1
            complexity_score = (
                depth_score * 0.4 + type_diversity * 0.3 + text_density * 0.3
            )

            return min(complexity_score, 1.0)
        except Exception:
            return 1.0  # Assume maximum complexity on error


__all__ = ["ComplexityAnalyzer"]
