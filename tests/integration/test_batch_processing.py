"""Integration tests for batch ingestion workflows."""

from __future__ import annotations

import time
from pathlib import Path
from typing import cast

import pytest

from importobot.medallion.bronze_layer import BronzeLayer
from importobot.services.data_ingestion_service import DataIngestionService


class _DummyBronzeLayer:
    """Minimal Bronze layer stub returning successful results."""

    def ingest(self, _data, metadata):  # pragma: no cover - behavior mocked in tests
        """Return the provided metadata to satisfy the service contract."""
        return metadata  # DataIngestionService ignores the concrete result in our test


def test_batch_ingestion_parallelism(monkeypatch: pytest.MonkeyPatch) -> None:
    """Batch ingestion should leverage parallel execution for performance."""
    bronze_layer = cast(BronzeLayer, _DummyBronzeLayer())
    service = DataIngestionService(bronze_layer=bronze_layer)

    files: list[str | Path] = [Path(f"test_{i}.json") for i in range(12)]

    def slow_ingest(file_path):
        time.sleep(0.02)
        return file_path

    monkeypatch.setattr(service, "ingest_file", slow_ingest, raising=False)

    start = time.perf_counter()
    sequential_results = [service.ingest_file(path) for path in files]
    sequential_time = time.perf_counter() - start

    start = time.perf_counter()
    parallel_results = service.ingest_batch(files, max_workers=4)
    parallel_time = time.perf_counter() - start

    assert sequential_results == parallel_results
    assert parallel_time < sequential_time
    speedup = sequential_time / max(parallel_time, 1e-9)
    assert speedup > 2.0
