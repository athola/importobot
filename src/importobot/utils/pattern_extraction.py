"""Shared pattern extraction utilities for keyword generators."""

import re


def extract_pattern(text: str, pattern: str) -> str:
    """Extract pattern from text using regex.

    Args:
        text: Text to search in
        pattern: Regex pattern to search for

    Returns:
        Matched text or empty string if no match
    """
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        # If the pattern has capture groups, return group 1
        # Otherwise, return the entire match
        return (
            match.group(1)
            if match.lastindex and match.lastindex >= 1
            else match.group(0)
        )
    return ""
