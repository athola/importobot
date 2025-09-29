"""String caching utilities to avoid circular imports.

Provides performance optimization for repeated string operations without
creating circular dependencies between modules.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1000)
def cached_string_lower(data_str: str) -> str:
    """Cache string lowercasing operations.

    Args:
        data_str: String to convert to lowercase

    Returns:
        Lowercase version of the string

    Note:
        Uses functools.lru_cache for automatic cache management.
        Maxsize of 1000 should handle most repeated operations.
    """
    return data_str.lower()


def data_to_lower_cached(data: Any) -> str:
    """Convert data to lowercase string with caching.

    This function handles the data-to-string conversion and then
    applies caching to the string lowercasing operation.

    Args:
        data: Data to convert to lowercase string

    Returns:
        Cached lowercase string representation
    """
    # Convert to string first (not cached as this is fast)
    data_str = str(data)

    # For very large strings, use specialized caching
    if len(data_str) > 10000:  # 10KB threshold
        return _cached_large_string_lower(data_str)

    # For normal strings, use direct caching
    return cached_string_lower(data_str)


@lru_cache(maxsize=100)
def _cached_large_string_lower(data_str: str) -> str:
    """Cache large string operations."""
    # For large strings, we still need to perform the conversion
    # The caching helps with repeated operations on the same large string
    return data_str.lower()


def clear_string_cache() -> None:
    """Clear all string caches."""
    cached_string_lower.cache_clear()
    _cached_large_string_lower.cache_clear()


def get_cache_info() -> dict[str, Any]:
    """Get cache statistics."""
    string_info = cached_string_lower.cache_info()
    large_info = _cached_large_string_lower.cache_info()

    # Calculate hit rates safely
    string_total = string_info.hits + string_info.misses
    string_hit_rate = (
        (string_info.hits / string_total * 100) if string_total > 0 else 0.0
    )

    large_total = large_info.hits + large_info.misses
    large_hit_rate = (large_info.hits / large_total * 100) if large_total > 0 else 0.0

    return {
        "string_cache": {
            **string_info._asdict(),
            "hit_rate_percent": round(string_hit_rate, 1),
        },
        "large_string_cache": {
            **large_info._asdict(),
            "hit_rate_percent": round(large_hit_rate, 1),
        },
        "total_operations": string_total + large_total,
        "overall_hit_rate": round(
            (string_info.hits + large_info.hits)
            / max(1, string_total + large_total)
            * 100,
            1,
        ),
    }
