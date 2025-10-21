"""LRU cache implementation with TTL and security features."""

from __future__ import annotations

import hashlib
import sys
import time
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from importobot.caching.base import CacheConfig, CacheStrategy
from importobot.telemetry import TelemetryClient, get_telemetry_client
from importobot.utils.logging import get_logger

logger = get_logger()

K = TypeVar("K")
V = TypeVar("V")


@dataclass(frozen=True)
class SecurityPolicy:
    """Security constraints for cache operations."""

    max_content_size: int = 50000
    max_collision_chain: int = 3


@dataclass
class CacheEntry(Generic[V]):
    """Cache entry with metadata."""

    value: V
    timestamp: float
    access_count: int = 0


class LRUCache(CacheStrategy[K, V]):
    """Unified LRU cache with TTL and security features."""

    TELEMETRY_BATCH_SIZE = 20
    TELEMETRY_FLUSH_SECONDS = 5.0

    def __init__(
        self,
        config: CacheConfig | None = None,
        security_policy: SecurityPolicy | None = None,
        telemetry_client: TelemetryClient | None = None,
    ) -> None:
        """Initialize LRU cache."""
        self.config = config or CacheConfig()
        self.security = security_policy or SecurityPolicy()
        self._telemetry = telemetry_client or get_telemetry_client()

        self._cache: dict[K, CacheEntry[V]] = {}
        self._collision_chains: dict[str, list[K]] = {}
        self._total_size = 0

        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._rejections = 0
        self._pending_metric_events = 0
        self._last_metrics_emit = time.time()

    def __len__(self) -> int:
        """Return the number of cached entries."""
        return len(self._cache)

    def __bool__(self) -> bool:
        """Return True when the cache currently holds entries."""
        return bool(self._cache)

    def get(self, key: K) -> V | None:
        """Retrieve value by key with LRU update."""
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
        entry.timestamp = time.time()
        self._cache[key] = self._cache.pop(key)

        self._hits += 1
        self._record_metric_event()
        return entry.value

    def set(self, key: K, value: V) -> None:
        """Store value with security validation."""
        content_size = self._estimate_size(value)
        if content_size > self.security.max_content_size:
            self._rejections += 1
            logger.warning(
                "Cache rejected oversized content: %d bytes (limit: %d)",
                content_size,
                self.security.max_content_size,
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

        if len(self._cache) >= self.config.max_size:
            self._evict_lru()

        while (
            self.config.max_content_size_bytes > 0
            and self._total_size + content_size > self.config.max_content_size_bytes
            and self._cache
        ):
            self._evict_lru()

        self._cache[key] = CacheEntry(value=value, timestamp=time.time())
        self._total_size += content_size
        self._record_metric_event()

    def delete(self, key: K) -> None:
        """Remove entry from cache."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._total_size -= self._estimate_size(entry.value)
            key_hash = self._hash_key(key)
            if key_hash in self._collision_chains:
                if key in self._collision_chains[key_hash]:
                    self._collision_chains[key_hash].remove(key)
                if not self._collision_chains[key_hash]:
                    del self._collision_chains[key_hash]

    def clear(self) -> None:
        """Clear all cache entries and reset statistics."""
        self._cache.clear()
        self._collision_chains.clear()
        self._total_size = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._rejections = 0
        self._emit_metrics(force=True)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
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

    def get_cache_stats(self) -> dict[str, Any]:
        """Alias helper to align with legacy cache API."""
        return self.get_stats()

    def flush_metrics(self) -> None:
        """Force emission of any pending telemetry events."""
        self._emit_metrics(force=True)

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if self._cache:
            oldest_key = next(iter(self._cache))
            self.delete(oldest_key)
            self._evictions += 1

    def _is_expired(self, timestamp: float) -> bool:
        """Check if entry has expired based on TTL."""
        if self.config.ttl_seconds is None or self.config.ttl_seconds <= 0:
            return False
        return (time.time() - timestamp) > self.config.ttl_seconds

    def _hash_key(self, key: K) -> str:
        """Generate hash for collision tracking."""
        key_str = str(key)
        # BLAKE2b offers strong collision resistance with lower CPU cost than
        # SHA-256, keeping per-request hashing fast while still guarding
        # against crafted collisions.
        return hashlib.blake2b(key_str.encode(), digest_size=16).hexdigest()

    def _estimate_size(self, value: V) -> int:
        """Estimate content size in bytes."""
        try:
            return sys.getsizeof(value)
        except (TypeError, AttributeError) as exc:
            logger.debug("Failed to estimate cache entry size for %r: %s", value, exc)
            return 0

    def _record_metric_event(self) -> None:
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


__all__ = ["LRUCache", "SecurityPolicy"]
