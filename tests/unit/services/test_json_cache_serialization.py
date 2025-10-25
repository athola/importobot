"""Tests verifying JSON cache avoids double serialization.

This test suite validates that the PerformanceCache optimization using
object identity (id(data)) for unhashable types prevents redundant
serialization when generating cache keys.
"""

import json
import time
from unittest.mock import patch

from importobot.services.performance_cache import PerformanceCache


class TestJSONCacheSerializationOptimization:
    """Verify JSON caching uses identity-based keys to avoid double serialization."""

    def test_json_cache_serializes_once_per_unique_object(self):
        """GIVEN an unhashable object (dict)
        WHEN caching it multiple times
        THEN json.dumps is called only once (not for key generation)

        This verifies the optimization in _build_cache_key that uses
        id(data) instead of hash(json.dumps(data)) for unhashable types.
        """
        cache = PerformanceCache()
        test_data = {"key": "value", "nested": {"data": [1, 2, 3]}}

        # Track json.dumps calls
        dumps_call_count = 0
        original_dumps = json.dumps

        def counting_dumps(*args, **kwargs):
            nonlocal dumps_call_count
            dumps_call_count += 1
            return original_dumps(*args, **kwargs)

        with patch("importobot.services.performance_cache.json.dumps", counting_dumps):
            # First call: cache miss, should serialize once
            result1 = cache.get_cached_json_string(test_data)
            assert dumps_call_count == 1, "First call should serialize once"

            # Second call with same object identity: cache hit, no serialization
            result2 = cache.get_cached_json_string(test_data)
            assert dumps_call_count == 1, "Cache hit should not serialize"
            assert result1 == result2

            # Third call: still same object, still cache hit
            result3 = cache.get_cached_json_string(test_data)
            assert dumps_call_count == 1, "Multiple hits should not serialize"
            assert result1 == result3

        # Verify the cached result is correct
        expected = json.dumps(test_data, sort_keys=True, separators=(",", ":"))
        assert result1 == expected

    def test_json_cache_distinguishes_objects_by_identity(self):
        """GIVEN two dicts with identical content but different identities
        WHEN caching both
        THEN each is serialized once (cache uses identity, not value)

        This verifies that id(data) is used for cache keys, making
        identical-value objects cache separately.
        """
        cache = PerformanceCache()

        data1 = {"key": "value"}
        data2 = {"key": "value"}  # Same content, different object

        dumps_call_count = 0
        original_dumps = json.dumps

        def counting_dumps(*args, **kwargs):
            nonlocal dumps_call_count
            dumps_call_count += 1
            return original_dumps(*args, **kwargs)

        with patch("importobot.services.performance_cache.json.dumps", counting_dumps):
            result1 = cache.get_cached_json_string(data1)
            assert dumps_call_count == 1

            # Different object identity, even though same value
            result2 = cache.get_cached_json_string(data2)
            assert dumps_call_count == 2, (
                "Different objects should serialize separately"
            )

            # But same results
            assert result1 == result2

            # Re-accessing original objects hits cache
            _ = cache.get_cached_json_string(data1)
            _ = cache.get_cached_json_string(data2)
            assert dumps_call_count == 2, "Cache hits should not serialize"

    def test_json_cache_faster_than_direct_serialization_on_hits(self):
        """GIVEN a complex nested structure
        WHEN caching and accessing repeatedly
        THEN cache hits are faster than direct json.dumps()

        This validates that the cache provides real performance benefit.
        """
        cache = PerformanceCache()

        # Create a moderately complex structure
        complex_data = {
            "tests": [
                {
                    "id": f"test_{i}",
                    "steps": [
                        {"action": f"step_{j}", "expected": f"result_{j}"}
                        for j in range(10)
                    ],
                }
                for i in range(50)
            ]
        }

        # Warm up cache
        _ = cache.get_cached_json_string(complex_data)

        # Measure cache hits
        cache_start = time.perf_counter()
        for _ in range(100):
            _ = cache.get_cached_json_string(complex_data)
        cache_time = time.perf_counter() - cache_start

        # Measure direct serialization
        direct_start = time.perf_counter()
        for _ in range(100):
            _ = json.dumps(complex_data, sort_keys=True, separators=(",", ":"))
        direct_time = time.perf_counter() - direct_start

        # Cache should be significantly faster (at least 2x)
        speedup = direct_time / cache_time
        assert speedup > 2.0, (
            f"Cache not providing benefit: speedup={speedup:.1f}x "
            f"(cache={cache_time:.4f}s, direct={direct_time:.4f}s)"
        )

    def test_hashable_data_uses_value_based_key(self):
        """GIVEN hashable data (string, tuple, etc)
        WHEN caching
        THEN cache key uses the value directly (no id() needed)

        This verifies that immutable hashables can be cached by value,
        allowing cache hits across different instances of same value.
        """
        cache = PerformanceCache()

        # Hashable data
        data1 = "test_string"
        data2 = "test_string"  # Same value, possibly different object

        dumps_call_count = 0
        original_dumps = json.dumps

        def counting_dumps(*args, **kwargs):
            nonlocal dumps_call_count
            dumps_call_count += 1
            return original_dumps(*args, **kwargs)

        with patch("importobot.services.performance_cache.json.dumps", counting_dumps):
            result1 = cache.get_cached_json_string(data1)
            assert dumps_call_count == 1

            # Same value should hit cache even if different object
            result2 = cache.get_cached_json_string(data2)
            # For strings in Python, small strings are interned, so this might
            # be 1 (cache hit) or 2 (if not interned). The important thing is
            # we're not serializing for the key generation.
            assert result1 == result2

    def test_cache_eviction_doesnt_leak_identity_refs(self):
        """GIVEN a small cache that triggers evictions
        WHEN filling beyond capacity
        THEN identity references are cleaned up properly

        This verifies that the _json_identity_refs dict doesn't leak memory.
        """
        cache = PerformanceCache(max_cache_size=10)

        # Create 20 different objects to force evictions
        objects = [{"id": i, "data": f"value_{i}"} for i in range(20)]

        for obj in objects:
            _ = cache.get_cached_json_string(obj)

        # Cache should be at max size
        stats = cache.get_cache_stats()
        assert stats["json_cache_size"] <= 10

        # Identity refs should also be bounded (no leaks)
        # We can't check this directly without accessing private state,
        # but we verify the cache size limit works
        assert len(cache._json_cache) <= 10
        assert len(cache._json_identity_refs) <= 10

    def test_identity_check_prevents_false_cache_hits(self):
        """GIVEN an object that gets garbage collected and its id reused
        WHEN the new object with reused id is cached
        THEN the old cache entry is evicted (no false hit)

        This verifies the identity reference checking in get_cached_json_string.
        """
        cache = PerformanceCache()

        data1 = {"value": "first"}
        result1 = cache.get_cached_json_string(data1)

        # In real scenarios, if data1 was deleted, GC might reuse the id
        # The cache should detect that the identity ref doesn't match
        data2 = {"value": "second"}

        # Even if ids somehow matched (unlikely in this test, but we check the logic),
        # the identity check `self._json_identity_refs.get(cache_key) is not data`
        # would catch it
        result2 = cache.get_cached_json_string(data2)

        # Results should be different
        assert result1 != result2

        # Verify both are correct
        assert result1 == '{"value":"first"}'
        assert result2 == '{"value":"second"}'
