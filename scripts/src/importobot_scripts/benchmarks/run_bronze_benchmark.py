"""Bronze layer ingestion benchmark for CI guardrails."""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.interfaces.data_models import LayerMetadata


@dataclass
class BenchmarkResult:
    """Container for benchmark metrics."""

    warmup_throughput: float
    warmup_elapsed_seconds: float
    benchmark_throughput: float
    benchmark_elapsed_seconds: float
    throughput_ratio: float
    records_ingested: int
    warmup_records: int
    timestamp_utc: str


def _ingest_records(
    layer: BronzeLayer,
    *,
    records: int,
    template: dict[str, Any],
) -> tuple[float, float]:
    """Ingest a number of records and return (throughput, elapsed_seconds)."""
    start = time.perf_counter()
    for idx in range(records):
        payload = template | {
            "record_id": idx,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        metadata = LayerMetadata(
            source_path=Path(f"benchmark_record_{idx}.json"),
            layer_name="bronze",
            ingestion_timestamp=datetime.now(timezone.utc),
        )
        layer.ingest(payload, metadata)
    elapsed = time.perf_counter() - start
    throughput = records / max(elapsed, 1e-9)
    return throughput, elapsed


def run_benchmark(
    *,
    warmup_records: int,
    benchmark_records: int,
    min_ratio: float,
    min_baseline_throughput: float,
) -> BenchmarkResult:
    """Execute warm-up and benchmark runs and validate thresholds."""
    bronze_layer = BronzeLayer()
    template = {
        "testCase": {
            "name": "Benchmark Test Case",
            "description": "Performance benchmark payload",
            "steps": [
                {"stepDescription": "Setup", "expectedResult": "Complete"},
                {"stepDescription": "Execute", "expectedResult": "Success"},
            ],
        }
    }

    warmup_throughput, warmup_elapsed = _ingest_records(
        bronze_layer, records=warmup_records, template=template
    )
    if warmup_throughput < min_baseline_throughput:
        raise SystemExit(
            f"Warm-up throughput {warmup_throughput:.2f} rec/s "
            f"is below minimum baseline {min_baseline_throughput:.2f} rec/s"
        )

    benchmark_throughput, benchmark_elapsed = _ingest_records(
        bronze_layer, records=benchmark_records, template=template
    )
    ratio = benchmark_throughput / warmup_throughput if warmup_throughput else 0.0
    if ratio < min_ratio:
        raise SystemExit(
            f"Benchmark throughput ratio {ratio:.2%} below minimum {min_ratio:.2%} "
            f"(warm-up {warmup_throughput:.2f} rec/s, "
            f"benchmark {benchmark_throughput:.2f} rec/s)"
        )

    return BenchmarkResult(
        warmup_throughput=warmup_throughput,
        warmup_elapsed_seconds=warmup_elapsed,
        benchmark_throughput=benchmark_throughput,
        benchmark_elapsed_seconds=benchmark_elapsed,
        throughput_ratio=ratio,
        records_ingested=benchmark_records,
        warmup_records=warmup_records,
        timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def main() -> None:
    """Execute Bronze layer ingestion benchmark with command line arguments."""
    parser = argparse.ArgumentParser(description="Bronze layer ingestion benchmark.")
    parser.add_argument(
        "--warmup-records", type=int, default=_int_env("BRONZE_BENCHMARK_WARMUP", 100)
    )
    parser.add_argument(
        "--benchmark-records",
        type=int,
        default=_int_env("BRONZE_BENCHMARK_RECORDS", 1000),
    )
    parser.add_argument(
        "--min-ratio",
        type=float,
        default=_float_env("BRONZE_BENCHMARK_MIN_RATIO", 0.8),
        help="Minimum acceptable benchmark throughput ratio relative to warm-up.",
    )
    parser.add_argument(
        "--min-baseline",
        type=float,
        default=_float_env("BRONZE_BENCHMARK_MIN_BASELINE", 100.0),
        help="Minimum acceptable warm-up throughput in records/sec.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            os.getenv(
                "BRONZE_BENCHMARK_OUTPUT", "performance-metrics/bronze_benchmark.json"
            )
        ),
    )
    args = parser.parse_args()

    result = run_benchmark(
        warmup_records=args.warmup_records,
        benchmark_records=args.benchmark_records,
        min_ratio=args.min_ratio,
        min_baseline_throughput=args.min_baseline,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    print(f"Bronze benchmark passed: {args.output}")


if __name__ == "__main__":
    main()
