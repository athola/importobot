"""Tests for the _resolve_positive_config helper in bronze_layer.py."""

import logging

import pytest

from importobot.medallion.bronze_layer import (
    _resolve_positive_config,  # type: ignore[attr-defined]
)


class TestResolvePositiveConfig:
    """Unit tests for the _resolve_positive_config module-level helper."""

    def test_none_value_falls_back_to_default(self) -> None:
        """When value is None the default must be returned unchanged."""
        result = _resolve_positive_config(None, 100, "param")

        assert result == 100

    def test_valid_positive_value_is_returned_as_is(self) -> None:
        """A positive integer value must be returned without modification."""
        result = _resolve_positive_config(42, 100, "param")

        assert result == 42

    def test_value_of_exactly_one_is_accepted(self) -> None:
        """Exactly 1 is the minimum valid positive integer; kept as-is."""
        result = _resolve_positive_config(1, 100, "param")

        assert result == 1

    def test_value_less_than_one_returns_default(self) -> None:
        """A value below 1 is invalid; the default must be returned."""
        result = _resolve_positive_config(0, 100, "param")

        assert result == 100

    def test_negative_value_returns_default(self) -> None:
        """A negative value is invalid; the default must be returned."""
        result = _resolve_positive_config(-5, 50, "param")

        assert result == 50

    def test_value_less_than_one_triggers_warning_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A value below 1 must emit a WARNING-level log message."""
        with caplog.at_level(logging.WARNING):
            _resolve_positive_config(0, 100, "max_records")

        assert len(caplog.records) >= 1
        warning_messages = [
            r.message for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert any("max_records" in msg for msg in warning_messages)

    def test_warning_log_includes_invalid_value_and_default(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Warning log mentions the invalid value and the fallback."""
        with caplog.at_level(logging.WARNING):
            _resolve_positive_config(-3, 200, "ttl_seconds")

        warning_text = " ".join(
            r.message for r in caplog.records if r.levelno == logging.WARNING
        )
        assert "-3" in warning_text
        assert "200" in warning_text

    def test_valid_value_does_not_trigger_warning_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """No warning emitted when a valid positive value is supplied."""
        with caplog.at_level(logging.WARNING):
            _resolve_positive_config(10, 100, "param")

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warning_records == []

    def test_none_value_does_not_trigger_warning_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Falling back from None to default is silent (no warning)."""
        with caplog.at_level(logging.WARNING):
            _resolve_positive_config(None, 100, "param")

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warning_records == []
