"""Shared field extraction utilities."""

from typing import Any


def extract_field(data: dict[str, Any], field_names: list[str]) -> str:
    """Extract value from first matching field name.

    Args:
        data: Dictionary to search in
        field_names: List of field names to try in order

    Returns:
        String value of first matching field, or empty string if none found
    """
    for field in field_names:
        if data.get(field):
            return str(data[field])
    return ""
