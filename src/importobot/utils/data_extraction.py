"""Utilities for extracting data from nested structures."""

from __future__ import annotations

from typing import Any


def extract_nested_field_names(data: dict[str, Any]) -> set[str]:
    """
    Extract all field names from a nested data structure.

    Args:
        data: The nested dictionary to extract field names from

    Returns:
        Set of all field names found in the nested structure
    """
    field_names = set()

    def _traverse(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                field_names.add(key)
                if isinstance(value, dict | list):
                    _traverse(value)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict | list):
                    _traverse(item)

    _traverse(data)
    return field_names


def extract_nested_field_data(data: dict[str, Any]) -> dict[str, list[Any]]:
    """
    Extract all field data from a nested structure for performance optimization.

    Args:
        data: The nested dictionary to extract field data from

    Returns:
        Dictionary mapping field names to lists of all values found for that field
    """
    field_data: dict[str, list[Any]] = {}

    def _traverse(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key not in field_data:
                    field_data[key] = []
                field_data[key].append(value)
                if isinstance(value, dict | list):
                    _traverse(value)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict | list):
                    _traverse(item)

    _traverse(data)
    return field_data


__all__ = ["extract_nested_field_data", "extract_nested_field_names"]
