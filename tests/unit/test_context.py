"""Tests for ApplicationContext pattern.

Demonstrates how context pattern enables:
- Clean testing without global state pollution
- Multiple concurrent instances
- Explicit dependency management
"""

import threading

import pytest

from importobot.context import (
    ApplicationContext,
    clear_context,
    get_context,
    set_context,
)
from importobot.services.performance_cache import get_performance_cache


class TestApplicationContext:
    """Test application context lifecycle and isolation."""

    def test_context_creates_lazily(self):
        """Context instances are created on first access."""
        clear_context()  # Ensure clean state

        context = get_context()
        assert isinstance(context, ApplicationContext)

    def test_context_is_thread_local(self):
        """Each thread gets its own context instance."""
        contexts = []

        def capture_context():
            contexts.append(get_context())

        threads = [threading.Thread(target=capture_context) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have gotten a different context instance
        assert len({id(context) for context in contexts}) == 3

    def test_context_can_be_explicitly_set(self):
        """Context can be explicitly set for dependency injection."""
        custom_context = ApplicationContext()
        set_context(custom_context)

        retrieved = get_context()
        assert retrieved is custom_context

    def test_clear_context_resets_state(self):
        """Clearing context removes all cached state."""
        context = get_context()
        # Access something to create state
        _ = context.performance_cache

        clear_context()

        # New context should be created
        new_context = get_context()
        assert new_context is not context

    def test_performance_cache_property(self):
        """Performance cache is lazily created through context."""
        context = ApplicationContext()
        assert context._performance_cache is None

        cache = context.performance_cache
        assert cache is not None
        # Subsequent access returns same instance
        assert context.performance_cache is cache

    def test_context_clear_caches(self):
        """Context can clear all cached data."""
        context = ApplicationContext()
        cache = context.performance_cache

        # Add some data
        cache.set("demo-key", "value")

        # Clear via context
        context.clear_caches()

        # Cache should be cleared
        assert cache.get("demo-key") is None

    def test_context_reset(self):
        """Context reset removes all dependencies."""
        context = ApplicationContext()
        _ = context.performance_cache  # Create cache

        assert context._performance_cache is not None

        context.reset()

        assert context._performance_cache is None


class TestContextInTesting:
    """Demonstrate how context pattern improves testing."""

    @pytest.fixture(autouse=True)
    def _clean_context(self):
        """Ensure clean context for each test."""
        clear_context()
        yield
        clear_context()

    def test_isolation_example_1(self):
        """First test has clean context."""
        context = get_context()
        cache = context.performance_cache

        # This test's modifications don't affect other tests
        cache.set("test1", "value1")

    def test_isolation_example_2(self):
        """Second test also has clean context."""
        context = get_context()
        cache = context.performance_cache

        # Starts fresh - no state from previous test
        assert cache.get("test1") is None


class TestContextVsGlobalVariable:
    """Compare context pattern vs global variable pattern."""

    def test_context_allows_multiple_instances(self):
        """With context, we can have multiple independent instances."""
        context1 = ApplicationContext()
        context2 = ApplicationContext()

        cache1 = context1.performance_cache
        cache2 = context2.performance_cache

        # These are independent instances
        assert cache1 is not cache2

    def test_context_explicit_dependency_injection(self):
        """Context enables explicit dependency injection for testing."""
        # Create custom context with test configuration
        test_context = ApplicationContext()

        # Use it explicitly
        set_context(test_context)

        # Now all code using get_context() will use our test context
        cache = get_performance_cache()
        assert cache is not None
