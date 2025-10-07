"""Performance optimization service with caching and lazy evaluation.

Addresses performance bottlenecks identified in the staff review:
- Repeated string operations (str(data).lower())
- JSON serialization without caching
- Expensive computation repetition
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from typing import Any, Dict, Optional
from weakref import WeakKeyDictionary

from importobot.utils.logging import setup_logger

logger = setup_logger(__name__)


class PerformanceCache:
    """Centralized caching service for expensive operations."""

    def __init__(self, max_cache_size: int = 1000):
        """Initialize performance cache.

        Args:
            max_cache_size: Maximum number of items to cache
        """
        self.max_cache_size = max_cache_size
        self._string_cache: Dict[str, str] = {}
        self._json_cache: Dict[str, str] = {}
        self._object_cache: WeakKeyDictionary = WeakKeyDictionary()
        self._cache_hits = 0
        self._cache_misses = 0
        self._string_ops_cache: Dict[str, Any] = {}
        logger.info("Initialized PerformanceCache with max_size=%d", max_cache_size)

    def get_cached_string_lower(self, data: Any) -> str:
        """Get cached lowercase string representation.

        This replaces the expensive str(data).lower() pattern found across
        5 modules with O(n) conversion on every format detection call.

        Args:
            data: Data to convert to lowercase string

        Returns:
            Cached lowercase string representation
        """
        # Create a cache key from the data
        cache_key = self._create_data_hash(data)

        # Check cache first
        if cache_key in self._string_cache:
            self._cache_hits += 1
            return self._string_cache[cache_key]

        # Cache miss - compute and store
        self._cache_misses += 1
        result = str(data).lower()

        # Manage cache size
        if len(self._string_cache) >= self.max_cache_size:
            self._evict_oldest_string_entry()

        self._string_cache[cache_key] = result
        return result

    def get_cached_json_string(self, data: Any) -> str:
        """Get cached JSON string representation.

        Addresses repeated JSON serialization without caching across 17 modules.

        Args:
            data: Data to serialize to JSON

        Returns:
            Cached JSON string representation
        """
        cache_key = self._create_data_hash(data)

        if cache_key in self._json_cache:
            self._cache_hits += 1
            return self._json_cache[cache_key]

        self._cache_misses += 1
        result = json.dumps(data, sort_keys=True, separators=(",", ":"))

        if len(self._json_cache) >= self.max_cache_size:
            self._evict_oldest_json_entry()

        self._json_cache[cache_key] = result
        return result

    def cache_object_attribute(self, obj: Any, attribute: str, value: Any) -> None:
        """Cache computed attribute for an object.

        Args:
            obj: Object to cache attribute for
            attribute: Attribute name
            value: Computed value to cache
        """
        if obj not in self._object_cache:
            self._object_cache[obj] = {}
        self._object_cache[obj][attribute] = value

    def get_cached_object_attribute(self, obj: Any, attribute: str) -> Optional[Any]:
        """Get cached attribute for an object.

        Args:
            obj: Object to get cached attribute for
            attribute: Attribute name

        Returns:
            Cached value if available, None otherwise
        """
        if obj in self._object_cache and attribute in self._object_cache[obj]:
            self._cache_hits += 1
            return self._object_cache[obj][attribute]

        self._cache_misses += 1
        return None

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._string_cache.clear()
        self._json_cache.clear()
        self._object_cache.clear()
        logger.info("Performance caches cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "string_cache_size": len(self._string_cache),
            "json_cache_size": len(self._json_cache),
            "object_cache_size": len(self._object_cache),
            "max_cache_size": self.max_cache_size,
        }

    def _create_data_hash(self, data: Any) -> str:
        """Create a hash key for data caching."""
        if isinstance(data, dict):
            # Sort keys for consistent hashing
            data_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
        else:
            data_str = str(data)

        return hashlib.blake2b(data_str.encode()).hexdigest()[:24]

    def _evict_oldest_string_entry(self) -> None:
        """Evict the oldest entry from string cache (simple FIFO)."""
        if self._string_cache:
            oldest_key = next(iter(self._string_cache))
            del self._string_cache[oldest_key]

    def _evict_oldest_json_entry(self) -> None:
        """Evict the oldest entry from JSON cache (simple FIFO)."""
        if self._json_cache:
            oldest_key = next(iter(self._json_cache))
            del self._json_cache[oldest_key]


class LazyEvaluator:
    """Lazy evaluation patterns for expensive computations."""

    def __init__(self, cache: Optional[PerformanceCache] = None):
        """Initialize lazy evaluator.

        Args:
            cache: Optional performance cache to use
        """
        self.cache = cache or PerformanceCache()
        self._string_ops_cache: "OrderedDict[str, Any]" = OrderedDict()

    def lazy_format_detection(
        self, data: Dict[str, Any], format_detector_func: Any
    ) -> Any:
        """Lazy format detection with caching.

        Args:
            data: Data to analyze
            format_detector_func: Function to call for format detection

        Returns:
            Lazy-evaluated format detection result
        """

        def _detect() -> Any:
            # Check cache first
            cached_result = self.cache.get_cached_object_attribute(
                data, "format_detection"
            )
            if cached_result is not None:
                return cached_result

            # Compute and cache
            result = format_detector_func(data)
            self.cache.cache_object_attribute(data, "format_detection", result)
            return result

        return _detect

    def cached_string_operations(self, data_hash: str, operation: str) -> Any:
        """Cache string operations with true LRU eviction.

        Args:
            data_hash: Hash of the data
            operation: String operation type

        Returns:
            Cached result of string operation
        """
        # Use instance-level cache to avoid memory leaks from lru_cache on methods
        cache_key = f"{data_hash}_{operation}"

        # Check if key exists and move to end (mark as recently used)
        if cache_key in self._string_ops_cache:
            self._string_ops_cache.move_to_end(cache_key)
            return self._string_ops_cache[cache_key]

        # Check cache size and evict LRU entries if needed
        if len(self._string_ops_cache) > 500:
            # Remove least recently used entries (first 100 entries in OrderedDict)
            for _ in range(100):
                if self._string_ops_cache:
                    self._string_ops_cache.popitem(last=False)

        # Cache miss - caller handles computation
        return None


# Global performance cache instance
_global_cache: Optional[PerformanceCache] = None


def get_performance_cache() -> PerformanceCache:
    """Get the global performance cache instance."""
    global _global_cache  # pylint: disable=global-statement
    if _global_cache is None:
        _global_cache = PerformanceCache()
    return _global_cache


def cached_string_lower(data: Any) -> str:
    """Global function for cached string lowercasing.

    This can replace str(data).lower() calls throughout the codebase.
    """
    return get_performance_cache().get_cached_string_lower(data)


def cached_json_dumps(data: Any) -> str:
    """Global function for cached JSON serialization."""
    return get_performance_cache().get_cached_json_string(data)
