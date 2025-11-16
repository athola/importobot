"""Shared data analysis utilities."""

from typing import Any


def count_data_elements(data: Any) -> int:
    """Count the number of elements/entries in data structures.

    Args:
        data: The data structure to count

    Returns:
        Number of elements (list length, dict entries, or 1 for primitives)
    """
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return len(data)
    return 1


def count_data_fields(data: Any) -> int:
    """Count the number of fields/attributes in data structures.

    Args:
        data: The data structure to analyze

    Returns:
        Number of fields (dict keys, or fields in first list item)
    """
    if isinstance(data, dict):
        return len(data)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        # For lists of dictionaries, count fields in first record
        return len(data[0])
    return 0


def get_data_types(data: Any) -> dict[str, int]:
    """Get count of different data types in the data.

    Args:
        data: The data structure to analyze

    Returns:
        Dictionary mapping type names to their counts
    """
    type_counts: dict[str, int] = {}

    if isinstance(data, dict):
        for value in data.values():
            type_name = type(value).__name__
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
    else:
        type_name = type(data).__name__
        type_counts[type_name] = 1

    return type_counts


# Internal utility - not part of public API
__all__: list[str] = []
