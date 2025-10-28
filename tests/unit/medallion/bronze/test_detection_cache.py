"""Tests for DetectionCache configuration safeguards."""

from importobot.medallion.bronze import detection_cache as detection_cache_module
from importobot.medallion.bronze.detection_cache import DetectionCache
from importobot.medallion.interfaces.enums import SupportedFormat


# pylint: disable=protected-access
class TestDetectionCacheConfiguration:
    """Validate collision chain limit configuration behaviour."""

    def test_default_collision_limit(self):
        """Default limit aligns with configured constant."""
        cache = DetectionCache()
        assert (
            cache._max_collision_chain_length
            == detection_cache_module.DETECTION_CACHE_COLLISION_LIMIT
        )

    def test_constructor_override_takes_precedence(self):
        """Constructor argument overrides default."""
        cache = DetectionCache(collision_chain_limit=5)
        assert cache._max_collision_chain_length == 5

    def test_configuration_constant_sets_limit(self, monkeypatch):
        """Module-level configuration controls default limit."""
        monkeypatch.setattr(
            detection_cache_module,
            "DETECTION_CACHE_COLLISION_LIMIT",
            7,
            raising=False,
        )
        cache = DetectionCache()
        assert cache._max_collision_chain_length == 7

    def test_invalid_configuration_falls_back(self, monkeypatch, caplog):
        """Invalid configuration values fall back to safe default."""
        monkeypatch.setattr(
            detection_cache_module,
            "DETECTION_CACHE_COLLISION_LIMIT",
            0,
            raising=False,
        )
        with caplog.at_level("WARNING"):
            cache = DetectionCache()
        assert cache._max_collision_chain_length == cache.MAX_COLLISION_CHAIN_LENGTH
        assert "Collision chain limit" in caplog.text

    def test_reject_non_positive_limits(self, caplog):
        """Non-positive limits are rejected and a warning emitted."""
        with caplog.at_level("WARNING"):
            cache = DetectionCache(collision_chain_limit=0)
        assert cache._max_collision_chain_length == cache.MAX_COLLISION_CHAIN_LENGTH
        assert "Collision chain limit" in caplog.text

    def test_detection_result_ttl_expires(self, monkeypatch):
        """Cached detection results expire after the configured TTL."""
        cache = DetectionCache(ttl_seconds=1)
        data = {"sample": 1}
        cache.cache_detection_result(data, SupportedFormat.ZEPHYR)

        base_time = detection_cache_module.time.time()
        monkeypatch.setattr(
            detection_cache_module.time,
            "time",
            lambda: base_time + 2,
        )
        monkeypatch.setattr(
            "importobot.caching.lru_cache.time.time",
            lambda: base_time + 2,
        )
        monkeypatch.setattr(
            "importobot.caching.lru_cache.time.monotonic",
            lambda: base_time + 2,
        )

        assert cache.get_cached_detection_result(data) is None

    def test_detection_cache_emits_telemetry(self, telemetry_events):
        """Detection cache should emit telemetry for hit/miss accounting."""
        cache = DetectionCache()
        data = {"sample": 42}

        cache.get_cached_detection_result(data)
        cache.cache_detection_result(data, SupportedFormat.ZEPHYR)
        cache.get_cached_detection_result(data)

        assert telemetry_events
        event_name, payload = telemetry_events[-1]
        assert event_name == "cache_metrics"
        assert payload["cache_name"] == "detection_cache"

    def test_rejects_oversized_content(self, monkeypatch):
        """Oversized payloads should be rejected and not cached."""
        cache = DetectionCache()
        monkeypatch.setattr(cache, "MAX_CONTENT_SIZE", 8, raising=False)

        large_data = {"payload": "A" * 20}
        result = cache.get_data_string_efficient(large_data)

        # Result is returned directly but cache remains empty
        assert "aaaaaaaaaaaaaaa" in result
        assert not cache._data_string_cache  # pylint: disable=protected-access
        assert cache._rejected_large_content == 1  # pylint: disable=protected-access

    def test_collision_chain_limit_enforced(self, monkeypatch):
        """Collision chains should be capped to prevent DoS."""
        cache = DetectionCache(collision_chain_limit=1)

        # Force primary hash collisions with different secondary hashes
        monkeypatch.setattr(
            cache,
            "_get_content_hash_and_string",  # pylint: disable=protected-access
            lambda data: ("fixed_hash", str(data).lower()),
        )
        # Different prefixes for collision simulation
        monkeypatch.setattr(
            cache,
            "_get_secondary_hash",  # pylint: disable=protected-access
            lambda data_str: (
                f"hash1_{data_str}" if "one" in data_str else f"hash2_{data_str}"
            ),
        )

        first = cache.get_data_string_efficient("entry-one")
        second = cache.get_data_string_efficient("entry-two")

        # First entry cached; second rejected due to collision limit
        assert first == "entry-one"
        # Returns original input when collision limit reached
        assert second == "entry-two"
        assert len(cache._data_string_cache) == 1  # pylint: disable=protected-access
        assert cache._collision_count == 1  # pylint: disable=protected-access

    def test_eviction_metrics_include_counts(self, telemetry_events):
        """Evictions should be counted and surfaced via telemetry."""
        cache = DetectionCache(max_cache_size=2)
        cache.cache_detection_result({"id": 1}, SupportedFormat.ZEPHYR)
        cache.cache_detection_result({"id": 2}, SupportedFormat.ZEPHYR)
        cache.cache_detection_result({"id": 3}, SupportedFormat.ZEPHYR)

        # pylint: disable=protected-access
        assert len(cache._detection_result_cache) == 2
        assert cache._eviction_count == 1  # pylint: disable=protected-access

        # Last telemetry entry should mention evictions
        event_name, payload = telemetry_events[-1]
        assert event_name == "cache_metrics"
        assert payload["evictions"] >= 1
