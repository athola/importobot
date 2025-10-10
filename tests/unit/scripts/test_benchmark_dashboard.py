"""Smoke tests for the benchmark dashboard generator."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.src.importobot_scripts.benchmarks import benchmark_dashboard


def sample_benchmark_payload() -> dict[str, object]:
    return {
        "timestamp": "2025-01-01 12:00:00",
        "single_file_conversion": {
            "simple": {"mean": 0.01, "std_dev": 0.002, "iterations": 5},
            "medium": {"mean": 0.02, "std_dev": 0.005, "iterations": 5},
        },
        "bulk_conversion": {
            "5_files": {
                "file_count": 5,
                "files_per_second": 12.5,
                "avg_time_per_file": 0.08,
                "complexity": "medium",
            }
        },
        "api_methods": {
            "strict_mode": {"mean": 0.03},
            "lenient_mode": {"mean": 0.02},
        },
        "lazy_loading": {
            "performance_improvement_percent": 42.0,
            "cache_effectiveness": "High",
            "first_access_cold": {"mean": 0.08},
            "cached_access": {"mean": 0.02},
        },
    }


def test_benchmark_dashboard_generation(tmp_path: Path) -> None:
    results_path = tmp_path / "run1.json"
    results_path.write_text(json.dumps(sample_benchmark_payload()), encoding="utf-8")
    output_html = tmp_path / "dashboard.html"

    exit_code = benchmark_dashboard.main(
        [
            "--input",
            str(results_path),
            "--output",
            str(output_html),
        ]
    )

    assert exit_code == 0
    content = output_html.read_text(encoding="utf-8")
    assert "Importobot Benchmark Dashboard" in content
    assert "Single File Conversion" in content
    assert "Bulk Conversion" in content
