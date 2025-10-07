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
    return cached_string_lower(str(data))


def clear_string_cache() -> None:
    """Clear all string caches."""
    cached_string_lower.cache_clear()


def get_cache_info() -> dict[str, Any]:
    """Get cache statistics."""
    cache_info = cached_string_lower.cache_info()

    # Calculate hit rate safely
    total = cache_info.hits + cache_info.misses
    hit_rate = (cache_info.hits / total * 100) if total > 0 else 0.0

    return {
        "cache": {
            **cache_info._asdict(),
            "hit_rate_percent": round(hit_rate, 1),
        },
    }
