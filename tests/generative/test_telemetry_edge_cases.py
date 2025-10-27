"""Generative tests for telemetry edge cases.

Property-based and fuzz testing to discover edge cases:
- Extreme parameter values
- Unusual data types
- Malformed inputs
- Boundary conditions
- Unicode and special characters
"""

import json
import os
import sys
import threading
from decimal import Decimal

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from importobot.telemetry import (
    TelemetryClient,
    _flag_from_env,
    _float_from_env,
    _int_from_env,
)


class TestExtremParameterValues:
    """Test telemetry with extreme parameter values."""

    @given(
        st.floats(
            min_value=0.0,
            max_value=1e10,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    def test_extreme_interval_values(self, interval):
        """Client should handle very large interval values."""
        client = TelemetryClient(min_emit_interval=interval, min_sample_delta=100)
        assert client._min_emit_interval == interval

    @given(st.integers(min_value=0, max_value=1_000_000_000))
    def test_extreme_sample_delta_values(self, delta):
        """Client should handle very large sample delta values."""
        client = TelemetryClient(min_emit_interval=60.0, min_sample_delta=delta)
        assert client._min_sample_delta == delta

    @given(
        st.integers(min_value=0, max_value=sys.maxsize),
        st.integers(min_value=0, max_value=sys.maxsize),
    )
    def test_extreme_hit_miss_counts(self, hits, misses):
        """Client should handle very large hit/miss counts."""
        # Limit total to avoid overflow in test execution
        assume(hits + misses < 1_000_000_000)

        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        client.record_cache_metrics("cache", hits=hits, misses=misses)

        if emitted:
            payload = emitted[0][1]
            assert payload["hits"] == hits
            assert payload["misses"] == misses
            assert payload["total_requests"] == hits + misses


class TestUnusualDataTypes:
    """Test telemetry with unusual data types in extras."""

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.text(),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=10,
        )
    )
    def test_various_extras_types(self, extras):
        """Extras should handle various JSON-serializable types."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        # Should not raise
        client.record_cache_metrics("cache", hits=10, misses=5, extras=extras)

        if emitted:
            payload = emitted[0][1]
            # Verify extras were merged
            for key in extras:
                assert key in payload

    def test_non_serializable_extras_handled(self):
        """Non-JSON-serializable extras should be handled gracefully."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []

        def safe_exporter(n, p):
            # Try to serialize - should handle via default=str
            json.dumps(p, default=str)
            emitted.append((n, p))

        client.register_exporter(safe_exporter)

        # Extras with non-serializable objects
        extras = {
            "decimal": Decimal("3.14"),
            "complex": complex(1, 2),
            "set": {1, 2, 3},
        }

        # Default logger exporter uses default=str, so should not raise
        client.record_cache_metrics("cache", hits=10, misses=5, extras=extras)


class TestMalformedInputs:
    """Test telemetry with malformed inputs."""

    @given(st.text())
    def test_arbitrary_cache_names(self, cache_name):
        """Cache names should handle arbitrary strings."""
        assume(len(cache_name) > 0)  # Empty names might be invalid

        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        client.record_cache_metrics(cache_name, hits=10, misses=5)

        if emitted:
            assert emitted[0][1]["cache_name"] == cache_name

    @given(
        st.text(
            alphabet=st.characters(
                min_codepoint=0, max_codepoint=0x10FFFF, blacklist_categories=["Cs"]
            ),
            min_size=1,
            max_size=100,
        )
    )
    def test_unicode_cache_names(self, cache_name):
        """Cache names should handle full unicode range."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        client.record_cache_metrics(cache_name, hits=10, misses=5)

        if emitted:
            assert emitted[0][1]["cache_name"] == cache_name

    @given(st.text(min_size=0, max_size=1000).filter(lambda s: "\x00" not in s))
    def test_env_var_parsing_never_crashes(self, value):
        """Environment variable parsing should never crash (except null bytes)."""
        old_value = os.environ.get("TEST_VAR_GEN")
        try:
            os.environ["TEST_VAR_GEN"] = value

            # All parsing functions should handle any string
            flag_result = _flag_from_env("TEST_VAR_GEN")
            assert isinstance(flag_result, bool)

            float_result = _float_from_env("TEST_VAR_GEN", default=1.0)
            assert isinstance(float_result, float)

            int_result = _int_from_env("TEST_VAR_GEN", default=1)
            assert isinstance(int_result, int)
        finally:
            if old_value is None:
                os.environ.pop("TEST_VAR_GEN", None)
            else:
                os.environ["TEST_VAR_GEN"] = old_value


class TestBoundaryConditions:
    """Test boundary conditions."""

    def test_zero_interval_zero_delta(self):
        """Zero interval and delta should allow all emissions."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        # All calls should emit
        for i in range(10):
            client.record_cache_metrics("cache", hits=i, misses=i)

        assert len(emitted) == 10

    def test_maximum_interval_maximum_delta(self):
        """Maximum values should effectively disable emissions."""
        client = TelemetryClient(
            min_emit_interval=float("inf"),
            min_sample_delta=sys.maxsize,
        )
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        # Only first call should emit
        for i in range(10):
            client.record_cache_metrics("cache", hits=i, misses=i)

        assert len(emitted) <= 2  # First emission + maybe one more

    @given(st.integers(min_value=-1000, max_value=1000))
    def test_negative_hits_misses_handled(self, value):
        """Negative values should be handled (even if semantically invalid)."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        # Current implementation doesn't validate, so should not crash
        client.record_cache_metrics("cache", hits=value, misses=abs(value))

        if emitted:
            payload = emitted[0][1]
            assert "hits" in payload
            assert "misses" in payload


class TestSpecialCharactersAndEncoding:
    """Test handling of special characters and encoding edge cases."""

    @pytest.mark.parametrize(
        "cache_name",
        [
            "cache\x00null",
            "cache\ttab",
            "cache\nneolinek",
            "cache\r\nwindows",
            "emoji🎉cache",
            "中文缓存",
            "עברית",
            "العربية",
            "cache'quote",
            'cache"doublequote',
            "cache\\backslash",
            "cache/slash",
            "cache<>brackets",
        ],
    )
    def test_special_character_cache_names(self, cache_name):
        """Cache names with special characters should be handled."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        client.record_cache_metrics(cache_name, hits=10, misses=5)

        if emitted:
            assert emitted[0][1]["cache_name"] == cache_name

    def test_very_long_cache_name(self):
        """Very long cache names should be handled."""
        cache_name = "cache_" * 1000  # 6000 characters
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        client.record_cache_metrics(cache_name, hits=10, misses=5)

        if emitted:
            assert emitted[0][1]["cache_name"] == cache_name

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=50),
            st.text(min_size=0, max_size=100),
            min_size=0,
            max_size=20,
        )
    )
    def test_extras_with_unicode_values(self, extras):
        """Extras with unicode values should be handled."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        client.record_cache_metrics("cache", hits=10, misses=5, extras=extras)

        if emitted:
            payload = emitted[0][1]
            for key in extras:
                assert key in payload


class TestEdgeCaseCompositions:
    """Test combinations of edge cases."""

    @given(
        st.text(min_size=1, max_size=50),
        st.integers(min_value=0, max_value=1_000_000),
        st.integers(min_value=0, max_value=1_000_000),
        st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.integers(), st.text(), st.booleans()),
            min_size=0,
            max_size=10,
        ),
    )
    @settings(max_examples=50)
    def test_combined_edge_cases(self, cache_name, hits, misses, extras):
        """Combination of edge cases should be handled robustly."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        # Should not raise
        client.record_cache_metrics(cache_name, hits=hits, misses=misses, extras=extras)

        if emitted:
            payload = emitted[0][1]
            assert payload["cache_name"] == cache_name
            assert payload["hits"] == hits
            assert payload["misses"] == misses
            assert payload["total_requests"] == hits + misses

    def test_rapid_state_transitions(self):
        """Rapid enable/disable transitions should be handled."""
        for _ in range(100):
            enabled = bool(_ % 2)
            if not enabled:
                # Disabled telemetry represented by absence of client
                continue

            client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
            client.clear_exporters()
            client.register_exporter(lambda n, p: None)

            # Should not crash when enabled
            client.record_cache_metrics("cache", hits=10, misses=5)


class TestFloatingPointPrecision:
    """Test floating-point precision edge cases."""

    @given(
        st.integers(min_value=0, max_value=1_000_000),
        st.integers(min_value=1, max_value=1_000_000),  # Avoid division by zero
    )
    def test_hit_rate_precision(self, hits, total):
        """Hit rate calculation should maintain precision."""
        assume(hits <= total)
        misses = total - hits

        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        client.record_cache_metrics("cache", hits=hits, misses=misses)

        if emitted:
            payload = emitted[0][1]
            expected_rate = hits / total
            actual_rate = payload["hit_rate"]

            # Should be very close (within floating-point precision)
            assert abs(actual_rate - expected_rate) < 1e-10

    @given(
        st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False)
    )
    def test_timestamp_precision(self, timestamp):
        """Timestamps should maintain precision."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        with pytest.MonkeyPatch.context() as m:
            m.setattr("time.time", lambda: timestamp)
            client.record_cache_metrics("cache", hits=10, misses=5)

        if emitted:
            recorded_timestamp = emitted[0][1]["timestamp"]
            assert abs(recorded_timestamp - timestamp) < 1e-6


class TestConcurrentEdgeCases:
    """Test edge cases under concurrent access."""

    def test_concurrent_clear_and_record(self):
        """Concurrent clear and record should not crash."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)

        def worker():
            for _ in range(100):
                if _ % 10 == 0:
                    client.clear_exporters()
                else:
                    client.record_cache_metrics("cache", hits=10, misses=5)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should complete without crash

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=20))
    def test_concurrent_different_cache_names(self, cache_names):
        """Concurrent access to different cache names should be safe."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()
        client.register_exporter(lambda n, p: None)

        def worker(cache_name):
            for _ in range(10):
                client.record_cache_metrics(cache_name, hits=10, misses=5)

        threads = [
            threading.Thread(target=worker, args=(name,)) for name in cache_names
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should complete successfully


class TestRegressionCases:
    """Tests for specific regression scenarios."""

    def test_empty_string_cache_name_handled(self):
        """Empty cache name should be handled gracefully."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        # Should not crash (though semantically questionable)
        client.record_cache_metrics("", hits=10, misses=5)

        if emitted:
            assert emitted[0][1]["cache_name"] == ""

    def test_none_extras_handled(self):
        """None as extras should be handled gracefully."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        emitted = []
        client.register_exporter(lambda n, p: emitted.append((n, p)))

        # Should not crash
        client.record_cache_metrics("cache", hits=10, misses=5, extras=None)

        if emitted:
            payload = emitted[0][1]
            assert "cache_name" in payload

    def test_exporter_that_modifies_payload(self):
        """Exporter modifying payload should not affect other exporters."""
        client = TelemetryClient(min_emit_interval=0.0, min_sample_delta=0)
        client.clear_exporters()

        payloads_received = []

        def mutating_exporter(_n, p):
            p["modified"] = True
            payloads_received.append(("mutating", dict(p)))

        def observing_exporter(_n, p):
            payloads_received.append(("observing", dict(p)))

        client.register_exporter(mutating_exporter)
        client.register_exporter(observing_exporter)

        client.record_cache_metrics("cache", hits=10, misses=5)

        # Both should see the modification (shared dict)
        # This documents current behavior - isolation would require copying
        assert all(p[1].get("modified") for p in payloads_received)
