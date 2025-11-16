"""String caching utilities to avoid circular imports.

Optimizes performance for repeated string operations.
"""

from __future__ import annotations

import os
from functools import lru_cache
from threading import Lock
from typing import Any, ClassVar


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

    Handles data-to-string conversion and applies caching to lowercasing.

    Args:
        data: Data to convert to lowercase string

    Returns:
        Cached lowercase string representation
    """
    result = cached_string_lower(str(data))
    _increment_operation_counter()
    return result


def clear_string_cache() -> None:
    """Clear all string caches."""
    cached_string_lower.cache_clear()
    _CacheState.reset()


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


class _CacheState:
    """Holds mutable state for the string cache."""

    lock: ClassVar[Lock] = Lock()
    operation_count: ClassVar[int] = 0
    clear_threshold: ClassVar[int] = int(
        os.getenv("IMPORTOBOT_STRING_CACHE_CLEAR_THRESHOLD", "0")
    )

    @classmethod
    def reset(cls) -> None:
        """Reset the internal operation counter for the cache."""
        cls.operation_count = 0


def _increment_operation_counter() -> None:
    """Increment the string-cache operation counter and evict when threshold is met."""
    if _CacheState.clear_threshold <= 0:
        return
    with _CacheState.lock:
        _CacheState.operation_count += 1
        if _CacheState.operation_count >= _CacheState.clear_threshold:
            cached_string_lower.cache_clear()
            _CacheState.reset()
