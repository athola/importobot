"""Caching and performance optimization for format detection."""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple

from importobot.medallion.interfaces.enums import SupportedFormat


class DetectionCache:
    """Manages caching and performance optimizations for format detection."""

    def __init__(self, max_cache_size: int = 1000):
        """Initialize detection cache."""
        self.max_cache_size = max_cache_size
        self._data_string_cache: OrderedDict[int, Tuple[Any, str]] = OrderedDict()
        self._normalized_key_cache: OrderedDict[int, Tuple[Any, set[str]]] = (
            OrderedDict()
        )
        self._detection_result_cache: OrderedDict[int, SupportedFormat] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0

    def get_data_string_efficient(self, data: Any) -> str:
        """Get string representation of data using cache."""
        data_hash = hash(str(data)[:1000])  # Hash first 1000 chars for efficiency

        if data_hash in self._data_string_cache:
            cached_data, cached_str = self._data_string_cache[data_hash]
            if cached_data == data:  # Verify it's the same data
                self._cache_hits += 1
                # Move to end (LRU)
                self._data_string_cache.move_to_end(data_hash)
                return cached_str

        self._cache_misses += 1
        # Convert to JSON string for consistent formatting
        try:
            data_str = json.dumps(data, separators=(",", ":"), sort_keys=True).lower()
        except (TypeError, ValueError):
            data_str = str(data).lower()

        # Cache the result
        self._data_string_cache[data_hash] = (data, data_str)

        # Maintain cache size
        if len(self._data_string_cache) > self.max_cache_size:
            self._data_string_cache.popitem(last=False)

        return data_str

    def get_normalized_key_set(self, data: Dict[str, Any]) -> set[str]:
        """Get normalized key set using cache."""
        data_hash = hash(str(list(data.keys())))

        if data_hash in self._normalized_key_cache:
            cached_data, cached_keys = self._normalized_key_cache[data_hash]
            if list(cached_data.keys()) == list(data.keys()):
                self._cache_hits += 1
                # Move to end (LRU)
                self._normalized_key_cache.move_to_end(data_hash)
                return cached_keys

        self._cache_misses += 1

        # Compute normalized keys
        normalized_keys = set()
        for key in data.keys():
            if isinstance(key, str):
                normalized_keys.add(key.lower().strip())

        # Cache the result
        self._normalized_key_cache[data_hash] = (data, normalized_keys)

        # Maintain cache size
        if len(self._normalized_key_cache) > self.max_cache_size:
            self._normalized_key_cache.popitem(last=False)

        return normalized_keys

    def cache_detection_result(self, data: Any, result: SupportedFormat) -> None:
        """Cache detection result."""
        try:
            data_hash = hash(str(data)[:1000])  # Hash first 1000 chars
            self._detection_result_cache[data_hash] = result

            # Maintain cache size
            if len(self._detection_result_cache) > self.max_cache_size:
                self._detection_result_cache.popitem(last=False)
        except (TypeError, ValueError):
            # Can't hash this data, skip caching
            pass

    def get_cached_detection_result(self, data: Any) -> Optional[SupportedFormat]:
        """Get cached detection result if available."""
        try:
            data_hash = hash(str(data)[:1000])
            if data_hash in self._detection_result_cache:
                self._cache_hits += 1
                # Move to end (LRU)
                self._detection_result_cache.move_to_end(data_hash)
                return self._detection_result_cache[data_hash]
        except (TypeError, ValueError):
            pass

        self._cache_misses += 1
        return None

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

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / max(total_requests, 1)

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "data_string_cache_size": len(self._data_string_cache),
            "normalized_key_cache_size": len(self._normalized_key_cache),
            "detection_result_cache_size": len(self._detection_result_cache),
        }

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._data_string_cache.clear()
        self._normalized_key_cache.clear()
        self._detection_result_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0


__all__ = ["DetectionCache"]
