"""Shared field extraction utilities."""

from typing import Any, Dict, List


def extract_field(data: Dict[str, Any], field_names: List[str]) -> str:
    """Extract value from first matching field name.

    Args:
        data: Dictionary to search in
        field_names: List of field names to try in order

    Returns:
        String value of first matching field, or empty string if none found
    """
    for field in field_names:
        if field in data and data[field]:
            return str(data[field])
    return ""
