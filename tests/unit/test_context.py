"""Tests for ApplicationContext pattern.

Demonstrates how context pattern enables:
- Clean testing without global state pollution
- Multiple concurrent instances
- Explicit dependency management
"""

import threading
import time
from typing import cast

import pytest

from importobot.context import (
    ApplicationContext,
    cleanup_stale_contexts,
    clear_context,
    get_context,
    get_registry_stats,
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


class TestContextCleanup:
    """Test context cleanup and memory management."""

    @pytest.fixture(autouse=True)
    def _clean_context_and_registry(self):
        """Ensure clean context and registry for each test."""
        clear_context()
        cleanup_stale_contexts()
        yield
        clear_context()
        cleanup_stale_contexts()

    def test_cleanup_stale_contexts_removes_dead_threads(self):
        """Cleanup should remove contexts for threads that are no longer alive."""
        contexts_created = []

        def worker():
            context = get_context()
            contexts_created.append(context)

        # Create and finish threads
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads should be dead now
        stats_before = get_registry_stats()
        assert cast(int, stats_before["size"]) >= 5

        # Cleanup should remove dead thread contexts
        removed = cleanup_stale_contexts()
        assert removed >= 5

        stats_after = get_registry_stats()
        assert cast(int, stats_after["dead_threads"]) == 0

    def test_get_registry_stats_reports_accurate_counts(self):
        """Registry stats should accurately report thread states."""
        # Start with clean state
        cleanup_stale_contexts()

        # Create contexts in current thread
        _ = get_context()

        stats = get_registry_stats()
        assert cast(int, stats["size"]) >= 1
        assert cast(int, stats["alive_threads"]) >= 1
        assert isinstance(stats["thread_names"], list)

    def test_cleanup_returns_zero_when_no_stale_contexts(self):
        """Cleanup should return 0 when there are no stale contexts."""
        # Ensure registry is clean
        cleanup_stale_contexts()

        # Create context in current (alive) thread
        _ = get_context()

        # Should not remove contexts for alive threads
        removed = cleanup_stale_contexts()
        assert removed == 0

    def test_registry_stats_includes_thread_names(self):
        """Stats should include thread names for debugging."""
        _ = get_context()

        stats = get_registry_stats()
        assert "thread_names" in stats
        assert isinstance(stats["thread_names"], list)
        assert len(stats["thread_names"]) > 0

    def test_cleanup_is_thread_safe(self):
        """Cleanup should be safe to call from multiple threads."""
        results = []

        def worker():
            _ = get_context()
            # Small delay to increase chance of concurrent cleanup
            time.sleep(0.01)

        def cleanup_worker():
            removed = cleanup_stale_contexts()
            results.append(removed)

        # Create worker threads
        workers = [threading.Thread(target=worker) for _ in range(10)]
        for t in workers:
            t.start()
        for t in workers:
            t.join()

        # Run cleanup from multiple threads
        cleanup_threads = [threading.Thread(target=cleanup_worker) for _ in range(3)]
        for t in cleanup_threads:
            t.start()
        for t in cleanup_threads:
            t.join()

        # Should complete without errors
        assert len(results) == 3


class TestContextMemoryManagement:
    """Test memory management and leak prevention."""

    @pytest.fixture(autouse=True)
    def _clean_context_and_registry(self):
        """Ensure clean context and registry for each test."""
        clear_context()
        cleanup_stale_contexts()
        yield
        clear_context()
        cleanup_stale_contexts()

    def test_context_not_retained_after_thread_cleanup(self):
        """Context should be removable after thread exits."""
        initial_stats = get_registry_stats()
        initial_size = cast(int, initial_stats["size"])

        def worker():
            _ = get_context()

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        # Thread is dead, cleanup should work
        removed = cleanup_stale_contexts()
        assert removed >= 1

        final_stats = get_registry_stats()
        assert cast(int, final_stats["size"]) <= initial_size

    def test_clear_context_removes_from_registry(self):
        """Clearing context should unregister it from the registry."""
        initial_size = cast(int, get_registry_stats()["size"])

        _ = get_context()
        after_get = cast(int, get_registry_stats()["size"])
        assert after_get > initial_size

        clear_context()
        after_clear = cast(int, get_registry_stats()["size"])
        assert after_clear <= initial_size

    def test_registry_does_not_grow_unbounded_with_cleanup(self):
        """Registry size should stay bounded when using cleanup."""
        # Create and cleanup multiple times
        for _ in range(10):

            def worker():
                _ = get_context()

            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()

            cleanup_stale_contexts()

        # Registry should not accumulate contexts
        stats = get_registry_stats()
        # Allow for main thread and a few stragglers, but not 10+
        assert cast(int, stats["size"]) < 5
