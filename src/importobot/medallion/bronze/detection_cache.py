"""Caching and performance optimization for format detection."""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

from importobot.config import (
    DETECTION_CACHE_COLLISION_LIMIT as CONFIG_COLLISION_LIMIT,
)
from importobot.config import (
    DETECTION_CACHE_MAX_SIZE as CONFIG_MAX_SIZE,
)
from importobot.config import (
    DETECTION_CACHE_TTL_SECONDS as CONFIG_TTL_SECONDS,
)
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.telemetry import TelemetryClient, get_telemetry_client
from importobot.utils.logging import setup_logger

logger = setup_logger(__name__)


DETECTION_CACHE_MAX_SIZE = CONFIG_MAX_SIZE
DETECTION_CACHE_COLLISION_LIMIT = CONFIG_COLLISION_LIMIT
DETECTION_CACHE_TTL_SECONDS = CONFIG_TTL_SECONDS


class DetectionCache:
    """Manages caching and performance optimizations for format detection."""

    # Security constants
    MAX_COLLISION_CHAIN_LENGTH = 3  # Prevent DoS via collision chains
    MAX_CONTENT_SIZE = 50000  # Prevent memory exhaustion attacks

    def __init__(
        self,
        max_cache_size: Optional[int] = None,
        *,
        collision_chain_limit: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
        telemetry_client: Optional[TelemetryClient] = None,
    ) -> None:
        """Initialize detection cache."""
        resolved_max = (
            max_cache_size if max_cache_size is not None else DETECTION_CACHE_MAX_SIZE
        )
        self.max_cache_size = resolved_max

        configured_limit = (
            collision_chain_limit
            if collision_chain_limit is not None
            else DETECTION_CACHE_COLLISION_LIMIT
        )
        if configured_limit < 1:
            logger.warning(
                "Collision chain limit %d must be >= 1; using default %d",
                configured_limit,
                self.MAX_COLLISION_CHAIN_LENGTH,
            )
            configured_limit = self.MAX_COLLISION_CHAIN_LENGTH
        self._max_collision_chain_length = configured_limit

        resolved_ttl = (
            ttl_seconds if ttl_seconds is not None else DETECTION_CACHE_TTL_SECONDS
        )
        self._ttl_seconds: Optional[int] = resolved_ttl if resolved_ttl > 0 else None

        # Use string hash as key, store only the computed result
        self._data_string_cache: OrderedDict[str, str] = OrderedDict()
        self._data_string_expiry: Dict[str, float] = {}
        self._normalized_key_cache: OrderedDict[str, set[str]] = OrderedDict()
        self._detection_result_cache: OrderedDict[str, SupportedFormat] = OrderedDict()
        self._detection_result_expiry: Dict[str, float] = {}
        # Collision tracking for security monitoring
        self._collision_chains: OrderedDict[str, list[str]] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0
        self._collision_count = 0
        self._rejected_large_content = 0
        self._telemetry = telemetry_client or get_telemetry_client()

    def get_data_string_efficient(self, data: Any) -> str:
        """Get string representation with secure collision-resistant caching."""
        # Generate optimized hash
        content_hash, data_str = self._get_content_hash_and_string(data)

        # Security check: Reject oversized content
        if len(data_str) > self.MAX_CONTENT_SIZE:
            self._rejected_large_content += 1
            logger.warning(
                "Cache rejected oversized content: %d bytes (limit: %d). "
                "Potential DoS attempt detected.",
                len(data_str),
                self.MAX_CONTENT_SIZE,
            )
            return data_str  # Don't cache, return directly

        # Generate secondary hash for collision detection
        secondary_hash = self._get_secondary_hash(data_str)
        cache_key = f"{content_hash}_{secondary_hash[:8]}"  # Combined key

        if cache_key in self._data_string_cache:
            if self._is_expired(self._data_string_expiry.get(cache_key)):
                self._evict_data_string_entry(cache_key)
            else:
                self._cache_hits += 1
                self._data_string_cache.move_to_end(cache_key)
                self._data_string_expiry[cache_key] = time.time()
                self._emit_cache_metrics()
                return self._data_string_cache[cache_key]

        # Handle potential collision with primary hash
        if content_hash in self._collision_chains:
            collision_list = self._collision_chains[content_hash]
            # Security: Limit collision chain length
            if len(collision_list) >= self._max_collision_chain_length:
                self._collision_count += 1
                logger.warning(
                    "Cache rejected data due to collision chain limit: %d (limit: %d). "
                    "Potential hash collision attack detected.",
                    len(collision_list),
                    self._max_collision_chain_length,
                )
                return data_str  # Don't cache, return directly
            collision_list.append(cache_key)
        else:
            self._collision_chains[content_hash] = [cache_key]

        self._cache_misses += 1

        # Cache with combined key (eliminates data duplication)
        self._data_string_cache[cache_key] = data_str
        self._data_string_expiry[cache_key] = time.time()
        self._emit_cache_metrics()

        # Maintain cache size
        if len(self._data_string_cache) > self.max_cache_size:
            oldest_key, _ = self._data_string_cache.popitem(last=False)
            self._data_string_expiry.pop(oldest_key, None)

        return data_str

    def _evict_data_string_entry(self, cache_key: str) -> None:
        self._data_string_cache.pop(cache_key, None)
        self._data_string_expiry.pop(cache_key, None)

    def _get_content_hash_and_string(self, data: Any) -> Tuple[str, str]:
        """Generate collision-resistant content hash and normalized string.

        Returns:
            Tuple of (content_hash, data_string) for caching and verification
        """
        # Convert to JSON string for consistent formatting
        try:
            normalized_str = json.dumps(
                data, separators=(",", ":"), sort_keys=True
            ).lower()
        except (TypeError, ValueError):
            normalized_str = str(data).lower()

        # Encode once so we can reuse the bytes for hashing and caching
        normalized_bytes = normalized_str.encode("utf-8")

        # Generate Blake2b hash of the complete normalized content
        # Blake2b is faster than SHA-256 with equivalent collision resistance
        content_hash = hashlib.blake2b(normalized_bytes).hexdigest()

        return content_hash, normalized_str

    def _get_secondary_hash(self, data_str: str) -> str:
        """Generate secondary hash for collision detection optimization."""
        # Use different algorithm for secondary hash to minimize correlation
        return hashlib.blake2b(
            data_str.encode("utf-8"),
            digest_size=16,  # Smaller digest for efficiency
            salt=b"collision_detect",  # Salt to differentiate from primary hash
        ).hexdigest()

    def get_normalized_key_set(self, data: Dict[str, Any]) -> set[str]:
        """Get normalized key set using secure collision-resistant cache."""
        # Create deterministic hash of sorted keys for consistent caching
        keys_string = json.dumps(sorted(data.keys()), sort_keys=True)

        # Security check: Reject oversized key sets
        if len(keys_string) > self.MAX_CONTENT_SIZE:
            self._rejected_large_content += 1
            logger.warning(
                "Cache rejected oversized key set: %d bytes (limit: %d). "
                "Potential DoS attempt detected.",
                len(keys_string),
                self.MAX_CONTENT_SIZE,
            )
            # Compute directly without caching
            return {key.lower().strip() for key in data.keys() if isinstance(key, str)}

        primary_hash = hashlib.blake2b(keys_string.encode("utf-8")).hexdigest()
        secondary_hash = self._get_secondary_hash(keys_string)
        cache_key = f"{primary_hash}_{secondary_hash[:8]}"

        if cache_key in self._normalized_key_cache:
            self._cache_hits += 1
            # Move to end (LRU)
            self._normalized_key_cache.move_to_end(cache_key)
            self._emit_cache_metrics()
            return self._normalized_key_cache[cache_key]

        self._cache_misses += 1

        # Compute normalized keys
        normalized_keys = {
            key.lower().strip() for key in data.keys() if isinstance(key, str)
        }

        # Cache with optimized key (no data duplication)
        self._normalized_key_cache[cache_key] = normalized_keys
        self._emit_cache_metrics()

        # Maintain cache size
        if len(self._normalized_key_cache) > self.max_cache_size:
            self._normalized_key_cache.popitem(last=False)

        return normalized_keys

    def cache_detection_result(self, data: Any, result: SupportedFormat) -> None:
        """Cache detection result using secure collision-resistant hashing."""
        try:
            content_hash, data_str = self._get_content_hash_and_string(data)

            # Security check: Reject oversized content
            if len(data_str) > self.MAX_CONTENT_SIZE:
                self._rejected_large_content += 1
                logger.warning(
                    "Cache rejected oversized detection result: %d bytes (limit: %d). "
                    "Potential DoS attempt detected.",
                    len(data_str),
                    self.MAX_CONTENT_SIZE,
                )
                return  # Don't cache

            secondary_hash = self._get_secondary_hash(data_str)
            cache_key = f"{content_hash}_{secondary_hash[:8]}"

            # Cache with optimized key (no data duplication)
            self._detection_result_cache[cache_key] = result
            self._detection_result_expiry[cache_key] = time.time()

            # Maintain cache size
            if len(self._detection_result_cache) > self.max_cache_size:
                oldest_key, _ = self._detection_result_cache.popitem(last=False)
                self._detection_result_expiry.pop(oldest_key, None)
        except (TypeError, ValueError):
            # Can't process this data, skip caching
            pass

    def get_cached_detection_result(self, data: Any) -> Optional[SupportedFormat]:
        """Get cached detection result using secure collision-resistant lookup."""
        try:
            content_hash, data_str = self._get_content_hash_and_string(data)

            # Security check: Reject oversized content
            if len(data_str) > self.MAX_CONTENT_SIZE:
                self._rejected_large_content += 1
                logger.warning(
                    "Cache lookup rejected oversized content: %d bytes (limit: %d). "
                    "Potential DoS attempt detected.",
                    len(data_str),
                    self.MAX_CONTENT_SIZE,
                )
                return None  # Don't lookup

            secondary_hash = self._get_secondary_hash(data_str)
            cache_key = f"{content_hash}_{secondary_hash[:8]}"

            if cache_key in self._detection_result_cache:
                if self._is_expired(self._detection_result_expiry.get(cache_key)):
                    self._evict_detection_result_entry(cache_key)
                else:
                    self._cache_hits += 1
                    self._detection_result_cache.move_to_end(cache_key)
                    self._detection_result_expiry[cache_key] = time.time()
                    self._emit_cache_metrics()
                    return self._detection_result_cache[cache_key]
        except (TypeError, ValueError):
            pass

        self._cache_misses += 1
        self._emit_cache_metrics()
        return None

    def _evict_detection_result_entry(self, cache_key: str) -> None:
        self._detection_result_cache.pop(cache_key, None)
        self._detection_result_expiry.pop(cache_key, None)

    def enforce_min_detection_time(
        self, start_time: float, data: Any, min_time_ms: float = 50.0
    ) -> None:
        """Enforce minimum detection time to prevent timing attacks."""
        _ = data  # Mark as intentionally unused
        elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        if elapsed_time < min_time_ms:
            # Add artificial delay to normalize timing
            # Convert back to seconds
            remaining_time = (min_time_ms - elapsed_time) / 1000.0
            time.sleep(remaining_time)

    def _is_expired(self, timestamp: Optional[float]) -> bool:
        if self._ttl_seconds is None or timestamp is None:
            return False
        return (time.time() - timestamp) > self._ttl_seconds

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics including security metrics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / max(total_requests, 1)

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "collision_count": self._collision_count,
            "rejected_large_content": self._rejected_large_content,
            "data_string_cache_size": len(self._data_string_cache),
            "normalized_key_cache_size": len(self._normalized_key_cache),
            "detection_result_cache_size": len(self._detection_result_cache),
            "collision_chains_count": len(self._collision_chains),
            "ttl_seconds": self._ttl_seconds or 0,
        }

    def clear_cache(self) -> None:
        """Clear all caches and reset security tracking."""
        self._data_string_cache.clear()
        self._data_string_expiry.clear()
        self._normalized_key_cache.clear()
        self._detection_result_cache.clear()
        self._detection_result_expiry.clear()
        self._collision_chains.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._collision_count = 0
        self._rejected_large_content = 0
        self._emit_cache_metrics()

    def _emit_cache_metrics(self) -> None:
        self._telemetry.record_cache_metrics(
            "detection_cache",
            hits=self._cache_hits,
            misses=self._cache_misses,
            extras={
                "data_string_cache_size": len(self._data_string_cache),
                "detection_result_cache_size": len(self._detection_result_cache),
                "normalized_key_cache_size": len(self._normalized_key_cache),
                "collision_count": self._collision_count,
                "ttl_seconds": self._ttl_seconds or 0,
            },
        )


__all__ = ["DetectionCache"]
