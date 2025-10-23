"""Regex compilation cache for improved performance.

This module provides a centralized cache for compiled regex patterns
to avoid repeated compilation of the same patterns.
"""

import re
from functools import lru_cache
from re import Pattern


def get_compiled_pattern(pattern: str, flags: int | re.RegexFlag = 0) -> Pattern[str]:
    r"""Get a compiled regex pattern, using cache for performance.

    Args:
        pattern: The regex pattern string
        flags: Regex flags (default: 0)

    Returns:
        Compiled regex pattern

    Example:
        >>> pattern = get_compiled_pattern(r'\d+')
        >>> pattern.findall('abc123def')
        ['123']
    """
    return _compile_pattern(pattern, flags)


@lru_cache(maxsize=512)
def _compile_pattern(pattern: str, flags: int) -> Pattern[str]:
    """Compile regex pattern with LRU caching.

    Args:
        pattern: The regex pattern string
        flags: Regex flags as integer

    Returns:
        Compiled regex pattern
    """
    return re.compile(pattern, flags)


def search_cached(
    pattern: str, text: str, flags: int | re.RegexFlag = 0
) -> re.Match[str] | None:
    """Perform regex search using cached pattern compilation.

    Args:
        pattern: The regex pattern string
        text: Text to search in
        flags: Regex flags (default: 0)

    Returns:
        Match object if found, None otherwise
    """
    compiled_pattern = get_compiled_pattern(pattern, flags)
    return compiled_pattern.search(text)


def match_cached(
    pattern: str, text: str, flags: int | re.RegexFlag = 0
) -> re.Match[str] | None:
    """Perform regex match using cached pattern compilation.

    Args:
        pattern: The regex pattern string
        text: Text to match against
        flags: Regex flags (default: 0)

    Returns:
        Match object if found, None otherwise
    """
    compiled_pattern = get_compiled_pattern(pattern, flags)
    return compiled_pattern.match(text)


def findall_cached(pattern: str, text: str, flags: int | re.RegexFlag = 0) -> list[str]:
    """Find all matches using cached pattern compilation.

    Args:
        pattern: The regex pattern string
        text: Text to search in
        flags: Regex flags (default: 0)

    Returns:
        List of all matches
    """
    compiled_pattern = get_compiled_pattern(pattern, flags)
    return compiled_pattern.findall(text)


def sub_cached(
    pattern: str, replacement: str, text: str, flags: int | re.RegexFlag = 0
) -> str:
    """Perform regex substitution using cached pattern compilation.

    Args:
        pattern: The regex pattern string
        replacement: Replacement string
        text: Text to process
        flags: Regex flags (default: 0)

    Returns:
        Text with substitutions applied
    """
    compiled_pattern = get_compiled_pattern(pattern, flags)
    return compiled_pattern.sub(replacement, text)


def clear_cache() -> None:
    """Clear the regex compilation cache."""
    _compile_pattern.cache_clear()


def get_cache_info() -> dict[str, int | None]:
    """Get cache statistics.

    Returns:
        Dictionary with cache statistics
    """
    info = _compile_pattern.cache_info()  # pylint: disable=no-value-for-parameter
    return {
        "hits": info.hits,
        "misses": info.misses,
        "maxsize": info.maxsize,
        "currsize": info.currsize,
    }


__all__ = [
    "clear_cache",
    "findall_cached",
    "get_cache_info",
    "get_compiled_pattern",
    "match_cached",
    "search_cached",
    "sub_cached",
]
