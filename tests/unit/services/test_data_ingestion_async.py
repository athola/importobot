"""Async wrappers for DataIngestionService."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest

from importobot.services.data_ingestion_service import DataIngestionService


@pytest.mark.asyncio
async def test_ingest_file_async(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test async wrapper for ingest_file."""
    mock_bronze = Mock()
    service = DataIngestionService(bronze_layer=mock_bronze)
    sentinel = object()
    monkeypatch.setattr(service, "ingest_file", lambda path: sentinel)

    result = await service.ingest_file_async("foo.json")

    assert result is sentinel


@pytest.mark.asyncio
async def test_ingest_json_string_async(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test async wrapper for ingest_json_string."""
    mock_bronze = Mock()
    service = DataIngestionService(bronze_layer=mock_bronze)
    sentinel = object()
    monkeypatch.setattr(
        service,
        "ingest_json_string",
        lambda json_string, source_name="string": sentinel,
    )

    result = await service.ingest_json_string_async("{}", "payload")

    assert result is sentinel


@pytest.mark.asyncio
async def test_ingest_batch_async(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test async wrapper for ingest_batch."""
    mock_bronze = Mock()
    service = DataIngestionService(bronze_layer=mock_bronze)

    # Track calls using a mutable container
    call_tracker: dict[str, Any] = {}

    def fake_batch(paths: list[str], max_workers: int = 4) -> list[str]:
        call_tracker["paths"] = paths
        call_tracker["max_workers"] = max_workers
        return ["ok"]

    monkeypatch.setattr(service, "ingest_batch", fake_batch)

    result = await service.ingest_batch_async(["a.json", "b.json"], max_workers=2)

    assert result == ["ok"]  # type: ignore[comparison-overlap]
    assert call_tracker["paths"] == ["a.json", "b.json"]
    assert call_tracker["max_workers"] == 2


@pytest.mark.asyncio
async def test_ingest_data_dict_async(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test async wrapper for ingest_data_dict."""
    mock_bronze = Mock()
    service = DataIngestionService(bronze_layer=mock_bronze)
    sentinel = object()
    monkeypatch.setattr(
        service, "ingest_data_dict", lambda data, source_name="dict": sentinel
    )

    result = await service.ingest_data_dict_async({"value": 1}, "dict")

    assert result is sentinel
