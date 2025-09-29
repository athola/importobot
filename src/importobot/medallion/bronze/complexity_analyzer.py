"""Data complexity analysis for format detection optimization."""

from __future__ import annotations

from typing import Any, Dict


class ComplexityAnalyzer:
    """Analyzes data complexity to optimize detection algorithms."""

    @staticmethod
    def assess_data_complexity(data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess data complexity and provide detailed reasoning.

        This method evaluates data complexity for algorithm selection.
        """
        try:
            # Quick heuristics to identify complex data with detailed reasons
            data_str = str(data)
            data_size = len(data_str)

            if data_size > 50000:  # Very large data
                return {
                    "too_complex": True,
                    "reason": (
                        f"Data size ({data_size:,} chars) exceeds limit (50,000 chars)"
                    ),
                    "recommendation": "Consider breaking data into smaller chunks",
                }

            # Count nesting levels quickly (limit check to prevent hangs)
            max_depth = 0
            current_depth = 0
            for char in data_str[:5000]:  # Only check first 5000 chars
                if char in "{[":
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif char in "}]":
                    current_depth -= 1
                if max_depth > 25:  # Very deep nesting
                    return {
                        "too_complex": True,
                        "reason": (
                            f"Nesting depth ({max_depth}) exceeds limit (25 levels)"
                        ),
                        "recommendation": (
                            "Flatten data structure for better performance"
                        ),
                    }

            # Count total keys (approximate)
            key_count = data_str.count('"') // 2  # Rough estimate
            if key_count > 2000:  # Too many keys
                return {
                    "too_complex": True,
                    "reason": (
                        f"Estimated key count (~{key_count}) exceeds limit (2,000 keys)"
                    ),
                    "recommendation": "Reduce data complexity or use batch processing",
                }

            # Check for potential circular references or repetitive patterns
            unique_content_ratio = len(set(data_str.split())) / max(
                1, len(data_str.split())
            )
            if len(data_str) > 10000 and unique_content_ratio < 0.1:  # Very repetitive
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
                "reason": f"Unable to assess complexity due to error: {str(e)}",
                "recommendation": "Check data format and structure",
            }

    @staticmethod
    def calculate_max_nesting_depth(data: Any, max_depth: int = 100) -> int:
        """Calculate maximum nesting depth of data structure."""
        if max_depth <= 0:
            return 0

        if isinstance(data, dict):
            if not data:
                return 1
            return 1 + max(
                ComplexityAnalyzer.calculate_max_nesting_depth(v, max_depth - 1)
                for v in data.values()
            )
        if isinstance(data, list):
            if not data:
                return 1
            return 1 + max(
                ComplexityAnalyzer.calculate_max_nesting_depth(v, max_depth - 1)
                for v in data
            )
        return 0

    @staticmethod
    def calculate_value_type_diversity(data: Dict[str, Any]) -> float:  # noqa: C901
        """Calculate diversity of value types in the data."""

        def count_types(
            obj: Any, depth: int = 0, visited: set | None = None
        ) -> Dict[str, int]:
            if visited is None:
                visited = set()

            # Prevent infinite recursion
            obj_id = id(obj)
            if obj_id in visited or depth > 10:
                return {}

            visited.add(obj_id)
            type_counts: Dict[str, int] = {}

            if isinstance(obj, dict):
                type_counts["dict"] = type_counts.get("dict", 0) + 1
                for value in obj.values():
                    child_counts = count_types(value, depth + 1, visited.copy())
                    for type_name, count in child_counts.items():
                        type_counts[type_name] = type_counts.get(type_name, 0) + count
            elif isinstance(obj, list):
                type_counts["list"] = type_counts.get("list", 0) + 1
                for item in obj:
                    child_counts = count_types(item, depth + 1, visited.copy())
                    for type_name, count in child_counts.items():
                        type_counts[type_name] = type_counts.get(type_name, 0) + count
            else:
                type_name = type(obj).__name__
                type_counts[type_name] = type_counts.get(type_name, 0) + 1

            return type_counts

        try:
            all_types = count_types(data)
            # Normalize: more types = higher diversity (0.0 to 1.0)
            return min(len(all_types) / 10.0, 1.0)
        except (RecursionError, MemoryError):
            return 0.0  # Very complex structure

    @staticmethod
    def calculate_text_density(data: Dict[str, Any]) -> float:
        """Calculate the ratio of text content to total data size."""
        try:
            text_chars, total_chars = ComplexityAnalyzer._count_text_recursive(data)
            return text_chars / max(total_chars, 1)
        except (RecursionError, MemoryError):
            return 0.0  # Very complex structure

    @staticmethod
    def _count_text_recursive(
        obj: Any, depth: int = 0, visited: set | None = None
    ) -> tuple[int, int]:
        """Recursively count text characters in data structure."""
        if visited is None:
            visited = set()

        # Prevent infinite recursion
        obj_id = id(obj)
        if obj_id in visited or depth > 10:
            return 0, 0

        visited.add(obj_id)

        if isinstance(obj, str):
            return ComplexityAnalyzer._count_string_chars(obj)
        if isinstance(obj, dict):
            return ComplexityAnalyzer._count_dict_chars(obj, depth, visited)
        if isinstance(obj, list):
            return ComplexityAnalyzer._count_list_chars(obj, depth, visited)
        return ComplexityAnalyzer._count_other_chars(obj)

    @staticmethod
    def _count_string_chars(text: str) -> tuple[int, int]:
        """Count characters in string."""
        text_len = len(text)
        return text_len, text_len

    @staticmethod
    def _count_dict_chars(obj: dict, depth: int, visited: set) -> tuple[int, int]:
        """Count characters in dictionary."""
        text_chars = 0
        total_chars = 0
        for key, value in obj.items():
            key_text, key_total = ComplexityAnalyzer._count_text_recursive(
                str(key), depth + 1, visited.copy()
            )
            val_text, val_total = ComplexityAnalyzer._count_text_recursive(
                value, depth + 1, visited.copy()
            )
            text_chars += key_text + val_text
            total_chars += key_total + val_total
        return text_chars, total_chars

    @staticmethod
    def _count_list_chars(obj: list, depth: int, visited: set) -> tuple[int, int]:
        """Count characters in list."""
        text_chars = 0
        total_chars = 0
        for item in obj:
            item_text, item_total = ComplexityAnalyzer._count_text_recursive(
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
        if isinstance(obj, (int, float, bool)) or obj is None:
            text_chars = 0
        else:
            text_chars = len(str_repr)
        return text_chars, total_chars

    @staticmethod
    def calculate_structural_complexity(data: Dict[str, Any]) -> float:
        """Calculate overall structural complexity score (0.0 to 1.0)."""
        try:
            # Combine multiple complexity metrics
            nesting_depth = ComplexityAnalyzer.calculate_max_nesting_depth(data)
            type_diversity = ComplexityAnalyzer.calculate_value_type_diversity(data)
            text_density = ComplexityAnalyzer.calculate_text_density(data)

            # Weight the metrics (more nesting = more complex)
            depth_score = min(nesting_depth / 20.0, 1.0)  # Normalize to 0-1
            complexity_score = (
                depth_score * 0.4 + type_diversity * 0.3 + text_density * 0.3
            )

            return min(complexity_score, 1.0)
        except Exception:
            return 1.0  # Assume maximum complexity on error


__all__ = ["ComplexityAnalyzer"]
