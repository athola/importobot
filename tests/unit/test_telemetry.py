"""Comprehensive unit tests for telemetry module.

Following TDD principles, these tests verify:
- Environment variable parsing with edge cases
- TelemetryClient initialization and configuration
- Rate limiting and throttling behavior
- Thread-safe singleton pattern
- Exporter registration and lifecycle
- Cache metrics collection
"""

import json
import threading
from typing import List, Tuple
from unittest.mock import Mock, patch

import pytest

from importobot.telemetry import (
    TelemetryClient,
    TelemetryPayload,
    _flag_from_env,
    _float_from_env,
    _int_from_env,
    clear_telemetry_exporters,
    get_telemetry_client,
    register_telemetry_exporter,
    reset_telemetry_client,
)


class TestEnvironmentParsing:
    """Test environment variable parsing helpers."""

    def test_flag_from_env_default_false(self, monkeypatch):
        """By default, undefined flags return False."""
        monkeypatch.delenv("TEST_FLAG", raising=False)
        assert _flag_from_env("TEST_FLAG") is False

    def test_flag_from_env_default_true(self, monkeypatch):
        """Flags can specify a custom default."""
        monkeypatch.delenv("TEST_FLAG", raising=False)
        assert _flag_from_env("TEST_FLAG", default=True) is True

    @pytest.mark.parametrize(
        "value",
        ["1", "true", "True", "TRUE", "yes", "YES", "on", "ON", "  1  ", "  true  "],
    )
    def test_flag_from_env_truthy(self, monkeypatch, value):
        """Various truthy strings should parse as True."""
        monkeypatch.setenv("TEST_FLAG", value)
        assert _flag_from_env("TEST_FLAG") is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "random", "", "  "])
    def test_flag_from_env_falsy(self, monkeypatch, value):
        """Non-truthy strings should parse as False."""
        monkeypatch.setenv("TEST_FLAG", value)
        assert _flag_from_env("TEST_FLAG") is False

    def test_float_from_env_default(self, monkeypatch):
        """Undefined floats return the default."""
        monkeypatch.delenv("TEST_FLOAT", raising=False)
        assert _float_from_env("TEST_FLOAT", default=3.14) == 3.14

    @pytest.mark.parametrize(
        "value,expected", [("1.5", 1.5), ("0.0", 0.0), ("-2.5", -2.5), ("100", 100.0)]
    )
    def test_float_from_env_valid(self, monkeypatch, value, expected):
        """Valid numeric strings should parse correctly."""
        monkeypatch.setenv("TEST_FLOAT", value)
        assert _float_from_env("TEST_FLOAT", default=0.0) == expected

    @pytest.mark.parametrize("value", ["invalid", "", "3.14.15"])
    def test_float_from_env_invalid_returns_default(self, monkeypatch, value):
        """Invalid numeric strings should fall back to default."""
        monkeypatch.setenv("TEST_FLOAT", value)
        assert _float_from_env("TEST_FLOAT", default=42.0) == 42.0

    def test_int_from_env_default(self, monkeypatch):
        """Undefined ints return the default."""
        monkeypatch.delenv("TEST_INT", raising=False)
        assert _int_from_env("TEST_INT", default=10) == 10

    @pytest.mark.parametrize(
        "value,expected", [("42", 42), ("0", 0), ("-10", -10), ("1000", 1000)]
    )
    def test_int_from_env_valid(self, monkeypatch, value, expected):
        """Valid integer strings should parse correctly."""
        monkeypatch.setenv("TEST_INT", value)
        assert _int_from_env("TEST_INT", default=0) == expected

    @pytest.mark.parametrize("value", ["invalid", "", "3.14", "10.5"])
    def test_int_from_env_invalid_returns_default(self, monkeypatch, value):
        """Invalid integer strings should fall back to default."""
        monkeypatch.setenv("TEST_INT", value)
        assert _int_from_env("TEST_INT", default=99) == 99


class TestTelemetryClientInitialization:
    """Test TelemetryClient initialization and configuration."""

    def test_disabled_client_has_no_exporters(self):
        """Disabled clients should not register any exporters."""
        client = TelemetryClient(
            enabled=False, min_emit_interval=60.0, min_sample_delta=100
        )
        assert client.enabled is False
        assert len(client._exporters) == 0

    def test_enabled_client_registers_default_exporter(self):
        """Enabled clients should automatically register the logger exporter."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=60.0, min_sample_delta=100
        )
        assert client.enabled is True
        assert len(client._exporters) == 1

    def test_configuration_parameters_stored(self):
        """Client should store provided configuration."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=30.0, min_sample_delta=50
        )
        assert client._min_emit_interval == 30.0
        assert client._min_sample_delta == 50

    def test_thread_safe_initialization(self):
        """Client initialization should be thread-safe."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=60.0, min_sample_delta=100
        )
        assert isinstance(client._lock, type(threading.Lock()))
        assert isinstance(client._last_emit, dict)


class TestExporterManagement:
    """Test exporter registration and lifecycle."""

    def test_register_exporter_when_enabled(self):
        """Exporters should be registered when client is enabled."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=60.0, min_sample_delta=100
        )
        initial_count = len(client._exporters)

        custom_exporter = Mock()
        client.register_exporter(custom_exporter)

        assert len(client._exporters) == initial_count + 1
        assert custom_exporter in client._exporters

    def test_register_exporter_when_disabled_does_nothing(self):
        """Exporters should not be registered when client is disabled."""
        client = TelemetryClient(
            enabled=False, min_emit_interval=60.0, min_sample_delta=100
        )
        custom_exporter = Mock()
        client.register_exporter(custom_exporter)

        assert len(client._exporters) == 0

    def test_clear_exporters_enabled(self):
        """Clearing exporters should reset to default when enabled."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=60.0, min_sample_delta=100
        )
        client.register_exporter(Mock())
        client.register_exporter(Mock())

        client.clear_exporters()

        # Should keep only the default logger exporter
        assert len(client._exporters) == 1

    def test_clear_exporters_disabled(self):
        """Clearing exporters on disabled client should result in empty list."""
        client = TelemetryClient(
            enabled=False, min_emit_interval=60.0, min_sample_delta=100
        )
        client.clear_exporters()

        assert len(client._exporters) == 0

    def test_multiple_exporters_receive_events(self):
        """All registered exporters should receive emitted events."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        client.clear_exporters()

        exporter1 = Mock()
        exporter2 = Mock()
        client.register_exporter(exporter1)
        client.register_exporter(exporter2)

        client.record_cache_metrics("test_cache", hits=10, misses=5)

        exporter1.assert_called_once()
        exporter2.assert_called_once()

        # Verify both got the same event
        assert exporter1.call_args[0][0] == "cache_metrics"
        assert exporter2.call_args[0][0] == "cache_metrics"


class TestCacheMetricsRecording:
    """Test cache metrics recording with rate limiting."""

    def test_disabled_client_does_not_record(self):
        """Disabled clients should not record any metrics."""
        client = TelemetryClient(
            enabled=False, min_emit_interval=60.0, min_sample_delta=100
        )
        exporter = Mock()
        client.register_exporter(exporter)

        client.record_cache_metrics("test_cache", hits=100, misses=50)

        exporter.assert_not_called()

    def test_basic_metric_recording(self):
        """Client should record metrics with correct structure."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        client.clear_exporters()

        events: List[Tuple[str, TelemetryPayload]] = []
        client.register_exporter(lambda name, payload: events.append((name, payload)))

        client.record_cache_metrics("test_cache", hits=80, misses=20)

        assert len(events) == 1
        event_name, payload = events[0]
        assert event_name == "cache_metrics"
        assert payload["cache_name"] == "test_cache"
        assert payload["hits"] == 80
        assert payload["misses"] == 20
        assert payload["total_requests"] == 100
        assert payload["hit_rate"] == 0.8
        assert "timestamp" in payload

    def test_hit_rate_calculation(self):
        """Hit rate should be calculated correctly."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        client.clear_exporters()

        events: List[Tuple[str, TelemetryPayload]] = []
        client.register_exporter(lambda name, payload: events.append((name, payload)))

        # 100% hit rate
        client.record_cache_metrics("cache1", hits=100, misses=0)
        assert events[-1][1]["hit_rate"] == 1.0

        # 0% hit rate
        client.record_cache_metrics("cache2", hits=0, misses=100)
        assert events[-1][1]["hit_rate"] == 0.0

        # 50% hit rate
        client.record_cache_metrics("cache3", hits=50, misses=50)
        assert events[-1][1]["hit_rate"] == 0.5

    def test_zero_requests_hit_rate(self):
        """Zero requests should result in 0.0 hit rate without division error."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        client.clear_exporters()

        events: List[Tuple[str, TelemetryPayload]] = []
        client.register_exporter(lambda name, payload: events.append((name, payload)))

        client.record_cache_metrics("empty_cache", hits=0, misses=0)

        assert events[-1][1]["hit_rate"] == 0.0

    def test_extras_payload_merged(self):
        """Extra payload fields should be merged into metrics."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        client.clear_exporters()

        events: List[Tuple[str, TelemetryPayload]] = []
        client.register_exporter(lambda name, payload: events.append((name, payload)))

        extras: dict[str, object] = {"cache_size": 500, "max_size": 1000}
        client.record_cache_metrics("test_cache", hits=10, misses=5, extras=extras)

        payload = events[-1][1]
        assert payload["cache_size"] == 500
        assert payload["max_size"] == 1000

    def test_rate_limiting_by_sample_delta(self):
        """Metrics should be throttled based on sample delta.

        Rate limiting uses AND logic: both conditions must be met to throttle.
        """
        client = TelemetryClient(
            enabled=True, min_emit_interval=999999.0, min_sample_delta=100
        )
        client.clear_exporters()

        events: List[Tuple[str, TelemetryPayload]] = []
        client.register_exporter(lambda name, payload: events.append((name, payload)))

        # First call should emit
        client.record_cache_metrics("cache", hits=10, misses=5)
        initial_count = len(events)

        # Second call with < 100 more samples AND within interval should not emit
        client.record_cache_metrics("cache", hits=20, misses=10)
        assert len(events) == initial_count  # No new emission

        # Third call with >= 100 more samples should emit (exceeds delta threshold)
        client.record_cache_metrics("cache", hits=110, misses=40)
        assert len(events) == initial_count + 1  # One new emission

    def test_rate_limiting_by_time_interval(self):
        """Metrics should be throttled based on time interval."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=60.0, min_sample_delta=999999
        )
        client.clear_exporters()

        events: List[Tuple[str, TelemetryPayload]] = []
        client.register_exporter(lambda name, payload: events.append((name, payload)))

        base_time = 1000.0

        # First call should emit
        with patch("importobot.telemetry.time.time", return_value=base_time):
            client.record_cache_metrics("cache", hits=10, misses=5)
        initial_count = len(events)

        # Second call within interval AND under sample delta should not emit
        with patch("importobot.telemetry.time.time", return_value=base_time + 30):
            client.record_cache_metrics("cache", hits=20, misses=10)
        assert len(events) == initial_count  # No new emission

        # Third call after interval should emit (exceeds time threshold)
        with patch("importobot.telemetry.time.time", return_value=base_time + 61):
            client.record_cache_metrics("cache", hits=30, misses=15)
        assert len(events) == initial_count + 1  # One new emission

    def test_separate_caches_tracked_independently(self):
        """Different cache names should have independent rate limiting."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=60.0, min_sample_delta=100
        )
        client.clear_exporters()

        events: List[Tuple[str, TelemetryPayload]] = []
        client.register_exporter(lambda name, payload: events.append((name, payload)))

        client.record_cache_metrics("cache1", hits=10, misses=5)
        client.record_cache_metrics("cache2", hits=20, misses=10)

        assert len(events) == 2
        assert events[0][1]["cache_name"] == "cache1"
        assert events[1][1]["cache_name"] == "cache2"


class TestExporterErrorHandling:
    """Test that exporter failures don't crash the client."""

    def test_failing_exporter_does_not_crash(self):
        """Exceptions in exporters should be caught and logged."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        client.clear_exporters()

        def failing_exporter(name, payload):
            raise RuntimeError("Simulated exporter failure")

        working_exporter = Mock()

        client.register_exporter(failing_exporter)
        client.register_exporter(working_exporter)

        # Should not raise despite failing exporter
        client.record_cache_metrics("cache", hits=10, misses=5)

        # Working exporter should still be called
        working_exporter.assert_called_once()

    def test_default_logger_exporter_format(self):
        """Default logger exporter should produce valid JSON."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )

        # Capture logger output
        with patch("importobot.telemetry.logger.warning") as mock_log:
            client.record_cache_metrics("test", hits=10, misses=5)

            mock_log.assert_called_once()
            # The format is: logger.warning("telemetry.%s %s", event_name, json_string)
            # So args are: (format_string, event_name, json_string)
            assert len(mock_log.call_args[0]) == 3
            _log_format, event_name, json_msg = mock_log.call_args[0]

            assert event_name == "cache_metrics"
            # Should be valid JSON
            payload = json.loads(json_msg)
            assert payload["cache_name"] == "test"
            assert payload["hits"] == 10


class TestGlobalSingleton:
    """Test global telemetry client singleton."""

    def test_get_telemetry_client_returns_singleton(self):
        """Multiple calls should return the same instance."""
        reset_telemetry_client()

        client1 = get_telemetry_client()
        client2 = get_telemetry_client()

        assert client1 is client2

    def test_reset_telemetry_client_clears_singleton(self):
        """Reset should allow new instance creation."""
        client1 = get_telemetry_client()
        reset_telemetry_client()
        client2 = get_telemetry_client()

        assert client1 is not client2

    def test_global_register_exporter(self, monkeypatch):
        """Global function should register on singleton."""
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
        reset_telemetry_client()

        exporter = Mock()
        register_telemetry_exporter(exporter)

        client = get_telemetry_client()
        assert exporter in client._exporters

    def test_global_clear_exporters(self, monkeypatch):
        """Global function should clear exporters on singleton."""
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
        reset_telemetry_client()

        register_telemetry_exporter(Mock())
        clear_telemetry_exporters()

        client = get_telemetry_client()
        # Should only have default exporter
        assert len(client._exporters) == 1

    def test_singleton_initialization_from_env(self, monkeypatch):
        """Singleton should initialize from environment variables."""
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_INTERVAL_SECONDS", "30")
        monkeypatch.setenv("IMPORTOBOT_TELEMETRY_MIN_SAMPLE_DELTA", "50")
        reset_telemetry_client()

        client = get_telemetry_client()

        assert client.enabled is True
        assert client._min_emit_interval == 30.0
        assert client._min_sample_delta == 50

    def test_singleton_disabled_by_default(self, monkeypatch):
        """Telemetry should be disabled by default."""
        monkeypatch.delenv("IMPORTOBOT_ENABLE_TELEMETRY", raising=False)
        reset_telemetry_client()

        client = get_telemetry_client()

        assert client.enabled is False


class TestThreadSafety:
    """Test thread-safety of telemetry client."""

    def test_concurrent_metric_recording(self):
        """Concurrent metric recording should be thread-safe."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=0.0, min_sample_delta=0
        )
        client.clear_exporters()

        events: List[Tuple[str, TelemetryPayload]] = []
        lock = threading.Lock()

        def thread_safe_exporter(name, payload):
            with lock:
                events.append((name, payload))

        client.register_exporter(thread_safe_exporter)

        threads = []
        for i in range(10):

            def record_metrics(cache_id=i):
                for _ in range(100):
                    client.record_cache_metrics(f"cache_{cache_id}", hits=10, misses=5)

            thread = threading.Thread(target=record_metrics)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have recorded metrics from all threads
        assert len(events) >= 10  # At least one per cache

    def test_concurrent_exporter_registration(self):
        """Concurrent exporter registration should be thread-safe."""
        client = TelemetryClient(
            enabled=True, min_emit_interval=60.0, min_sample_delta=100
        )

        def register_exporter():
            for _ in range(10):
                client.register_exporter(Mock())

        threads = [threading.Thread(target=register_exporter) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should have registered all exporters
        # 1 default + 5 threads * 10 exporters = 51
        assert len(client._exporters) == 51

    def test_global_singleton_thread_safety(self, monkeypatch):
        """Global singleton should be thread-safe during initialization."""
        monkeypatch.setenv("IMPORTOBOT_ENABLE_TELEMETRY", "1")
        reset_telemetry_client()

        clients = []
        lock = threading.Lock()

        def get_client():
            client = get_telemetry_client()
            with lock:
                clients.append(client)

        threads = [threading.Thread(target=get_client) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All threads should get the same instance
        assert len({id(c) for c in clients}) == 1
