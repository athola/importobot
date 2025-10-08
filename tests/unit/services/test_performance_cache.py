"""Tests for performance and file content caches."""

import time
from pathlib import Path

import pytest

from importobot.services.data_ingestion_service import FileContentCache
from importobot.services.performance_cache import PerformanceCache


class TestPerformanceCacheTTL:
    """Ensure performance cache entries expire when TTL is set."""

    def test_string_cache_ttl_expires(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that cache entries expire after TTL seconds."""
        cache = PerformanceCache(ttl_seconds=1)
        payload = {"value": 1}

        first = cache.get_cached_string_lower(payload)
        assert first == str(payload).lower()

        base_time = time.time()
        monkeypatch.setattr(
            "importobot.services.performance_cache.time.time",
            lambda: base_time + 2,
        )

        second = cache.get_cached_string_lower(payload)
        assert second == str(payload).lower()
        # TTL expiration should force a cache miss then reinsert, so hit count resets
        assert cache.get_cache_stats()["cache_hits"] == 0


class TestFileContentCacheTTL:
    """Ensure file content cache respects TTL."""

    def test_file_cache_ttl_expires(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that file content cache entries expire after TTL."""
        cache = FileContentCache(ttl_seconds=1)
        file_path = tmp_path / "sample.json"
        file_path.write_text("data")

        cache.cache_content(file_path, "data")

        base_time = time.time()
        monkeypatch.setattr(
            "importobot.services.data_ingestion_service.time.time",
            lambda: base_time + 2,
        )

        assert cache.get_cached_content(file_path) is None


class TestCacheTelemetry:
    """Telemetry emission smoke tests for cache instrumentation."""

    def test_performance_cache_emits_telemetry(
        self, telemetry_events: list[tuple[str, dict[str, object]]]
    ) -> None:
        """Test that performance cache emits telemetry events."""
        cache = PerformanceCache(ttl_seconds=0)
        cache.get_cached_string_lower("payload")
        cache.get_cached_string_lower("payload")

        assert telemetry_events
        event_name, payload = telemetry_events[-1]
        assert event_name == "cache_metrics"
        assert payload["cache_name"] == "performance_cache"
        assert isinstance(payload["hits"], int) and payload["hits"] >= 0

    def test_file_content_cache_emits_telemetry(
        self,
        tmp_path: Path,
        telemetry_events: list[tuple[str, dict[str, object]]],
    ) -> None:
        """Test that file content cache emits telemetry events."""
        cache = FileContentCache(ttl_seconds=0)
        file_path = tmp_path / "content.json"
        file_path.write_text("data", encoding="utf-8")

        cache.cache_content(file_path, "data")
        # First access counts as hit after initial cache population
        cache.get_cached_content(file_path)

        assert telemetry_events
        event_name, payload = telemetry_events[-1]
        assert event_name == "cache_metrics"
        assert payload["cache_name"] == "file_content_cache"
        assert isinstance(payload["hits"], int) and payload["hits"] >= 1
