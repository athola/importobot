"""Unit tests for LRUCache implementation.

Test Principles:
- Test behavior, not implementation
- One concept per test
- Follow Arrange-Act-Assert pattern
- Use descriptive test names
"""

import time

import pytest

from importobot.caching import CacheConfig, LRUCache, SecurityPolicy
from importobot.telemetry import TelemetryClient, TelemetryPayload


class TestLRUCacheBasicOperations:
    """Test fundamental cache operations (get, set, delete)."""

    def test_get_returns_none_for_missing_key(self):
        """GIVEN an empty cache
        WHEN getting a key that doesn't exist
        THEN None is returned
        """
        cache = LRUCache[str, str]()

        result = cache.get("nonexistent")

        assert result is None

    def test_set_and_get_stores_and_retrieves_value(self):
        """GIVEN a cache
        WHEN setting a key-value pair and then getting that key
        THEN the original value is returned
        """
        cache = LRUCache[str, int]()

        cache.set("key1", 42)
        result = cache.get("key1")

        assert result == 42

    def test_set_overwrites_existing_key(self):
        """GIVEN a cache with an existing key
        WHEN setting the same key with a new value
        THEN the new value replaces the old one
        """
        cache = LRUCache[str, str]()
        cache.set("key", "old_value")

        cache.set("key", "new_value")
        result = cache.get("key")

        assert result == "new_value"

    def test_delete_removes_key(self):
        """GIVEN a cache with a stored key
        WHEN deleting that key
        THEN subsequent get returns None
        """
        cache = LRUCache[str, str]()
        cache.set("key", "value")

        cache.delete("key")
        result = cache.get("key")

        assert result is None

    def test_delete_nonexistent_key_does_not_raise(self):
        """GIVEN an empty cache
        WHEN deleting a key that doesn't exist
        THEN no exception is raised
        """
        cache = LRUCache[str, str]()

        cache.delete("nonexistent")  # Should not raise

    def test_clear_removes_all_entries(self):
        """GIVEN a cache with multiple entries
        WHEN clearing the cache
        THEN all entries are removed
        """
        cache = LRUCache[str, int]()
        cache.set("key1", 1)
        cache.set("key2", 2)
        cache.set("key3", 3)

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None


class TestLRUEvictionPolicy:
    """Test LRU eviction behavior (least recently used gets evicted)."""

    def test_cache_respects_max_size(self):
        """GIVEN a cache with max_size=2
        WHEN adding 3 items
        THEN cache only contains 2 items
        """
        config = CacheConfig(max_size=2)
        cache = LRUCache[str, int](config=config)

        cache.set("key1", 1)
        cache.set("key2", 2)
        cache.set("key3", 3)

        stats = cache.get_stats()
        assert stats["cache_size"] == 2

    def test_oldest_entry_is_evicted(self):
        """GIVEN a cache with max_size=2 containing key1, key2
        WHEN adding key3
        THEN key1 (oldest) is evicted, key2 and key3 remain
        """
        config = CacheConfig(max_size=2)
        cache = LRUCache[str, int](config=config)
        cache.set("key1", 1)
        cache.set("key2", 2)

        cache.set("key3", 3)

        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == 2
        assert cache.get("key3") == 3

    def test_get_updates_recency(self):
        """GIVEN a cache with max_size=2 containing key1, key2
        WHEN accessing key1 (making it recently used) then adding key3
        THEN key2 (now oldest) is evicted, not key1
        """
        config = CacheConfig(max_size=2)
        cache = LRUCache[str, int](config=config)
        cache.set("key1", 1)
        cache.set("key2", 2)

        # Access key1 to make it recently used
        _ = cache.get("key1")

        # Add key3, should evict key2 (oldest)
        cache.set("key3", 3)

        assert cache.get("key1") == 1  # Still present
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == 3

    def test_eviction_increments_counter(self):
        """GIVEN a cache with max_size=2
        WHEN adding 3 items
        THEN eviction counter is incremented
        """
        config = CacheConfig(max_size=2)
        cache = LRUCache[str, int](config=config)
        cache.set("key1", 1)
        cache.set("key2", 2)

        cache.set("key3", 3)

        stats = cache.get_stats()
        assert stats["evictions"] >= 1


class TestTTLExpiration:
    """Test time-to-live expiration behavior."""

    def test_entries_expire_after_ttl(self):
        """GIVEN a cache with TTL=1 second
        WHEN setting a value and waiting >1 second
        THEN the value expires and get returns None
        """
        config = CacheConfig(ttl_seconds=1)
        cache = LRUCache[str, str](config=config)
        cache.set("key", "value")

        # Verify it's cached initially
        assert cache.get("key") == "value"

        # Wait for TTL to expire
        time.sleep(1.1)

        # Should be expired now
        assert cache.get("key") is None

    def test_entries_without_ttl_do_not_expire(self):
        """GIVEN a cache with no TTL (ttl_seconds=None)
        WHEN setting a value and waiting
        THEN the value never expires
        """
        config = CacheConfig(ttl_seconds=None)
        cache = LRUCache[str, str](config=config)
        cache.set("key", "value")

        # Wait a bit
        time.sleep(0.5)

        # Should still be there
        assert cache.get("key") == "value"

    def test_get_refreshes_ttl(self):
        """GIVEN a cache with TTL=1 second containing an entry
        WHEN accessing the entry before expiration
        THEN the TTL is refreshed (timestamp updated)
        """
        config = CacheConfig(ttl_seconds=1)
        cache = LRUCache[str, str](config=config)
        cache.set("key", "value")

        # Access before expiration to refresh TTL
        time.sleep(0.5)
        assert cache.get("key") == "value"

        # Wait another 0.7 seconds (total 1.2 from initial set)
        time.sleep(0.7)

        # Should still be valid because TTL was refreshed
        # (only 0.7s since last access, not 1.2s)
        assert cache.get("key") == "value"

    def test_periodic_cleanup_removes_expired_without_access(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GIVEN a cache with TTL and periodic cleanup
        WHEN time advances past TTL without touching an entry
        THEN the cache purges the stale entry on the next operation
        """
        base_time = {"value": 1_000.0}

        def fake_time() -> float:
            return base_time["value"]

        monkeypatch.setattr("importobot.caching.lru_cache.time.time", fake_time)

        config = CacheConfig(ttl_seconds=4)
        cache = LRUCache[str, str](config=config)

        cache.set("stale", "value")
        assert cache.get_stats()["cache_size"] == 1

        # Advance time beyond TTL and cleanup interval
        base_time["value"] += 5.0

        cache.set("fresh", "value2")

        stats = cache.get_stats()
        assert stats["cache_size"] == 1
        assert cache.get("stale") is None
        assert cache.get("fresh") == "value2"


class TestSecurityPolicies:
    """Test security constraints (content size, collision chains)."""

    def test_rejects_oversized_content(self, caplog):
        """GIVEN a cache with max_content_size=100 bytes
        WHEN setting a value larger than 100 bytes
        THEN the value is rejected and warning is logged
        """
        config = CacheConfig()
        security = SecurityPolicy(max_content_size=100)
        cache = LRUCache[str, str](config=config, security_policy=security)
        large_value = "x" * 200  # 200 bytes

        with caplog.at_level("WARNING"):
            cache.set("key", large_value)

        # Value was not cached
        assert cache.get("key") is None
        assert "oversized content" in caplog.text.lower()

    def test_rejection_increments_counter(self):
        """GIVEN a cache with max_content_size=100 bytes
        WHEN attempting to set oversized content
        THEN rejection counter is incremented
        """
        config = CacheConfig()
        security = SecurityPolicy(max_content_size=100)
        cache = LRUCache[str, str](config=config, security_policy=security)
        large_value = "x" * 200

        cache.set("key", large_value)

        stats = cache.get_stats()
        assert stats["rejections"] >= 1

    def test_config_max_bytes_rejects_oversized_entry(self, caplog):
        """GIVEN a cache with max_content_size_bytes=100
        WHEN setting a single value larger than the total capacity
        THEN the value is rejected and not cached
        """
        config = CacheConfig(max_content_size_bytes=100)
        cache = LRUCache[str, str](config=config)
        large_value = "x" * 200

        with caplog.at_level("WARNING"):
            cache.set("key", large_value)

        assert cache.get("key") is None
        stats = cache.get_stats()
        assert stats["rejections"] >= 1
        assert "exceeding configured cache capacity" in caplog.text.lower()

    def test_collision_chain_limit_enforced(self, monkeypatch, caplog):
        """GIVEN a cache with max_collision_chain=1
        WHEN attempting to store 2 items with same hash
        THEN second item is rejected
        """
        config = CacheConfig()
        security = SecurityPolicy(max_collision_chain=1)
        cache = LRUCache[str, str](config=config, security_policy=security)

        # Force hash collision by mocking _hash_key
        monkeypatch.setattr(cache, "_hash_key", lambda key: "fixed_hash")

        cache.set("key1", "value1")

        with caplog.at_level("WARNING"):
            cache.set("key2", "value2")

        # First key cached, second rejected
        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert "collision chain limit" in caplog.text.lower()


class TestCacheStatistics:
    """Test cache hit/miss tracking and statistics."""

    def test_cache_miss_increments_counter(self):
        """GIVEN an empty cache
        WHEN getting a non-existent key
        THEN miss counter is incremented
        """
        cache = LRUCache[str, str]()

        cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats["cache_misses"] == 1

    def test_cache_hit_increments_counter(self):
        """GIVEN a cache with a stored key
        WHEN getting that key
        THEN hit counter is incremented
        """
        cache = LRUCache[str, str]()
        cache.set("key", "value")

        cache.get("key")

        stats = cache.get_stats()
        assert stats["cache_hits"] == 1

    def test_hit_rate_calculated_correctly(self):
        """GIVEN a cache with 2 hits and 1 miss
        WHEN getting stats
        THEN hit_rate is 2/3 (0.666...)
        """
        cache = LRUCache[str, str]()
        cache.set("key1", "value1")

        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 1
        expected_rate = 2 / 3
        assert abs(stats["hit_rate"] - expected_rate) < 0.01

    def test_clear_resets_statistics(self):
        """GIVEN a cache with tracked hits/misses
        WHEN clearing the cache
        THEN all statistics are reset to zero
        """
        cache = LRUCache[str, str]()
        cache.set("key", "value")
        cache.get("key")  # Hit
        cache.get("missing")  # Miss

        cache.clear()

        stats = cache.get_stats()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["cache_size"] == 0


class TestTelemetryIntegration:
    """Test telemetry emission for monitoring."""

    def test_emits_telemetry_on_operations(self, telemetry_events):
        """GIVEN a cache with telemetry enabled
        WHEN performing cache operations
        THEN telemetry events are emitted
        """
        cache = LRUCache[str, str]()

        cache.set("key", "value")
        cache.get("key")
        cache.flush_metrics()

        # Verify telemetry events were recorded
        assert len(telemetry_events) > 0
        event_names = [event[0] for event in telemetry_events]
        assert "cache_metrics" in event_names

    def test_telemetry_includes_cache_stats(self, telemetry_events):
        """GIVEN a cache with telemetry enabled
        WHEN performing operations
        THEN telemetry includes hit/miss statistics
        """
        cache = LRUCache[str, str]()
        cache.set("key", "value")
        cache.get("key")
        cache.flush_metrics()

        # Find cache_metrics events
        cache_events = [e for e in telemetry_events if e[0] == "cache_metrics"]
        assert len(cache_events) > 0

        # Verify metrics are included
        latest_event = cache_events[-1]
        payload = latest_event[1]
        assert "hits" in payload
        assert "misses" in payload

    def test_telemetry_can_be_disabled(self):
        """GIVEN a cache with telemetry disabled
        WHEN performing operations
        THEN no telemetry events are emitted
        """
        config = CacheConfig(enable_telemetry=False)

        class CountingTelemetryClient(TelemetryClient):
            def __init__(self) -> None:
                super().__init__(min_emit_interval=0.0, min_sample_delta=1)
                self.calls = 0

            def record_cache_metrics(
                self,
                cache_name: str,
                *,
                hits: int,
                misses: int,
                extras: TelemetryPayload | None = None,
            ) -> None:
                self.calls += 1
                super().record_cache_metrics(
                    cache_name, hits=hits, misses=misses, extras=extras
                )

        mock_telemetry = CountingTelemetryClient()

        cache = LRUCache[str, str](config=config, telemetry_client=mock_telemetry)
        cache.set("key", "value")
        cache.get("key")

        # No telemetry calls should have been made
        assert mock_telemetry.calls == 0


class TestCacheContains:
    """Test the contains() helper method."""

    def test_contains_returns_true_for_existing_key(self):
        """GIVEN a cache with a stored key
        WHEN checking if key is in cache
        THEN contains returns True
        """
        cache = LRUCache[str, str]()
        cache.set("key", "value")

        assert cache.contains("key") is True

    def test_contains_returns_false_for_missing_key(self):
        """GIVEN an empty cache
        WHEN checking if key is in cache
        THEN contains returns False
        """
        cache = LRUCache[str, str]()

        assert cache.contains("nonexistent") is False

    def test_contains_returns_false_for_expired_key(self):
        """GIVEN a cache with an expired entry
        WHEN checking if key is in cache
        THEN contains returns False
        """
        config = CacheConfig(ttl_seconds=1)
        cache = LRUCache[str, str](config=config)
        cache.set("key", "value")

        time.sleep(1.1)

        assert cache.contains("key") is False


class TestCacheWithDifferentTypes:
    """Test cache with various key and value types."""

    def test_cache_with_complex_objects(self):
        """GIVEN a cache for complex objects
        WHEN storing and retrieving objects
        THEN objects are cached correctly
        """
        cache = LRUCache[str, dict]()
        complex_obj = {"nested": {"data": [1, 2, 3]}, "value": 42}

        cache.set("obj", complex_obj)
        result = cache.get("obj")

        assert result == complex_obj

    def test_cache_with_integer_keys(self):
        """GIVEN a cache with integer keys
        WHEN storing and retrieving with int keys
        THEN cache works correctly
        """
        cache = LRUCache[int, str]()

        cache.set(1, "one")
        cache.set(2, "two")

        assert cache.get(1) == "one"
        assert cache.get(2) == "two"

    def test_cache_with_tuple_keys(self):
        """GIVEN a cache with tuple keys
        WHEN storing and retrieving with tuple keys
        THEN cache works correctly
        """
        cache = LRUCache[tuple, str]()

        cache.set(("a", "b"), "value1")
        cache.set((1, 2, 3), "value2")

        assert cache.get(("a", "b")) == "value1"
        assert cache.get((1, 2, 3)) == "value2"
