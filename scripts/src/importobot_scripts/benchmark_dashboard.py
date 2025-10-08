#!/usr/bin/env python3
"""Generate a lightweight HTML dashboard from benchmark JSON results."""

from __future__ import annotations

import argparse
import html
import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _human_ms(value: float | None) -> str:
    if value is None:
        return "–"
    return f"{value * 1000:.2f} ms"


def _render_table(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> str:
    header_html = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    body = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(c))}</td>" for c in row)
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _render_single_file_section(data: dict[str, Any]) -> str:
    if not data:
        return ""
    rows = []
    for complexity, stats in data.items():
        mean = stats.get("mean")
        p95 = stats.get("percentile_95")
        std_dev = stats.get("std_dev")
        rows.append(
            [
                complexity.title(),
                _human_ms(mean),
                _human_ms(p95),
                _human_ms(std_dev),
                f"{stats.get('iterations', '-')}",
            ]
        )
    table = _render_table(
        ["Complexity", "Average", "95th percentile", "Std Dev", "Iterations"], rows
    )
    return f"<h2>Single File Conversion</h2>{table}"


def _render_bulk_section(data: dict[str, Any]) -> str:
    if not data:
        return ""
    rows = []
    for label, stats in data.items():
        rows.append(
            [
                label,
                f"{stats.get('file_count', '-')}",
                f"{stats.get('files_per_second', 0):.2f}",
                _human_ms(stats.get("avg_time_per_file")),
                stats.get("complexity", "-"),
            ]
        )
    table = _render_table(
        ["Scenario", "Files", "Files/sec", "Avg per file", "Complexity"], rows
    )
    return f"<h2>Bulk Conversion</h2>{table}"


def _render_api_section(data: dict[str, Any]) -> str:
    if not data:
        return ""
    rows = []
    for mode, stats in data.items():
        rows.append(
            [
                mode.replace("_", " ").title(),
                _human_ms(stats.get("mean")),
                _human_ms(stats.get("percentile_95")),
            ]
        )
    table = _render_table(["Mode", "Average", "95th percentile"], rows)
    return f"<h2>API Method Comparison</h2>{table}"


def _render_lazy_loading_section(data: dict[str, Any]) -> str:
    if not data:
        return ""
    improvement = data.get("performance_improvement_percent")
    summary = (
        f"<p><strong>Cache effectiveness:</strong> {html.escape(data.get('cache_effectiveness', 'Unknown'))}"
        f" — <em>{improvement:.2f}% speedup after warm cache</em></p>"
        if improvement is not None
        else ""
    )
    rows = []
    for label in ["first_access_cold", "cached_access", "multi_property_access"]:
        stats = data.get(label)
        if not stats:
            continue
        rows.append([label.replace("_", " ").title(), _human_ms(stats.get("mean"))])
    table = _render_table(["Scenario", "Average"], rows)
    return f"<h2>Lazy Loading</h2>{summary}{table}"


def render_dashboard(run_results: list[tuple[Path, dict[str, Any]]]) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    sections = [
        "<h1>Importobot Benchmark Dashboard</h1>",
        f"<p class=meta>Generated {html.escape(generated_at)} (UTC)</p>",
    ]

    if not run_results:
        sections.append("<p>No benchmark results found.</p>")
    else:
        for path, data in run_results:
            sections.append(
                f"<section class=run><h2>Run: {html.escape(str(path))}</h2>"
                f"<p><strong>Timestamp:</strong> {html.escape(data.get('timestamp', 'unknown'))}</p>"
            )
            sections.append(
                _render_single_file_section(data.get("single_file_conversion", {}))
            )
            sections.append(_render_bulk_section(data.get("bulk_conversion", {})))
            sections.append(_render_api_section(data.get("api_methods", {})))
            if "parallel_conversion" in data:
                pc = data["parallel_conversion"]
                sections.append(
                    "<h2>Parallel Conversion</h2>"
                    + _render_table(
                        ["Files", "Workers", "Total time", "Files/sec"],
                        [
                            [
                                pc.get("file_count", "-"),
                                pc.get("max_workers", "-"),
                                _human_ms(pc.get("total_time")),
                                f"{pc.get('files_per_second', 0):.2f}",
                            ]
                        ],
                    )
                )
            sections.append(_render_lazy_loading_section(data.get("lazy_loading", {})))
            raw_json = html.escape(json.dumps(data, indent=2))
            sections.append(
                f"<details><summary>Raw JSON</summary><pre>{raw_json}</pre></details></section>"
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Importobot Benchmark Dashboard</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 2rem; background-color: #f8f9fa; color: #212529; }}
h1 {{ margin-top: 0; }}
h2 {{ margin-top: 1.8rem; }}
table {{ border-collapse: collapse; margin-top: 0.8rem; width: 100%; max-width: 960px; background: white; }}
th, td {{ border: 1px solid #dee2e6; padding: 0.5rem 0.75rem; text-align: left; }}
th {{ background-color: #343a40; color: #fff; }}
tr:nth-child(even) td {{ background-color: #f1f3f5; }}
section.run {{ margin-bottom: 3rem; padding: 1.5rem; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-radius: 8px; }}
p.meta {{ color: #6c757d; }}
details pre {{ background: #212529; color: #f8f9fa; padding: 1rem; overflow-x: auto; }}
</style>
</head>
<body>
{"".join(sections)}
</body>
</html>"""


def load_results(paths: list[Path]) -> list[tuple[Path, dict[str, Any]]]:
    run_results: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
            run_results.append((path, data))
        except (OSError, json.JSONDecodeError):
            continue
    return run_results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate benchmark dashboard")
    parser.add_argument(
        "--input",
        nargs="+",
        type=Path,
        default=[Path("performance_benchmark_results.json")],
        help="Benchmark JSON files to include",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("performance_benchmark_dashboard.html"),
        help="Output HTML file path",
    )
    args = parser.parse_args(argv)

    run_results = load_results(args.input)
    html_output = render_dashboard(run_results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_output, encoding="utf-8")
    print(f"📊 Benchmark dashboard written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
