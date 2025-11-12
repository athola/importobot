#!/usr/bin/env python
"""Inspect how complexity-related signals correlate with detection accuracy.

This utility runs the format detector against integration samples and logs
structural complexity, information richness, indicator counts, and Bayesian posterior.
Output can be redirected to a CSV for correlation checks.
"""

# ruff: noqa: E402, I001 - Module level import not at top of file
# due to Robot Framework stubbing
# pylint: disable=C0413
from __future__ import annotations

import csv
import sys
import types
from collections.abc import Iterable
from pathlib import Path
from typing import Any

# The public importobot package requires Robot Framework at import time.
# During analysis runs we only need the conversion code, so we provide a
# lightweight stub to satisfy the dependency check.
sys.modules.setdefault("robot", types.ModuleType("robot"))  # noqa: E402

# Local/third-party imports (before first-party due to Robot Framework stubbing)
from importobot_scripts.test_fixtures import TEST_DATA_SAMPLES  # noqa: E402

# Importobot first-party imports
from importobot.medallion.bronze.format_detector import (
    FormatDetector,  # noqa: E402
)
from importobot.medallion.bronze.test_case_complexity_analyzer import (  # noqa: E402
    TestCaseComplexityAnalyzer,
)
from importobot.medallion.interfaces.enums import SupportedFormat  # noqa: E402

RESULT_FIELDS = [
    "sample",
    "true_format",
    "predicted_format",
    "is_correct",
    "predicted_confidence",
    "true_confidence",
    "complexity_score",
    "information_content",
    "format_specific_indicators",
    "unique_field_patterns",
    "text_length",
    "parameter_count",
    "relationships",
]


def _load_samples() -> dict[str, dict[str, Any]]:
    """Load representative test samples from the integration fixture."""
    return dict(TEST_DATA_SAMPLES)


def _iter_samples(
    samples: dict[str, dict[str, Any]],
) -> Iterable[tuple[str, SupportedFormat, dict[str, Any]]]:
    """Yield each sample with its ground-truth format."""
    format_mapping = {
        "zephyr_complete": SupportedFormat.ZEPHYR,
        "xray_with_jira": SupportedFormat.JIRA_XRAY,
        "testrail_api_response": SupportedFormat.TESTRAIL,
        "testlink_xml_export": SupportedFormat.TESTLINK,
        "generic_unstructured": SupportedFormat.GENERIC,
    }

    for key, true_format in format_mapping.items():
        data = samples.get(key)
        if not data:
            continue
        yield key, true_format, data


def _analyze_sample(
    name: str,
    true_format: SupportedFormat,
    data: dict[str, Any],
    detector: FormatDetector,
    analyzer: TestCaseComplexityAnalyzer,
) -> dict[str, Any]:
    """Collect complexity signals and detection results for a single sample."""
    complexity_summary = analyzer.get_complexity_summary(data)
    posteriors = detector.get_all_format_confidences(data)

    # Determine predicted format from posterior distribution
    predicted_name = max(
        posteriors.keys(), key=lambda k: posteriors.get(k, 0.0), default="UNKNOWN"
    )
    predicted_confidence = posteriors.get(predicted_name, 0.0)
    true_confidence = posteriors.get(true_format.name, 0.0)

    try:
        predicted_format = SupportedFormat[predicted_name]
    except KeyError:
        predicted_format = SupportedFormat.UNKNOWN

    structural_metrics = complexity_summary.get("evidence_metrics", {})
    info_metrics = complexity_summary.get("information_metrics", {})

    return {
        "sample": name,
        "true_format": true_format.name,
        "predicted_format": predicted_format.name,
        "is_correct": predicted_format == true_format,
        "predicted_confidence": round(predicted_confidence, 6),
        "true_confidence": round(true_confidence, 6),
        "complexity_score": round(complexity_summary["complexity_score"], 6),
        "information_content": round(complexity_summary["information_content"], 6),
        "format_specific_indicators": structural_metrics.get("format_indicators", 0),
        "unique_field_patterns": structural_metrics.get("unique_patterns", 0),
        "text_length": info_metrics.get("text_length", 0),
        "parameter_count": info_metrics.get("parameter_count", 0),
        "relationships": info_metrics.get("relationships", 0),
    }


def run_analysis(output_path: Path | None = None) -> list[dict[str, Any]]:
    """Execute the analysis and optionally write results to CSV."""
    samples = _load_samples()
    detector = FormatDetector()
    analyzer = TestCaseComplexityAnalyzer()

    results: list[dict[str, Any]] = []
    for name, true_format, data in _iter_samples(samples):
        results.append(_analyze_sample(name, true_format, data, detector, analyzer))

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=RESULT_FIELDS)
            writer.writeheader()
            writer.writerows(results)

    return results


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    argv = argv or sys.argv[1:]
    output_path = Path(argv[0]).resolve() if argv else None

    results = run_analysis(output_path)

    # Show a quick overview when not writing to disk
    if not output_path:
        print(",".join(RESULT_FIELDS))
        for row in results:
            print(",".join(str(row[field]) for field in RESULT_FIELDS))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
