"""Unit tests for JSON size validation helper."""

import pytest

from importobot.exceptions import ValidationError
from importobot.utils.validation import validate_json_size


def _build_json_payload(repeated_char_count: int) -> str:
    return '{"data": "' + ("x" * repeated_char_count) + '"}'


def test_json_size_validation_blocks_large_payloads() -> None:
    """JSON payloads larger than 10MB should be rejected."""
    large_json = _build_json_payload(11 * 1024 * 1024)

    with pytest.raises(ValidationError) as exc:
        validate_json_size(large_json, max_size_mb=10)

    message = str(exc.value)
    assert "JSON input too large" in message
    assert "10MB limit" in message


def test_json_size_validation_allows_payloads_under_limit() -> None:
    """Payloads just under the limit should pass validation."""
    almost_limit = _build_json_payload(10 * 1024 * 1024 - 1024)
    validate_json_size(almost_limit, max_size_mb=10)


@pytest.mark.parametrize("size_mb", [1, 5, 9])
def test_json_size_validation_passes_reasonable_sizes(size_mb: int) -> None:
    """Smaller payloads should always be accepted."""
    payload = _build_json_payload(size_mb * 1024 * 512)
    validate_json_size(payload, max_size_mb=10)


def test_json_size_validation_ignores_non_strings() -> None:
    """Non-string inputs are ignored by size validation."""
    validate_json_size({"data": "value"}, max_size_mb=10)
    validate_json_size(None, max_size_mb=10)
    validate_json_size(42, max_size_mb=10)
