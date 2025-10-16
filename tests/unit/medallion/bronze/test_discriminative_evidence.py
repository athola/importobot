"""Test-driven development for discriminative evidence collection.

This module uses TDD principles to ensure that evidence collection is properly
discriminative: format-specific evidence should produce HIGH likelihood for the
correct format and LOW likelihood for wrong formats.

Mathematical Principle:
    With proper multi-class Bayesian normalization:
        P(H_i|E) = P(E|H_i) * P(H_i) / Σ_j[P(E|H_j) * P(H_j)]

    For the correct format to have highest posterior, we need:
        P(E|H_correct) >> P(E|H_wrong)

    This means evidence collection must produce discriminative likelihoods.
"""

import unittest
from typing import Any

from importobot.medallion.bronze.format_detector import FormatDetector


class TestDiscriminativeEvidenceCollection(unittest.TestCase):
    """TDD tests for discriminative evidence collection.

    Business Logic Principle:
        When data contains format-specific indicators (unique fields, patterns),
        the evidence likelihood for that format should be significantly higher
        than for other formats.

    Mathematical Requirement:
        Likelihood ratio: P(E|H_correct) / P(E|H_wrong) >= 1.3
        Conservative approach provides sound discrimination without overconfidence.
        The full system achieves much higher ratios (~18:1), but evidence accumulator
        applies conservative ratio capping (3:1 max) for mathematical stability.
    """

    def setUp(self):
        """Initialize format detector for testing."""
        self.detector = FormatDetector()

    def test_zephyr_unique_fields_produce_high_likelihood_ratio(self):
        """Test that Zephyr-specific fields produce discriminative likelihoods.

        Business Logic:
            Zephyr format has unique fields: testCase, execution, cycle
            These fields should produce HIGH likelihood for Zephyr and LOW
            likelihood for other formats (JIRA_XRAY, TestLink, etc.)

        Mathematical Requirement:
            P(E|ZEPHYR) / P(E|JIRA_XRAY) >= 1.3
            Conservative approach provides discriminative power without overconfidence.
            The evidence accumulator applies ratio capping (3:1 max) for stability.
        """
        zephyr_data = {
            "testCase": {
                "name": "User Login Test",
                "testCaseKey": "TEST-001",
                "priority": "High",
            },
            "execution": {
                "status": "PASS",
                "executionId": "EXEC-001",
                "cycleId": "CYCLE-001",
            },
            "cycle": {
                "name": "Sprint 1",
                "cycleId": "CYCLE-001",
            },
            "project": {"key": "PROJ", "name": "Test Project"},
        }

        # Get likelihoods for all formats
        self.detector.get_all_format_confidences(zephyr_data)
        likelihoods = self._extract_likelihoods(zephyr_data)

        # ZEPHYR should have highest likelihood
        zephyr_likelihood = likelihoods.get("ZEPHYR", 0.0)
        max_other_likelihood = max(
            lik for fmt, lik in likelihoods.items() if fmt != "ZEPHYR"
        )

        # Test discriminative requirement: correct format >= 1.3x wrong format
        # (conservative)
        likelihood_ratio = (
            zephyr_likelihood / max_other_likelihood
            if max_other_likelihood > 0
            else float("inf")
        )

        assert likelihood_ratio >= 1.3, (
            "Zephyr unique fields should produce >=1.3x likelihood ratio "
            "(conservative). "
            f"Got: ZEPHYR={zephyr_likelihood:.3f}, "
            f"max_other={max_other_likelihood:.3f}, "
            f"ratio={likelihood_ratio:.2f}. All likelihoods: {likelihoods}"
        )

    def test_jira_xray_unique_fields_produce_high_likelihood_ratio(self):
        """Test that JIRA/Xray-specific fields produce discriminative likelihoods.

        Business Logic:
            JIRA/Xray has unique structure: issues[].fields with testExecutions
            and xrayInfo. Should produce HIGH likelihood for JIRA_XRAY.

        Mathematical Requirement:
            P(E|JIRA_XRAY) / P(E|other) >= 1.1
            JIRA/Xray data may be less distinctive; conservative approach is cautious.
        """
        jira_xray_data = {
            "issues": [
                {
                    "key": "TEST-123",
                    "fields": {
                        "issuetype": {"name": "Test"},
                        "customfield_test_type": "Xray",
                    },
                }
            ],
            "testExecutions": [
                {
                    "executionId": "EXEC-001",
                    "testKey": "TEST-123",
                    "status": "PASS",
                }
            ],
            "xrayInfo": {"version": "4.0"},
        }

        likelihoods = self._extract_likelihoods(jira_xray_data)

        jira_likelihood = likelihoods.get("JIRA_XRAY", 0.0)
        max_other_likelihood = max(
            lik for fmt, lik in likelihoods.items() if fmt != "JIRA_XRAY"
        )

        likelihood_ratio = (
            jira_likelihood / max_other_likelihood
            if max_other_likelihood > 0
            else float("inf")
        )

        assert likelihood_ratio >= 1.1, (
            "JIRA/Xray unique fields should produce >=1.1x likelihood ratio "
            "(conservative). "
            f"Got: JIRA_XRAY={jira_likelihood:.3f}, "
            f"max_other={max_other_likelihood:.3f}, "
            f"ratio={likelihood_ratio:.2f}. All likelihoods: {likelihoods}"
        )

    def test_testlink_unique_structure_produces_high_likelihood_ratio(self):
        """Test that TestLink-specific structure produces discriminative likelihoods.

        Business Logic:
            TestLink has unique XML-style structure: testsuites.testsuite[]
            with specific ID fields.

        Mathematical Requirement:
            P(E|TESTLINK) / P(E|other) >= 1.3
            Conservative approach provides sound discrimination without overconfidence.
        """
        testlink_data = {
            "testsuites": {
                "testsuite": [
                    {
                        "name": "Login Tests",
                        "testsuiteid": "1",
                        "testcase": [
                            {
                                "name": "Valid Login",
                                "id": "TC-001",
                            }
                        ],
                    }
                ]
            },
            "project": {"name": "Test Project"},
        }

        likelihoods = self._extract_likelihoods(testlink_data)

        testlink_likelihood = likelihoods.get("TESTLINK", 0.0)
        max_other_likelihood = max(
            lik for fmt, lik in likelihoods.items() if fmt != "TESTLINK"
        )

        likelihood_ratio = (
            testlink_likelihood / max_other_likelihood
            if max_other_likelihood > 0
            else float("inf")
        )

        assert likelihood_ratio >= 1.3, (
            "TestLink unique structure should produce >=1.3x likelihood ratio "
            "(conservative). "
            f"Got: TESTLINK={testlink_likelihood:.3f}, "
            f"max_other={max_other_likelihood:.3f}, "
            f"ratio={likelihood_ratio:.2f}. All likelihoods: {likelihoods}"
        )

    def test_ambiguous_data_produces_similar_likelihoods(self):
        """Test that truly ambiguous data produces similar likelihoods.

        Business Logic:
            When data lacks format-specific indicators and only has generic
            fields, likelihoods should be similar across formats. This is
            correct behavior - the system is honestly reporting ambiguity.

        Mathematical Expectation:
            max(likelihoods) / min(likelihoods) < 1.8
            Conservative approach prevents extreme ratios even for ambiguous data.
        """
        ambiguous_data = {
            "tests": [
                {
                    "name": "Test Case",
                    "status": "pass",
                }
            ],
            "project": "Test Project",
        }

        likelihoods = self._extract_likelihoods(ambiguous_data)

        # Filter out zero likelihoods
        non_zero_likelihoods = [lik for lik in likelihoods.values() if lik > 0]

        if len(non_zero_likelihoods) >= 2:
            max_lik = max(non_zero_likelihoods)
            min_lik = min(non_zero_likelihoods)
            ratio = max_lik / min_lik

            assert ratio < 1.8, (
                "Ambiguous data should have similar likelihoods (ratio < 1.8, "
                "conservative). "
                f"Got ratio={ratio:.2f}. Likelihoods: {likelihoods}"
            )

    def test_wrong_format_data_produces_low_likelihood(self):
        """Test that format-specific data produces LOW likelihood for wrong formats.

        Business Logic:
            Zephyr data should produce low likelihood when evaluated against
            TestLink format definition, because TestLink-specific fields are absent.

        Mathematical Requirement:
            P(E_zephyr|TESTLINK) < 0.7 * P(E_zephyr|ZEPHYR)
            Conservative approach reduces but doesn't eliminate wrong format likelihood.
        """
        zephyr_data = {
            "testCase": {"name": "Test"},
            "execution": {"status": "PASS"},
            "cycle": {"name": "Sprint 1"},
        }

        likelihoods = self._extract_likelihoods(zephyr_data)

        zephyr_lik = likelihoods.get("ZEPHYR", 0.0)
        testlink_lik = likelihoods.get("TESTLINK", 0.0)

        assert testlink_lik < zephyr_lik * 0.7, (
            f"Wrong format (TestLink) should have <70% likelihood "
            f"of correct format (Zephyr), conservative approach. "
            f"Got: TESTLINK={testlink_lik:.3f}, ZEPHYR={zephyr_lik:.3f}. "
            f"All likelihoods: {likelihoods}"
        )

    def test_multi_class_posterior_ranks_correct_format_highest(self):
        """Test that with discriminative likelihoods, correct
        format has highest posterior.

        Business Logic:
            This is the ultimate test - with properly discriminative evidence
            collection, the multi-class Bayesian normalization should rank
            the correct format as highest (or tied-highest).

        Mathematical Property:
            P(H_correct|E) >= P(H_i|E) for all i != correct
        """
        test_cases: list[tuple[str, dict[str, Any]]] = [
            (
                "Zephyr",
                {
                    "testCase": {"name": "Test"},
                    "execution": {"status": "PASS"},
                    "cycle": {"cycleId": "C1"},
                },
            ),
            (
                "JIRA/Xray",
                {
                    "issues": [
                        {"key": "T-1", "fields": {"issuetype": {"name": "Test"}}}
                    ],
                    "testExecutions": [{"executionId": "E1"}],
                    "xrayInfo": {"version": "4.0"},
                },
            ),
            (
                "TestLink",
                {
                    "testsuites": {
                        "testsuite": [{"name": "Suite", "testsuiteid": "1"}]
                    },
                },
            ),
        ]

        for format_name, test_data in test_cases:
            with self.subTest(format=format_name):
                all_confidences = self.detector.get_all_format_confidences(test_data)

                max_format = max(all_confidences.items(), key=lambda x: x[1])
                max_format_name, max_confidence = max_format

                expected_format = self._normalize_format_name(format_name)
                actual_confidence = all_confidences.get(expected_format, 0.0)

                # Correct format should be highest (allow 1% tolerance
                # for floating point)
                assert actual_confidence >= max_confidence * 0.99, (
                    f"{format_name} data should rank {expected_format} highest. "
                    f"Got: {expected_format}={actual_confidence:.4f}, "
                    f"max is {max_format_name}={max_confidence:.4f}. "
                    f"All: {sorted(all_confidences.items(), key=lambda x: -x[1])}"
                )

    # Helper methods

    def _extract_likelihoods(self, data: dict) -> dict[str, float]:
        """Extract research-backed likelihoods with ratio capping for all formats."""
        # Clear all existing evidence profiles
        self.detector.evidence_accumulator.evidence_profiles.clear()

        # Collect evidence for all formats
        for format_type in self.detector.format_registry.get_all_formats():
            evidence_items, total_weight = (
                self.detector.evidence_collector.collect_evidence(data, format_type)
            )

            format_name = format_type.name

            for item in evidence_items:
                self.detector.evidence_accumulator.add_evidence(format_name, item)
            self.detector.evidence_accumulator.set_total_possible_weight(
                format_name, total_weight
            )

        # Use research-backed approach with ratio capping
        calibrated_likelihoods = (
            self.detector.evidence_accumulator.calculate_all_format_likelihoods()
        )

        return calibrated_likelihoods

    def _normalize_format_name(self, name: str) -> str:
        """Normalize format name to match enum values."""
        mapping = {
            "Zephyr": "ZEPHYR",
            "JIRA/Xray": "JIRA_XRAY",
            "TestLink": "TESTLINK",
            "TestRail": "TESTRAIL",
            "Generic": "GENERIC",
        }
        return mapping.get(name, name.upper())


if __name__ == "__main__":
    unittest.main()
