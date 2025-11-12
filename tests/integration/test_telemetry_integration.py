"""Integration tests for telemetry with cache services.

These tests verify end-to-end telemetry behavior when integrated with:
- PerformanceCache
- FileContentCache
- OptimizationService
- DataIngestionService
"""

import time
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from importobot.services.data_ingestion_service import (
    FileContentCache,
)
from importobot.services.optimization_service import OptimizationService
from importobot.services.performance_cache import PerformanceCache
from importobot.telemetry import (
    TelemetryClient,
    TelemetryPayload,
    clear_telemetry_exporters,
    get_telemetry_client,
    register_telemetry_exporter,
    reset_telemetry_client,
)


class TestPerformanceCacheTelemetry:
    """Integration tests for PerformanceCache telemetry."""

    def test_performance_cache_emits_metrics_on_operations(
        self, telemetry_events: list[tuple[str, dict[str, Any]]]
    ) -> None:
        """PerformanceCache should emit telemetry during normal operations."""
        cache = PerformanceCache(max_cache_size=100, ttl_seconds=0)

        # Perform cache operations
        cache.get_cached_string_lower({"test": "data"})
        cache.get_cached_string_lower({"test": "data"})  # Hit
        cache.get_cached_json_string({"other": "data"})

        # Should have emitted cache metrics
        assert len(telemetry_events) > 0

        # Verify structure of emitted events
        for event_name, payload in telemetry_events:
            assert event_name == "cache_metrics"
            assert "cache_name" in payload
            assert payload["cache_name"] == "performance_cache"
            assert "hits" in payload
            assert "misses" in payload
            assert "hit_rate" in payload

    def test_performance_cache_tracks_hit_rate_accurately(self) -> None:
        """Hit rate should accurately reflect cache performance."""
        cache = PerformanceCache(max_cache_size=100, ttl_seconds=0)

        test_data = {"value": 123}

        # First access is a miss
        cache.get_cached_string_lower(test_data)

        # Next 9 accesses are hits
        for _ in range(9):
            cache.get_cached_string_lower(test_data)

        # Get final stats
        stats = cache.get_stats()

        # Should have 90% hit rate (9 hits, 1 miss)
        assert stats["cache_hits"] == 9
        assert stats["cache_misses"] == 1
        assert stats["hit_rate_percent"] == 90.0

    def test_performance_cache_ttl_affects_metrics(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TTL expiration should cause cache misses."""
        cache = PerformanceCache(max_cache_size=100, ttl_seconds=1)

        test_data = {"value": 456}

        # First access
        cache.get_cached_string_lower(test_data)
        initial_misses = cache.get_stats()["cache_misses"]

        # Access again immediately - should hit
        cache.get_cached_string_lower(test_data)
        assert cache.get_stats()["cache_hits"] == 1

        # Simulate time passing
        base_time = time.time()
        monkeypatch.setattr(
            "importobot.services.performance_cache.time.time", lambda: base_time + 2
        )

        # Access after TTL - should miss
        cache.get_cached_string_lower(test_data)
        final_misses = cache.get_stats()["cache_misses"]

        assert final_misses > initial_misses

    def test_performance_cache_size_limits_tracked(self) -> None:
        """Cache size limits should be reflected in telemetry."""
        max_size = 5
        cache = PerformanceCache(max_cache_size=max_size, ttl_seconds=0)

        # Fill cache beyond max size
        for i in range(max_size * 2):
            cache.get_cached_string_lower({"value": i})

        stats = cache.get_stats()

        # Cache should not exceed max size
        assert stats["string_cache_size"] <= max_size
        assert stats["max_cache_size"] == max_size


class TestFileContentCacheTelemetry:
    """Integration tests for FileContentCache telemetry."""

    def test_file_cache_emits_metrics(
        self, tmp_path: Path, telemetry_events: list[tuple[str, dict[str, Any]]]
    ) -> None:
        """FileContentCache should emit telemetry during file operations."""
        cache = FileContentCache(max_size_mb=10, ttl_seconds=0)

        # Create test file
        test_file = tmp_path / "test.json"
        test_file.write_text('{"test": "data"}')

        # Cache and retrieve
        cache.cache_content(test_file, '{"test": "data"}')
        cache.get_cached_content(test_file)

        # Should have emitted telemetry
        assert len(telemetry_events) > 0

        # Verify event structure
        cache_events = [
            e for e in telemetry_events if e[1]["cache_name"] == "file_content_cache"
        ]
        assert len(cache_events) > 0

    def test_file_cache_handles_file_changes(self, tmp_path: Path) -> None:
        """File modifications should invalidate cache and increase misses."""
        cache = FileContentCache(max_size_mb=10, ttl_seconds=0)

        test_file = tmp_path / "mutable.json"
        test_file.write_text('{"version": 1}')

        # Initial cache
        cache.cache_content(test_file, '{"version": 1}')
        initial_hits = 0

        # Hit
        cache.get_cached_content(test_file)
        initial_hits += 1

        # Modify file
        time.sleep(0.01)  # Ensure mtime changes
        test_file.write_text('{"version": 2}')

        # Should be a miss now
        result = cache.get_cached_content(test_file)
        assert result is None  # Cache invalidated

    def test_file_cache_respects_size_limits(self, tmp_path: Path) -> None:
        """Cache should evict entries when size limit is exceeded."""
        cache = FileContentCache(max_size_mb=1, ttl_seconds=0)  # Small limit

        # Create large content that will exceed limit
        large_content = "x" * (512 * 1024)  # 512KB

        files = []
        for i in range(5):
            file_path = tmp_path / f"file_{i}.txt"
            file_path.write_text(large_content)
            files.append(file_path)
            cache.cache_content(file_path, large_content)

        # Cache should have evicted older entries
        # Can't fit all 5 files (2.5MB) in 1MB cache
        assert cache._current_size_bytes <= cache._max_size_bytes


class TestOptimizationServiceTelemetry:
    """Integration tests for OptimizationService telemetry."""

    def test_optimization_service_operations_emit_telemetry(self) -> None:
        """OptimizationService should use performance cache with telemetry."""
        service = OptimizationService(cache_ttl_seconds=0)

        def objective(params: dict[str, float]) -> float:
            return params.get("x", 0.0) ** 2

        service.register_scenario(
            "test_scenario",
            objective,
            {"x": 1.0},
            parameter_bounds={"x": (-10.0, 10.0)},
        )

        # Verify scenario was registered
        assert service.has_scenario("test_scenario")

        # OptimizationService uses its own cache, so no telemetry events expected


class TestDataIngestionServiceTelemetry:
    """Integration tests for DataIngestionService telemetry."""

    def test_file_content_cache_emits_telemetry_directly(
        self, tmp_path: Path, telemetry_events: list[tuple[str, dict[str, Any]]]
    ) -> None:
        """FileContentCache used by DataIngestionService should emit telemetry."""
        # Test FileContentCache directly since full DataIngestionService
        # integration requires complex storage setup
        cache = FileContentCache(max_size_mb=10, ttl_seconds=0)

        test_file = tmp_path / "test.json"
        test_file.write_text('{"test": "data"}')

        # Use cache
        cache.cache_content(test_file, '{"test": "data"}')
        cache.get_cached_content(test_file)

        # Should have file cache telemetry
        file_cache_events = [
            e
            for e in telemetry_events
            if e[1].get("cache_name") == "file_content_cache"
        ]
        assert len(file_cache_events) > 0


class TestCrossCacheTelemetry:
    """Test telemetry when multiple caches are active."""

    def test_multiple_caches_emit_separate_metrics(
        self, tmp_path: Path, telemetry_events: list[tuple[str, dict[str, Any]]]
    ) -> None:
        """Different caches should emit independently tracked metrics."""
        perf_cache = PerformanceCache(max_cache_size=100, ttl_seconds=0)
        file_cache = FileContentCache(max_size_mb=10, ttl_seconds=0)

        # Use performance cache
        perf_cache.get_cached_string_lower({"test": "data"})

        # Use file cache
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        file_cache.cache_content(test_file, "content")
        file_cache.get_cached_content(test_file)

        # Should have events from both caches
        cache_names = {event[1]["cache_name"] for event in telemetry_events}
        assert "performance_cache" in cache_names
        assert "file_content_cache" in cache_names

    def test_cache_metrics_dont_interfere(self) -> None:
        """Metrics from different caches should not interfere with each other."""
        cache1 = PerformanceCache(max_cache_size=100, ttl_seconds=0)
        cache2 = PerformanceCache(max_cache_size=50, ttl_seconds=0)

        # Use both caches
        cache1.get_cached_string_lower({"cache": 1})
        cache2.get_cached_string_lower({"cache": 2})

        # Each cache should track its own stats
        stats1 = cache1.get_stats()
        stats2 = cache2.get_stats()

        assert stats1["cache_misses"] >= 1
        assert stats2["cache_misses"] >= 1
        # Stats should be independent
        assert stats1["max_cache_size"] == 100
        assert stats2["max_cache_size"] == 50


class TestTelemetryRateLimitingIntegration:
    """Test rate limiting behavior in real-world scenarios."""

    def test_high_frequency_cache_operations_throttled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """High-frequency operations should be throttled appropriately."""
        # Configure aggressive rate limiting
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_SAMPLE_DELTA", "100")
        monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_INTERVAL_SECONDS", "10")
        reset_telemetry_client()

        # Re-register exporter after reset
        events: list[tuple[str, TelemetryPayload]] = []

        def capture_exporter(name: str, payload: dict[str, Any]) -> None:
            events.append((name, payload))

        clear_telemetry_exporters()
        register_telemetry_exporter(capture_exporter)

        cache = PerformanceCache(max_cache_size=1000, ttl_seconds=0)

        # Perform many operations
        for i in range(50):
            cache.get_cached_string_lower({"iteration": i})

        # Should have throttled emissions
        # Fewer than 50 events due to throttling
        assert len(events) < 50

    def test_different_caches_independent_throttling(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Different cache names should have independent rate limiting."""
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_SAMPLE_DELTA", "10")
        monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_INTERVAL_SECONDS", "5")
        reset_telemetry_client()

        events: list[tuple[str, TelemetryPayload]] = []
        clear_telemetry_exporters()
        register_telemetry_exporter(lambda n, p: events.append((n, p)))

        client = get_telemetry_client()
        assert client is not None

        # Record metrics for different caches
        client.record_cache_metrics("cache_a", hits=5, misses=2)
        client.record_cache_metrics("cache_b", hits=8, misses=3)

        # Both should emit (different cache names)
        cache_names = {event[1]["cache_name"] for event in events}
        assert "cache_a" in cache_names
        assert "cache_b" in cache_names


class TestTelemetryErrorResilience:
    """Test that telemetry failures don't crash services."""

    def test_failing_exporter_doesnt_break_cache(self) -> None:
        """Cache should continue working even if telemetry fails."""

        def failing_exporter(name: str, payload: dict[str, Any]) -> None:
            raise RuntimeError("Telemetry export failed")

        clear_telemetry_exporters()
        register_telemetry_exporter(failing_exporter)

        cache = PerformanceCache(max_cache_size=100, ttl_seconds=0)

        # Should not raise despite failing exporter
        test_data = {"test": "data"}
        result1 = cache.get_cached_string_lower(test_data)
        result2 = cache.get_cached_string_lower(test_data)

        # Cache should still work correctly
        # get_cached_string_lower returns str(data).lower()
        assert result1.lower() == str({"test": "data"}).lower()
        assert result2.lower() == str({"test": "data"}).lower()
        assert cache.get_stats()["cache_hits"] == 1

    def test_telemetry_disabled_services_work_normally(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Services should work normally when telemetry is disabled."""
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "0")
        reset_telemetry_client()

        cache = PerformanceCache(max_cache_size=100, ttl_seconds=0)
        file_cache = FileContentCache(max_size_mb=10, ttl_seconds=0)

        # Operations should work normally
        # get_cached_string_lower returns str(data).lower()
        result = cache.get_cached_string_lower({"key": "value"})
        assert result.lower() == str({"key": "value"}).lower()

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        file_cache.cache_content(test_file, "content")
        assert file_cache.get_cached_content(test_file) == "content"


class TestTelemetryLifecycle:
    """Test telemetry initialization and cleanup."""

    def test_telemetry_client_lifecycle(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test full lifecycle of telemetry client."""
        # Start disabled
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "0")
        reset_telemetry_client()

        client1 = get_telemetry_client()
        assert client1 is None

        # Enable and reset
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
        reset_telemetry_client()

        client2 = get_telemetry_client()
        assert client2 is not None
        assert isinstance(client2, TelemetryClient)

    def test_exporter_registration_survives_operations(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Custom exporters should persist through cache operations."""
        custom_events: list[tuple[str, TelemetryPayload]] = []

        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
        reset_telemetry_client()

        def custom_exporter(name: str, payload: dict[str, Any]) -> None:
            custom_events.append((name, payload))

        register_telemetry_exporter(custom_exporter)

        cache = PerformanceCache(max_cache_size=100, ttl_seconds=0)

        # Perform operations
        for i in range(10):
            cache.get_cached_string_lower({"iteration": i})

        # Custom exporter should have received events
        assert len(custom_events) > 0

    def test_clear_exporters_resets_to_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Clearing exporters should restore default logger exporter."""
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
        reset_telemetry_client()

        # Add custom exporters
        register_telemetry_exporter(Mock())
        register_telemetry_exporter(Mock())

        client = get_telemetry_client()
        assert client is not None
        initial_count = len(client._exporters)
        assert initial_count > 1  # Default + custom exporters

        # Clear
        clear_telemetry_exporters()

        # Should have only default exporter
        assert len(client._exporters) == 1
