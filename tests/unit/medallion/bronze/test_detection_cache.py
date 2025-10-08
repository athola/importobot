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
