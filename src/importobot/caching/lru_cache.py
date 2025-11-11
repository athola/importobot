"""Implements an LRU cache with Time-To-Live (TTL) and security features."""

from __future__ import annotations

import hashlib
import heapq
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from importobot.caching.base import CacheConfig, CacheStrategy
from importobot.config import (
    CACHE_DEFAULT_CLEANUP_INTERVAL,
    CACHE_MAX_CLEANUP_INTERVAL,
    CACHE_MIN_CLEANUP_INTERVAL,
    CACHE_SHORT_TTL_THRESHOLD,
)
from importobot.telemetry import TelemetryClient, get_telemetry_client
from importobot.utils.logging import get_logger

logger = get_logger()

K = TypeVar("K")
V = TypeVar("V")


@dataclass(frozen=True)
class SecurityPolicy:
    """Defines security constraints for cache operations."""

    max_content_size: int = 50000
    max_collision_chain: int = 3


@dataclass(frozen=True)
class _HeapEntry:
    """Represents a heap entry used for expiration tracking."""

    expire_time: float
    key_hash: str  # Use hash to avoid key type issues in heap

    def __lt__(self, other: _HeapEntry) -> bool:
        return self.expire_time < other.expire_time


@dataclass
class CacheEntry(Generic[V]):
    """Represents a cache entry, including its associated metadata."""

    value: V
    timestamp: float
    access_count: int = 0
    heap_index: int = -1  # Track position in heap for efficient removal


class LRUCache(CacheStrategy[K, V]):
    """A unified LRU cache implementation with TTL and security enhancements."""

    TELEMETRY_BATCH_SIZE = 20
    TELEMETRY_FLUSH_SECONDS = 5.0

    # Cleanup interval thresholds (in seconds)
    MIN_CLEANUP_INTERVAL = CACHE_MIN_CLEANUP_INTERVAL
    DEFAULT_CLEANUP_INTERVAL = CACHE_DEFAULT_CLEANUP_INTERVAL
    MAX_CLEANUP_INTERVAL = CACHE_MAX_CLEANUP_INTERVAL
    SHORT_TTL_THRESHOLD = CACHE_SHORT_TTL_THRESHOLD

    def __init__(
        self,
        config: CacheConfig | None = None,
        security_policy: SecurityPolicy | None = None,
        telemetry_client: TelemetryClient | None = None,
    ) -> None:
        """Initialize the LRU cache."""
        self.config = config or CacheConfig()
        self.security = security_policy or SecurityPolicy()
        self._telemetry = telemetry_client or get_telemetry_client()

        self._cache: OrderedDict[K, CacheEntry[V]] = OrderedDict()
        self._collision_chains: dict[str, list[K]] = {}
        self._total_size = 0

        # Min-heap for efficient expiration tracking (O(log n) operations)
        self._expiration_heap: list[_HeapEntry] = []
        self._heap_key_mapping: dict[
            str, K
        ] = {}  # Maps heap entry key_hash to cache key

        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._rejections = 0
        self._pending_metric_events = 0
        self._last_metrics_emit = time.time()
        self._cleanup_interval = self._determine_cleanup_interval()
        self._last_cleanup = time.monotonic()

    def __len__(self) -> int:
        """Return the number of cached entries."""
        return len(self._cache)

    def __bool__(self) -> bool:
        """Return `True` if the cache currently holds entries, `False` otherwise."""
        return bool(self._cache)

    def get(self, key: K) -> V | None:
        """Retrieve a value by its key, updating its position in the LRU order."""
        self._optional_cleanup()
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            self._record_metric_event()
            return None

        if self._is_expired(entry.timestamp):
            self.delete(key)
            self._misses += 1
            self._record_metric_event()
            return None

        entry.access_count += 1
        entry.timestamp = time.monotonic()
        self._cache.move_to_end(key)
        # Update expiration heap since timestamp changed
        self._remove_from_expiration_heap(key)
        self._add_to_expiration_heap(key, entry)

        self._hits += 1
        self._record_metric_event()
        return entry.value

    def set(self, key: K, value: V) -> None:
        """Store a value, subject to security validation."""
        self._optional_cleanup()
        content_size = self._estimate_size(value)
        if content_size > self.security.max_content_size:
            self._rejections += 1
            logger.warning(
                "Cache rejected oversized content: %d bytes (limit: %d)",
                content_size,
                self.security.max_content_size,
            )
            return
        max_cache_bytes = self.config.max_content_size_bytes
        if max_cache_bytes > 0 and content_size > max_cache_bytes:
            self._rejections += 1
            logger.warning(
                "Cache rejected value exceeding configured cache capacity: %d bytes "
                "(limit: %d)",
                content_size,
                max_cache_bytes,
            )
            return

        key_hash = self._hash_key(key)
        if key_hash in self._collision_chains:
            if (
                len(self._collision_chains[key_hash])
                >= self.security.max_collision_chain
            ):
                self._rejections += 1
                logger.warning(
                    "Cache rejected data due to collision chain limit: %d",
                    len(self._collision_chains[key_hash]),
                )
                return
            if key not in self._collision_chains[key_hash]:
                self._collision_chains[key_hash].append(key)
        else:
            self._collision_chains[key_hash] = [key]

        if key in self._cache:
            existing = self._cache.pop(key)
            self._total_size -= self._estimate_size(existing.value)
            self._remove_from_expiration_heap(key)

        if len(self._cache) >= self.config.max_size:
            self._evict_lru()

        eviction_attempts = 0
        while (
            max_cache_bytes > 0
            and self._total_size + content_size > max_cache_bytes
            and self._cache
            and eviction_attempts < self.config.max_size
        ):
            self._evict_lru()
            eviction_attempts += 1

        entry = CacheEntry(value=value, timestamp=time.monotonic())
        self._cache[key] = entry
        self._add_to_expiration_heap(key, entry)
        self._total_size += content_size
        self._record_metric_event()

    def contains(self, key: K) -> bool:
        """Check if a key exists in the cache and if its entry has not expired.

        Returns:
            `True` if the key exists and is not expired, `False` otherwise.
        """
        if key not in self._cache:
            return False

        entry = self._cache[key]
        if self._is_expired(entry.timestamp):
            # Clean up expired entry
            self.delete(key)
            return False

        return True

    def delete(self, key: K) -> None:
        """Remove an entry from the cache."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._total_size -= self._estimate_size(entry.value)
            self._remove_from_expiration_heap(key)
            key_hash = self._hash_key(key)
            if key_hash in self._collision_chains:
                if key in self._collision_chains[key_hash]:
                    self._collision_chains[key_hash].remove(key)
                if not self._collision_chains[key_hash]:
                    del self._collision_chains[key_hash]

    def clear(self) -> None:
        """Clear all cache entries and resets associated statistics."""
        self._cache.clear()
        self._collision_chains.clear()
        self._expiration_heap.clear()
        self._heap_key_mapping.clear()
        self._total_size = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._rejections = 0
        self._emit_metrics(force=True)
        self._last_cleanup = time.monotonic()

    def get_stats(self) -> dict[str, Any]:
        """Retrieve current cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total > 0 else 0.0

        return {
            "cache_hits": self._hits,
            "cache_misses": self._misses,
            "hit_rate": hit_rate,
            "cache_size": len(self._cache),
            "max_size": self.config.max_size,
            "current_bytes": self._total_size,
            "max_bytes": self.config.max_content_size_bytes,
            "evictions": self._evictions,
            "rejections": self._rejections,
            "ttl_seconds": self.config.ttl_seconds or 0,
        }

    def flush_metrics(self) -> None:
        """Force the emission of any pending telemetry events."""
        self._emit_metrics(force=True)

    def _add_to_expiration_heap(self, key: K, entry: CacheEntry[V]) -> None:
        """Add an entry to the expiration heap for efficient cleanup."""
        if self.config.ttl_seconds is None or self.config.ttl_seconds <= 0:
            return

        key_hash = self._hash_key(key)
        expire_time = entry.timestamp + self.config.ttl_seconds
        heap_entry = _HeapEntry(expire_time=expire_time, key_hash=key_hash)
        heapq.heappush(self._expiration_heap, heap_entry)
        self._heap_key_mapping[key_hash] = key
        entry.heap_index = len(self._expiration_heap) - 1

    def _remove_from_expiration_heap(self, key: K) -> None:
        """Remove an entry from the expiration heap mapping."""
        key_hash = self._hash_key(key)
        self._heap_key_mapping.pop(key_hash, None)
        # Note: We don't actually remove from the heap list as that's O(n)
        # Instead, we'll handle stale entries during cleanup

    def _evict_lru(self) -> None:
        """Evicts the least recently used entry from the cache."""
        if self._cache:
            oldest_key = next(iter(self._cache))
            self.delete(oldest_key)
            self._evictions += 1

    def _is_expired(self, timestamp: float) -> bool:
        """Check if an entry has expired based on its Time-To-Live (TTL)."""
        if self.config.ttl_seconds is None or self.config.ttl_seconds <= 0:
            return False
        return (time.monotonic() - timestamp) > self.config.ttl_seconds

    def _hash_key(self, key: K) -> str:
        """Generate a hash for collision tracking."""
        key_str = str(key)
        # BLAKE2b offers strong collision resistance with lower CPU cost than
        # SHA-256, keeping per-request hashing fast while still guarding
        # against crafted collisions.
        return hashlib.blake2b(key_str.encode(), digest_size=16).hexdigest()

    def _calculate_expiration_tolerance(
        self, entry_timestamp: float, current_time: float, ttl_seconds: float
    ) -> float:
        """Calculate a dynamic tolerance for expiration checks.

        This method computes a tolerance to reduce timing-related issues by considering:
        1.  Entry age relative to TTL (older entries receive more tolerance).
        2.  Absolute TTL value (longer TTLs receive proportionally more tolerance).
        3.  System timing precision.

        Returns:
            The tolerance in seconds.
        """
        if ttl_seconds <= 0:
            return 0.0

        # Calculate entry age as a fraction of TTL
        entry_age = current_time - entry_timestamp
        age_fraction = min(entry_age / ttl_seconds, 1.0)

        # Base tolerance: proportional to TTL to handle timing precision
        # 1% of TTL provides good balance between precision and reliability
        base_tolerance = ttl_seconds * 0.01

        # Age-based scaling: older entries get more tolerance
        # This accounts for accumulated timing drift over time
        # More aggressive scaling for edge cases in parallel execution
        age_multiplier = 1.0 + (age_fraction * 4.0)

        # System precision buffer: fixed minimum to handle edge cases
        # In parallel environments, we need at least 10ms buffer
        system_precision_buffer = 0.01

        # Calculate final tolerance with all factors
        tolerance = max(system_precision_buffer, base_tolerance * age_multiplier)

        # Add safety factor for parallel execution edge cases
        # This provides additional buffer for extreme timing variations
        safety_factor = 2.0
        tolerance *= safety_factor

        # Cap tolerance to prevent excessive leniency (max 15% of TTL)
        max_tolerance = ttl_seconds * 0.15
        return min(tolerance, max_tolerance)

    def _estimate_size(self, value: V) -> int:
        """Estimate the content size in bytes.

        Return a conservative estimate when `sys.getsizeof()` fails to prevent
        bypassing security constraints and unbounded cache growth.
        """
        try:
            return sys.getsizeof(value)
        except (TypeError, AttributeError) as exc:
            logger.warning(
                "Failed to estimate cache entry size for %r: %s. "
                "Using conservative estimate of 1024 bytes to maintain "
                "security constraints.",
                value,
                exc,
            )
            # Use conservative default instead of 0 to prevent:
            # 1. Bypassing max_content_size security check
            # 2. Unbounded growth when tracking total cache size
            return 1024

    def _determine_cleanup_interval(self) -> float | None:
        """Determine a cleanup cadence based on the Time-To-Live (TTL) configuration.

        **Strategy**:
        -   No TTL: No cleanup is required.
        -   Short TTLs (≤5s): Cleanup occurs at half the TTL, with a minimum of 100ms
            to prevent excessive CPU usage.
        -   Long TTLs (>5s): Cleanup at half TTL, bounded between 5s and 5 min.
        """
        ttl = self.config.ttl_seconds
        if ttl is None or ttl <= 0:
            return None

        # Short-lived caches need aggressive cleanup to prevent stale entries
        if ttl <= self.SHORT_TTL_THRESHOLD:
            return max(ttl / 2, self.MIN_CLEANUP_INTERVAL)

        # Long-lived caches use bounded scaling to balance overhead and responsiveness
        return max(
            self.DEFAULT_CLEANUP_INTERVAL, min(ttl / 2, self.MAX_CLEANUP_INTERVAL)
        )

    def _optional_cleanup(self) -> None:
        """Execute periodic cleanup for expired entries."""
        if self._cleanup_interval is None:
            return
        now = time.monotonic()
        if (now - self._last_cleanup) < self._cleanup_interval:
            return
        self._cleanup_expired_entries(now)
        self._last_cleanup = now

    def _cleanup_expired_entries(self, reference_time: float | None = None) -> None:
        """Remove expired cache entries efficiently using a min-heap."""
        if self.config.ttl_seconds is None or self.config.ttl_seconds <= 0:
            return
        if not self._cache or not self._expiration_heap:
            return

        now = reference_time if reference_time is not None else time.monotonic()
        expired_count = 0

        # Remove expired entries from heap in O(log n) per removal
        while self._expiration_heap:
            heap_entry = self._expiration_heap[0]  # Peek at minimum
            if heap_entry.expire_time > now:
                break  # No more expired entries

            # Pop expired entry
            heapq.heappop(self._expiration_heap)

            # Check if the key still exists and is actually expired
            # (handles stale heap entries from key updates/deletions)
            key_hash = heap_entry.key_hash
            if key_hash in self._heap_key_mapping:
                key = self._heap_key_mapping[key_hash]
                entry = self._cache.get(key)
                if entry is not None:
                    # Calculate expected expire time with dynamic tolerance
                    expected_expire_time = entry.timestamp + self.config.ttl_seconds

                    # Calculate dynamic tolerance based on cache characteristics
                    # This adapts to system conditions to reduce timing-related issues.
                    tolerance = self._calculate_expiration_tolerance(
                        entry.timestamp, now, self.config.ttl_seconds
                    )

                    if expected_expire_time <= (now + tolerance):
                        # This entry is actually expired (with dynamic tolerance)
                        self.delete(key)
                        self._evictions += 1
                        expired_count += 1
                    else:
                        # Entry was updated but heap entry is stale
                        # The updated entry will have its own heap entry
                        pass
                # Remove mapping regardless (stale or expired)
                self._heap_key_mapping.pop(key_hash, None)

        if expired_count > 0:
            duration_ms = int((time.monotonic() - now) * 1000)
            logger.debug(
                "Heap-based cleanup removed %d expired entries in %d ms",
                expired_count,
                duration_ms,
            )

    def _record_metric_event(self) -> None:
        """Record a metric event."""
        if not self.config.enable_telemetry or self._telemetry is None:
            return
        self._pending_metric_events += 1
        now = time.time()
        if (
            self._pending_metric_events >= self.TELEMETRY_BATCH_SIZE
            or now - self._last_metrics_emit >= self.TELEMETRY_FLUSH_SECONDS
        ):
            self._emit_metrics(now=now)

    def _emit_metrics(self, *, now: float | None = None, force: bool = False) -> None:
        """Emit telemetry metrics."""
        if not self.config.enable_telemetry or self._telemetry is None:
            self._pending_metric_events = 0
            self._last_metrics_emit = time.time()
            return
        if not force and self._pending_metric_events == 0:
            return

        self._telemetry.record_cache_metrics(
            "lru_cache",
            hits=self._hits,
            misses=self._misses,
            extras={
                "cache_size": len(self._cache),
                "max_size": self.config.max_size,
                "evictions": self._evictions,
                "rejections": self._rejections,
                "ttl_seconds": self.config.ttl_seconds or 0,
            },
        )
        self._pending_metric_events = 0
        self._last_metrics_emit = now if now is not None else time.time()


__all__ = ["CacheConfig", "LRUCache", "SecurityPolicy"]
