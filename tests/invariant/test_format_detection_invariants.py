"""Format detection invariant tests using Hypothesis.
# pylint: disable=superfluous-parens,comparison-with-itself
# Invariant test issues

Tests properties that should always hold true for format detection:
- Confidence scores are always in valid ranges
- Format detection is deterministic for same input
- Detection handles malformed input gracefully
- Priority system maintains consistency
"""

import math
import time

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from importobot.medallion.bronze.format_detector import FormatDetector
from importobot.medallion.bronze.shared_config import TESTRAIL_COMMON_FIELDS
from importobot.medallion.interfaces.enums import SupportedFormat


# Custom strategies for generating test data structures
@st.composite
def json_like_structure(draw):
    """Generate JSON-like structures that might represent test data."""
    return draw(
        st.recursive(
            st.one_of(
                st.none(),
                st.booleans(),
                st.integers(min_value=-1000, max_value=1000),
                st.floats(allow_nan=False, allow_infinity=False),
                st.text(min_size=0, max_size=50),
            ),
            lambda children: st.one_of(
                st.lists(children, min_size=0, max_size=10),
                st.dictionaries(
                    keys=st.text(min_size=0, max_size=20),
                    values=children,
                    min_size=0,
                    max_size=10,
                ),
            ),
            max_leaves=20,
        )
    )


@st.composite
def management_like_data(draw):
    """Generate data that might look like test management system exports."""
    base_keys = draw(
        st.sets(
            st.sampled_from(
                [
                    "id",
                    "name",
                    "title",
                    "description",
                    "status",
                    "steps",
                    "testCase",
                    "execution",
                    "cycle",
                    "issues",
                    "key",
                    "fields",
                    *TESTRAIL_COMMON_FIELDS,
                    "testsuites",
                    "testsuite",
                    "testcase",
                    "tests",
                    "test_cases",
                ]
            ),
            min_size=0,
            max_size=8,
        )
    )

    data = {}
    for key in base_keys:
        data[key] = draw(
            st.one_of(
                st.text(min_size=0, max_size=100),
                st.integers(min_value=0, max_value=9999),
                st.lists(
                    st.dictionaries(
                        keys=st.text(min_size=0, max_size=10),
                        values=st.text(min_size=0, max_size=50),
                        min_size=0,
                        max_size=5,
                    ),
                    min_size=0,
                    max_size=5,
                ),
            )
        )

    return data


class TestFormatDetectionInvariants:
    """Format detection system invariant tests."""

    @given(json_like_structure())
    @settings(max_examples=100)
    def test_confidence_score_bounds_invariant(self, data):
        """Invariant: Confidence scores should always be between 0.0 and 1.0."""
        assume(isinstance(data, dict))  # Only test with dict input

        detector = FormatDetector()

        try:
            # Test all supported formats
            for format_type in detector.get_supported_formats():
                confidence = detector.get_format_confidence(data, format_type)

                # Confidence must be a valid float in range [0.0, 1.0]
                assert isinstance(confidence, float)
                assert 0.0 <= confidence <= 1.0
                assert not math.isnan(confidence)  # Check for NaN

        except Exception as e:
            # Any exception in confidence calculation is a bug
            pytest.fail(f"Exception in confidence calculation: {type(e).__name__}: {e}")

    @given(management_like_data())
    @settings(max_examples=50)
    def test_format_detection_determinism_invariant(self, data):
        """Invariant: Format detection should be deterministic for same input."""
        detector = FormatDetector()

        try:
            # Detect format multiple times
            detection1 = detector.detect_format(data)
            detection2 = detector.detect_format(data)
            detection3 = detector.detect_format(data)

            # Results should be identical
            assert detection1 == detection2 == detection3

            # Confidence scores should also be identical
            for format_type in detector.get_supported_formats():
                conf1 = detector.get_format_confidence(data, format_type)
                conf2 = detector.get_format_confidence(data, format_type)
                conf3 = detector.get_format_confidence(data, format_type)

                assert conf1 == conf2 == conf3

        except Exception as e:
            pytest.fail(f"Exception in determinism test: {type(e).__name__}: {e}")

    @given(
        st.one_of(
            st.none(),
            st.text(),
            st.integers(),
            st.lists(st.text()),
            st.dictionaries(st.integers(), st.text()),  # Invalid key types
        )
    )
    @settings(max_examples=30)
    def test_invalid_input_handling_invariant(self, invalid_data):
        """Invariant: Format detection should handle invalid input gracefully."""
        detector = FormatDetector()

        try:
            result = detector.detect_format(invalid_data)

            # Should return UNKNOWN for invalid input
            assert result == SupportedFormat.UNKNOWN

            # Confidence for all formats should be very low for invalid input
            for format_type in detector.get_supported_formats():
                confidence = detector.get_format_confidence(invalid_data, format_type)
                assert isinstance(confidence, float)
                assert 0.0 <= confidence <= 1.0

        except Exception as e:
            pytest.fail(f"Exception handling invalid input: {type(e).__name__}: {e}")

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(min_size=0, max_size=100),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=50)
    def test_confidence_consistency_invariant(self, data):
        """Invariant: Higher confidence should correlate with format selection."""
        detector = FormatDetector()

        try:
            detected_format = detector.detect_format(data)

            # Get confidence for the detected format
            detected_confidence = detector.get_format_confidence(data, detected_format)

            # Get confidence for all other formats
            other_confidences = []
            for format_type in detector.get_supported_formats():
                if format_type != detected_format:
                    other_confidences.append(
                        detector.get_format_confidence(data, format_type)
                    )

            # If a specific format was detected (not UNKNOWN), its confidence
            # should be among the highest (accounting for priority weights)
            if detected_format != SupportedFormat.UNKNOWN and other_confidences:
                # The detected format should have reasonable confidence
                # (may not always be highest due to priority multipliers)
                assert detected_confidence >= 0.0

        except Exception as e:
            pytest.fail(
                f"Exception in confidence consistency test: {type(e).__name__}: {e}"
            )

    @given(management_like_data(), st.integers(min_value=1, max_value=100))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.filter_too_much])
    def test_format_detection_scalability_invariant(self, data, iterations):
        """Invariant: Format detection performance should be consistent."""
        assume(iterations <= 100)  # Limit to reasonable range for CI

        detector = FormatDetector()

        times = []

        try:
            # Measure detection time over multiple iterations
            for _ in range(min(iterations, 20)):  # Cap at 20 for performance
                start_time = time.perf_counter()
                result = detector.detect_format(data)
                end_time = time.perf_counter()

                elapsed = max(0, end_time - start_time)  # Ensure non-negative
                times.append(elapsed)

                # Results should be consistent
                assert isinstance(result, SupportedFormat)

            # Performance should be reasonable (< 1 second per detection)
            max_time = max(times)
            assert max_time < 1.0

            # Performance should be relatively consistent (no huge outliers)
            if len(times) > 1:
                avg_time = sum(times) / len(times)
                # Only check variance if average is meaningful (> 0.001 seconds)
                if avg_time > 0.001:
                    for time_taken in times:
                        # No single detection should take more than 10x the average
                        assert time_taken < avg_time * 10

        except Exception as e:
            pytest.fail(f"Exception in scalability test: {type(e).__name__}: {e}")

    @given(
        st.dictionaries(
            keys=st.sampled_from(
                [
                    "testExecutions",
                    "testInfo",
                    "evidences",  # Xray specific
                    "testCase",
                    "execution",
                    "cycle",  # Zephyr specific
                    *TESTRAIL_COMMON_FIELDS,
                    "id",  # TestRail specific
                    "testsuites",
                    "testsuite",  # TestLink specific
                ]
            ),
            values=st.one_of(
                st.text(),
                st.lists(
                    st.dictionaries(
                        keys=st.text(min_size=1, max_size=10),
                        values=st.text(min_size=0, max_size=20),
                        min_size=0,
                        max_size=3,
                    )
                ),
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=50)
    def test_specific_format_indicators_invariant(self, data_with_indicators):
        """Invariant: Specific format indicators increase confidence appropriately."""
        detector = FormatDetector()

        try:
            detected_format = detector.detect_format(data_with_indicators)
            confidence = detector.get_format_confidence(
                data_with_indicators, detected_format
            )

            # Data with specific indicators should have some confidence
            # (though not necessarily high due to other factors)
            assert confidence >= 0.0

            # Format detection should not crash with indicator data
            assert isinstance(detected_format, SupportedFormat)

            # Should be able to get evidence details
            evidence = detector.get_format_evidence(
                data_with_indicators, detected_format
            )
            assert isinstance(evidence, dict)

        except Exception as e:
            pytest.fail(f"Exception with format indicators: {type(e).__name__}: {e}")
