"""Performance optimization service with caching and lazy evaluation.

Addresses performance bottlenecks identified in the staff review:
- Repeated string operations (str(data).lower())
- JSON serialization without caching
- Expensive computation repetition
"""

from __future__ import annotations

import importlib
import json
import time
from collections import OrderedDict
from collections.abc import Hashable
from dataclasses import dataclass
from typing import Any, Protocol, cast
from weakref import WeakKeyDictionary

from importobot.config import _int_from_env
from importobot.telemetry import TelemetryClient, get_telemetry_client
from importobot.utils.logging import get_logger


class _NullTelemetry:
    """A no-op telemetry client for when telemetry is disabled."""

    def record_cache_metrics(  # pylint: disable=unused-argument
        self,
        cache_name: str,
        *,
        hits: int,
        misses: int,
        extras: dict[str, Any] | None = None,
    ) -> None:
        return None


logger = get_logger(__name__)


DEFAULT_MAX_SIZE = _int_from_env(
    "IMPORTOBOT_PERFORMANCE_CACHE_MAX_SIZE", 1000, minimum=1
)
DEFAULT_TTL_SECONDS = _int_from_env(
    "IMPORTOBOT_PERFORMANCE_CACHE_TTL_SECONDS", 0, minimum=0
)


@dataclass(frozen=True)
class _CacheKey:
    """Internal cache key encapsulating namespace and identity semantics."""

    namespace: str
    value: Any
    uses_identity: bool

    def __hash__(self) -> int:  # pragma: no cover - dataclass default hash is fine
        return hash((self.namespace, self.value))


class PerformanceCache:
    """Centralized caching service for expensive operations."""

    def __init__(
        self,
        max_cache_size: int | None = None,
        *,
        ttl_seconds: int | None = None,
        telemetry_client: TelemetryClient | None = None,
    ) -> None:
        """Initialize performance cache.

        Args:
            max_cache_size: Maximum number of items to cache
            ttl_seconds: Optional TTL in seconds; 0 disables expiration
        """
        resolved_max = (
            max_cache_size if max_cache_size is not None else DEFAULT_MAX_SIZE
        )
        if resolved_max < 1:
            logger.warning(
                "Performance cache size %d must be >= 1; using default %d",
                resolved_max,
                DEFAULT_MAX_SIZE,
            )
            resolved_max = DEFAULT_MAX_SIZE
        self.max_cache_size = resolved_max

        resolved_ttl = ttl_seconds if ttl_seconds is not None else DEFAULT_TTL_SECONDS
        self._ttl_seconds: int | None = resolved_ttl if resolved_ttl > 0 else None
        # TTL evicts stale entries automatically; defaults to
        # `IMPORTOBOT_PERFORMANCE_CACHE_TTL_SECONDS`.

        self._string_cache: dict[_CacheKey, str] = {}
        self._string_identity_refs: dict[_CacheKey, Any] = {}
        self._string_cache_expiry: dict[_CacheKey, float] = {}
        self._json_cache: dict[_CacheKey, str] = {}
        self._json_identity_refs: dict[_CacheKey, Any] = {}
        self._json_cache_expiry: dict[_CacheKey, float] = {}
        self._object_cache: WeakKeyDictionary[Any, Any] = WeakKeyDictionary()
        self._manual_cache: dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._string_ops_cache: dict[str, Any] = {}
        resolved_telemetry = telemetry_client or get_telemetry_client()
        self._telemetry: TelemetryClient | _NullTelemetry = (
            resolved_telemetry if resolved_telemetry is not None else _NullTelemetry()
        )
        logger.info("Initialized PerformanceCache with max_size=%d", resolved_max)

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
        cache_key = self._build_cache_key("string", data)

        # Check cache first
        if cache_key in self._string_cache:
            current_time = time.time()
            if self._is_expired(
                self._string_cache_expiry.get(cache_key), now=current_time
            ) or (
                cache_key.uses_identity
                and self._string_identity_refs.get(cache_key) is not data
            ):
                self._evict_string_entry(cache_key)
            else:
                self._cache_hits += 1
                self._string_cache_expiry[cache_key] = current_time
                self._emit_cache_metrics()
                return self._string_cache[cache_key]

        # Cache miss - compute and store
        self._cache_misses += 1
        result = str(data).lower()

        # Manage cache size
        if len(self._string_cache) >= self.max_cache_size:
            self._evict_oldest_string_entry()

        self._string_cache[cache_key] = result
        self._string_cache_expiry[cache_key] = time.time()
        if cache_key.uses_identity:
            self._string_identity_refs[cache_key] = data
        else:
            self._string_identity_refs.pop(cache_key, None)
        self._emit_cache_metrics()
        return result

    def get_cached_json_string(self, data: Any) -> str:
        """Get cached JSON string representation.

        Addresses repeated JSON serialization without caching across 17 modules.

        Args:
            data: Data to serialize to JSON

        Returns:
            Cached JSON string representation
        """
        cache_key = self._build_cache_key("json", data)

        if cache_key in self._json_cache:
            current_time = time.time()
            if self._is_expired(
                self._json_cache_expiry.get(cache_key), now=current_time
            ) or (
                cache_key.uses_identity
                and self._json_identity_refs.get(cache_key) is not data
            ):
                self._evict_json_entry(cache_key)
            else:
                self._cache_hits += 1
                self._json_cache_expiry[cache_key] = current_time
                self._emit_cache_metrics()
                return self._json_cache[cache_key]

        self._cache_misses += 1
        result = json.dumps(data, sort_keys=True, separators=(",", ":"))

        if len(self._json_cache) >= self.max_cache_size:
            self._evict_oldest_json_entry()

        self._json_cache[cache_key] = result
        self._json_cache_expiry[cache_key] = time.time()
        if cache_key.uses_identity:
            self._json_identity_refs[cache_key] = data
        else:
            self._json_identity_refs.pop(cache_key, None)
        self._emit_cache_metrics()
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

    def get_cached_object_attribute(self, obj: Any, attribute: str) -> Any | None:
        """Get cached attribute for an object.

        Args:
            obj: Object to get cached attribute for
            attribute: Attribute name

        Returns:
            Cached value if available, None otherwise
        """
        if obj in self._object_cache and attribute in self._object_cache[obj]:
            self._cache_hits += 1
            self._emit_cache_metrics()
            return self._object_cache[obj][attribute]

        self._cache_misses += 1
        self._emit_cache_metrics()
        return None

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._string_cache.clear()
        self._string_identity_refs.clear()
        self._string_cache_expiry.clear()
        self._json_cache.clear()
        self._json_identity_refs.clear()
        self._json_cache_expiry.clear()
        self._object_cache.clear()
        self._manual_cache.clear()
        self._emit_cache_metrics()
        logger.info("Performance caches cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self._string_cache) + len(self._manual_cache),
            "string_cache_size": len(self._string_cache),
            "json_cache_size": len(self._json_cache),
            "object_cache_size": len(self._object_cache),
            "max_cache_size": self.max_cache_size,
            "ttl_seconds": self._ttl_seconds or 0,
        }

    def _emit_cache_metrics(self) -> None:
        """Emit cache performance metrics to telemetry."""
        if self._telemetry is not None:
            self._telemetry.record_cache_metrics(
                "performance_cache",
                hits=self._cache_hits,
                misses=self._cache_misses,
                extras={
                    "string_cache_size": len(self._string_cache),
                    "json_cache_size": len(self._json_cache),
                    "object_cache_size": len(self._object_cache),
                    "manual_cache_size": len(self._manual_cache),
                    "max_cache_size": self.max_cache_size,
                    "ttl_seconds": self._ttl_seconds or 0,
                },
            )

    def _build_cache_key(self, namespace: str, data: Any) -> _CacheKey:
        """Build an internal cache key without forcing serialization when possible."""
        if isinstance(data, Hashable):
            return _CacheKey(namespace, data, False)
        return _CacheKey(namespace, id(data), True)

    def _evict_oldest_string_entry(self) -> None:
        """Evict the oldest entry from string cache (simple FIFO)."""
        if self._string_cache:
            oldest_key = next(iter(self._string_cache))
            self._evict_string_entry(oldest_key)

    def _evict_oldest_json_entry(self) -> None:
        """Evict the oldest entry from JSON cache (simple FIFO)."""
        if self._json_cache:
            oldest_key = next(iter(self._json_cache))
            self._evict_json_entry(oldest_key)

    def _evict_string_entry(self, cache_key: _CacheKey) -> None:
        """Evict a specific entry from the string cache."""
        self._string_cache.pop(cache_key, None)
        self._string_cache_expiry.pop(cache_key, None)
        self._string_identity_refs.pop(cache_key, None)

    def _evict_json_entry(self, cache_key: _CacheKey) -> None:
        """Evict a specific entry from the JSON cache."""
        self._json_cache.pop(cache_key, None)
        self._json_cache_expiry.pop(cache_key, None)
        self._json_identity_refs.pop(cache_key, None)

    def _is_expired(self, timestamp: float | None, *, now: float | None = None) -> bool:
        """Check if a cache entry has expired."""
        if self._ttl_seconds is None or timestamp is None:
            return False
        current = now if now is not None else time.time()
        return (current - timestamp) > self._ttl_seconds

    def set(self, key: str, value: Any) -> None:
        """Store a value in the manual cache segment."""
        self._manual_cache[key] = value

    def get(self, key: str) -> Any | None:
        """Retrieve a value from the manual cache segment."""
        return self._manual_cache.get(key)


class LazyEvaluator:
    """Lazy evaluation patterns for expensive computations."""

    def __init__(self, cache: PerformanceCache | None = None):
        """Initialize lazy evaluator.

        Args:
            cache: Optional performance cache to use
        """
        self.cache = cache or PerformanceCache()
        self._string_ops_cache: OrderedDict[str, Any] = OrderedDict()

    def lazy_format_detection(
        self, data: dict[str, Any], format_detector_func: Any
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


class _SupportsPerformanceCache(Protocol):
    @property
    def performance_cache(self) -> PerformanceCache:
        """Return performance cache instance."""
        ...


def get_performance_cache() -> PerformanceCache:
    """Get the performance cache from the current application context."""
    context_module = importlib.import_module("importobot.context")
    context = cast(_SupportsPerformanceCache, context_module.get_context())
    return context.performance_cache


def cached_string_lower(data: Any) -> str:
    """Global function for cached string lowercasing.

    This can replace str(data).lower() calls throughout the codebase.
    """
    return get_performance_cache().get_cached_string_lower(data)


def cached_json_dumps(data: Any) -> str:
    """Global function for cached JSON serialization."""
    return get_performance_cache().get_cached_json_string(data)
