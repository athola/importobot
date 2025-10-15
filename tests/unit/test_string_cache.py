"""Tests for the string caching utilities."""

from __future__ import annotations

import importlib

import pytest

from importobot.utils import string_cache


def test_cache_clear_threshold_evicts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured threshold should clear the cache after enough operations."""
    importlib.reload(string_cache)

    monkeypatch.setattr(string_cache._CacheState, "clear_threshold", 2, raising=False)
    monkeypatch.setattr(string_cache._CacheState, "operation_count", 0, raising=False)

    first = string_cache.data_to_lower_cached("FOO")
    second = string_cache.data_to_lower_cached("BAR")

    assert first == "foo"
    assert second == "bar"
    # After threshold is reached the cache should be empty
    assert string_cache.cached_string_lower.cache_info().currsize == 0
    # pylint: disable=protected-access
    assert string_cache._CacheState.operation_count == 0


def test_clear_string_cache_resets_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clearing the cache should also reset the operation counter."""
    importlib.reload(string_cache)

    monkeypatch.setattr(string_cache._CacheState, "operation_count", 5, raising=False)
    string_cache.clear_string_cache()

    assert string_cache.cached_string_lower.cache_info().currsize == 0
    # pylint: disable=protected-access
    assert string_cache._CacheState.operation_count == 0
