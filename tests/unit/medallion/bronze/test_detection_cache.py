"""Tests for DetectionCache configuration safeguards."""

from importobot.medallion.bronze.detection_cache import DetectionCache


# pylint: disable=protected-access
class TestDetectionCacheConfiguration:
    """Validate collision chain limit configuration behaviour."""

    def test_default_collision_limit(self):
        """Default limit uses class constant."""
        cache = DetectionCache()
        assert cache._max_collision_chain_length == cache.MAX_COLLISION_CHAIN_LENGTH

    def test_constructor_override_takes_precedence(self):
        """Constructor argument overrides default."""
        cache = DetectionCache(collision_chain_limit=5)
        assert cache._max_collision_chain_length == 5

    def test_env_variable_sets_limit(self, monkeypatch):
        """Environment variable configures limit when provided."""
        monkeypatch.setenv("IMPORTOBOT_DETECTION_CACHE_COLLISION_LIMIT", "7")
        cache = DetectionCache()
        assert cache._max_collision_chain_length == 7

    def test_invalid_env_falls_back_to_default(self, monkeypatch, caplog):
        """Invalid environment input falls back and logs a warning."""
        monkeypatch.setenv("IMPORTOBOT_DETECTION_CACHE_COLLISION_LIMIT", "not-a-number")
        with caplog.at_level("WARNING"):
            cache = DetectionCache()
        assert cache._max_collision_chain_length == cache.MAX_COLLISION_CHAIN_LENGTH
        assert "Invalid IMPORTOBOT_DETECTION_CACHE_COLLISION_LIMIT" in caplog.text

    def test_reject_non_positive_limits(self, monkeypatch, caplog):
        """Non-positive limits are rejected and a warning emitted."""
        monkeypatch.setenv("IMPORTOBOT_DETECTION_CACHE_COLLISION_LIMIT", "0")
        with caplog.at_level("WARNING"):
            cache = DetectionCache(collision_chain_limit=0)
        assert cache._max_collision_chain_length == cache.MAX_COLLISION_CHAIN_LENGTH
        assert "Collision chain limit" in caplog.text
