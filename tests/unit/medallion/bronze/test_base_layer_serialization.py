"""Tests for serialization helpers on BaseMedallionLayer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from importobot.medallion.base_layers import BaseMedallionLayer


class _DummyLayer(BaseMedallionLayer):
    """Minimal concrete implementation for serialization tests."""

    def __init__(self) -> None:
        super().__init__("dummy")

    # Minimal implementations to satisfy abstract interface; not exercised in tests
    def ingest(self, data, metadata):  # type: ignore[override]
        raise NotImplementedError

    def ingest_with_detection(self, data, source_info):  # type: ignore[override]
        raise NotImplementedError

    def validate(self, data):  # type: ignore[override]
        raise NotImplementedError

    def get_record_metadata(self, record_id):  # type: ignore[override]
        raise NotImplementedError

    def get_record_lineage(self, record_id):  # type: ignore[override]
        raise NotImplementedError

    def validate_bronze_data(self, data):  # type: ignore[override]
        raise NotImplementedError

    def get_bronze_records(  # type: ignore[override]
        self, filter_criteria=None, limit=None
    ):
        raise NotImplementedError


def test_serialize_datetime_uses_isoformat(caplog: pytest.LogCaptureFixture) -> None:
    """Serialization should convert datetime objects into ISO 8601 strings."""
    layer = _DummyLayer()
    payload = {"ts": datetime(2025, 1, 1, 12, 0)}

    serialized = layer._serialize_data(payload)  # pylint: disable=protected-access

    assert '"ts": "2025-01-01T12:00:00"' in serialized
    assert "Falling back" not in caplog.text


def test_serialize_path_is_string(caplog: pytest.LogCaptureFixture) -> None:
    """Serialization should convert Path objects into string paths."""
    layer = _DummyLayer()
    payload = {"path": Path("/tmp/example.txt")}

    serialized = layer._serialize_data(payload)  # pylint: disable=protected-access

    assert '"path": "/tmp/example.txt"' in serialized
    assert "Falling back" not in caplog.text


def test_non_serializable_type_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Non-serializable objects should fall back to string conversion with warning."""

    class Custom:
        """Dummy object providing a string representation for serialization."""

        def __str__(self) -> str:
            return "custom-repr"

    layer = _DummyLayer()
    payload = {"value": Custom()}

    with caplog.at_level("WARNING"):
        serialized = layer._serialize_data(payload)  # pylint: disable=protected-access

    assert '"value": "custom-repr"' in serialized
    assert "Falling back to string serialization" in caplog.text
