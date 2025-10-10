"""Tests for the Bronze layer benchmark helper."""

from __future__ import annotations

from typing import Any

import pytest

from scripts.src.importobot_scripts.benchmarks import run_bronze_benchmark as benchmark


def test_run_benchmark_enforces_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    """Benchmark should abort when throughput ratio drops below the threshold."""
    call_order: list[int] = []

    def fake_ingest(
        layer: Any, *, records: int, template: dict[str, Any]
    ) -> tuple[float, float]:
        call_order.append(records)
        if records == 10:
            return 400.0, 0.025
        return 100.0, 0.1  # 25% of baseline -> below 0.8 ratio

    monkeypatch.setattr(benchmark, "_ingest_records", fake_ingest)

    with pytest.raises(SystemExit):
        benchmark.run_benchmark(
            warmup_records=10,
            benchmark_records=50,
            min_ratio=0.8,
            min_baseline_throughput=50.0,
        )

    assert call_order == [10, 50]


def test_run_benchmark_enforces_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Benchmark should fail fast when baseline throughput is too low."""

    def fake_ingest(
        layer: Any, *, records: int, template: dict[str, Any]
    ) -> tuple[float, float]:
        return 20.0, 1.0

    monkeypatch.setattr(benchmark, "_ingest_records", fake_ingest)

    with pytest.raises(SystemExit):
        benchmark.run_benchmark(
            warmup_records=5,
            benchmark_records=20,
            min_ratio=0.8,
            min_baseline_throughput=100.0,
        )


def test_run_benchmark_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful benchmark returns structured metrics."""
    responses = iter(
        [
            (200.0, 0.05),  # warm-up
            (190.0, 0.052),  # benchmark (95% of baseline)
        ]
    )

    monkeypatch.setattr(
        benchmark,
        "_ingest_records",
        lambda layer, *, records, template: next(responses),
    )

    result = benchmark.run_benchmark(
        warmup_records=10,
        benchmark_records=60,
        min_ratio=0.8,
        min_baseline_throughput=100.0,
    )

    assert result.warmup_throughput == pytest.approx(200.0)
    assert result.benchmark_throughput == pytest.approx(190.0)
    assert result.throughput_ratio == pytest.approx(0.95)
    assert result.records_ingested == 60
