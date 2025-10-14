"""Regression tests for Bayesian ratio behaviour and ambiguous evidence handling."""

from __future__ import annotations

from importobot.medallion.bronze.format_detector import FormatDetector
from importobot.medallion.interfaces.enums import SupportedFormat


def _collect_likelihoods(detector: FormatDetector, data: dict) -> dict[str, float]:
    """Helper that mirrors the accumulator pipeline for deterministic likelihoods."""
    accumulator = detector.evidence_accumulator
    accumulator.evidence_profiles.clear()

    for format_type in detector.format_registry.get_all_formats():
        evidence_items, total_weight = detector.evidence_collector.collect_evidence(
            data, format_type
        )
        fmt_name = format_type.name
        for item in evidence_items:
            accumulator.add_evidence(fmt_name, item)
        accumulator.set_total_possible_weight(fmt_name, total_weight)

    return accumulator.calculate_all_format_likelihoods()


def test_ambiguous_input_remains_low_ratio() -> None:
    """Ambiguous data should not strongly favour any specific format."""
    detector = FormatDetector()
    ambiguous_data = {
        "tests": [{"name": "Test Case", "status": "pass"}],
        "project": "Test Project",
    }

    likelihoods = _collect_likelihoods(detector, ambiguous_data)
    positive = sorted((lik for lik in likelihoods.values() if lik > 0), reverse=True)

    assert positive, "Expected at least one positive likelihood for ambiguous data"
    assert positive[0] / positive[-1] <= 1.5, (
        "Ambiguous evidence should be capped at 1.5:1 ratio to avoid overconfidence"
    )

    detected = detector.detect_format(ambiguous_data)
    assert detected in {SupportedFormat.GENERIC, SupportedFormat.UNKNOWN}


def test_confident_formats_show_clear_separation() -> None:
    """Representative format samples must dominate alternative likelihoods."""
    detector = FormatDetector()
    samples: list[tuple[str, dict, float]] = [
        (
            "ZEPHYR",
            {
                "testCase": {"name": "User Login Test", "testCaseKey": "TEST-001"},
                "execution": {"status": "PASS", "executionId": "EXEC-001"},
                "cycle": {"name": "Sprint 1", "cycleId": "CYCLE-001"},
            },
            1.3,
        ),
        (
            "JIRA_XRAY",
            {
                "issues": [
                    {"key": "TEST-123", "fields": {"issuetype": {"name": "Test"}}}
                ],
                "testExecutions": [{"executionId": "EXEC-001", "testKey": "TEST-123"}],
                "xrayInfo": {"version": "4.0"},
            },
            1.3,
        ),
        (
            "TESTLINK",
            {
                "testsuites": {
                    "testsuite": [
                        {
                            "name": "Login Tests",
                            "testsuiteid": "1",
                            "testcase": [{"name": "Valid Login", "id": "TC-001"}],
                        }
                    ]
                }
            },
            1.3,
        ),
    ]

    for fmt_name, data, min_ratio in samples:
        likelihoods = _collect_likelihoods(detector, data)
        correct = likelihoods.get(fmt_name, 0.0)
        others = [
            lik for key, lik in likelihoods.items() if key != fmt_name and lik > 0
        ]

        assert correct > 0.0, f"Expected positive likelihood for {fmt_name}"
        assert others, f"Expected comparative likelihoods for {fmt_name}"

        ratio = correct / max(others)
        assert ratio >= min_ratio, (
            f"{fmt_name} likelihood ratio dropped below the conservative bound "
            f"{ratio:.2f} < {min_ratio}"
        )

        # Multi-class posterior should agree with the expected format.
        detected = detector.detect_format(data)
        assert detected.name == fmt_name


def test_wrong_format_likelihood_penalty() -> None:
    """Wrong formats must receive substantially lower likelihood than the true one."""
    detector = FormatDetector()
    zephyr_sample = {
        "testCase": {"name": "Test"},
        "execution": {"status": "PASS"},
        "cycle": {"name": "Sprint 1"},
    }

    likelihoods = _collect_likelihoods(detector, zephyr_sample)
    correct = likelihoods.get("ZEPHYR", 0.0)
    assert correct > 0.0, "Expected Zephyr likelihood to be positive for Zephyr sample"

    for fmt, lik in likelihoods.items():
        if fmt == "ZEPHYR":
            continue
        assert lik <= correct * 0.7, (
            f"{fmt} likelihood {lik:.3f} exceeds 70% of Zephyr's {correct:.3f}"
        )
