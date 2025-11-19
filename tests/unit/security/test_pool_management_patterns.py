"""Tests for new pool management patterns replacing global pool."""

from __future__ import annotations

import threading

from importobot.security.secure_memory import (
    SecureMemoryPool,
    SecureMemoryPoolFactory,
    get_current_memory_pool,
    secure_memory_pool_context,
)


class TestPoolManagementPatterns:
    """Test the various pool management patterns."""

    def test_direct_pool_creation(self) -> None:
        """Test direct pool creation with names."""
        pool = SecureMemoryPool(name="direct-test")
        assert pool.name == "direct-test"

        # Pool should start empty
        stats = pool.get_stats()
        assert stats["total_instances"] == 0
        assert stats["active_instances"] == 0

    def test_factory_pattern(self) -> None:
        """Test factory pattern for pool creation."""
        # Test basic factory creation
        pool1 = SecureMemoryPoolFactory.create_pool("factory-basic")
        assert pool1.name == "factory-basic"

        # Test isolated pool creation
        isolated_pool = SecureMemoryPoolFactory.create_isolated_pool("session-123")
        assert isolated_pool.name == "isolated-session-123"

        # Test temporary pool creation
        temp_pool = SecureMemoryPoolFactory.create_temporary_pool()
        assert temp_pool.name.startswith("temp-")

    def test_current_pool_isolation(self) -> None:
        """Test that each thread gets its own current pool."""

        def thread_worker(thread_id: int) -> SecureMemoryPool:
            """Worker function that runs in a separate thread."""
            pool = get_current_memory_pool()
            # Allocate some memory to verify it's working
            pool.allocate(f"thread-{thread_id}".encode())
            return pool

        # Create multiple threads
        threads = []
        pools = []

        for i in range(3):
            thread = threading.Thread(target=lambda i=i: pools.append(thread_worker(i)))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Each thread should have gotten its own pool
        assert len(pools) == 3
        # Each pool should have one allocation
        for pool in pools:
            stats = pool.get_stats()
            assert stats["total_instances"] == 1

    def test_context_manager_isolation(self) -> None:
        """Test context manager pool isolation."""
        # Start with default pool
        default_pool = get_current_memory_pool()
        original_name = default_pool.name

        # Use context manager with custom pool
        custom_pool = SecureMemoryPool(name="context-test")
        with secure_memory_pool_context(custom_pool) as ctx_pool:
            # Should be using the custom pool
            assert get_current_memory_pool() is custom_pool
            assert get_current_memory_pool() is ctx_pool
            assert ctx_pool.name == "context-test"

        # Should revert to original pool after context
        restored_pool = get_current_memory_pool()
        assert restored_pool.name == original_name

    def test_nested_context_managers(self) -> None:
        """Test nested context manager behavior."""
        outer_pool = SecureMemoryPool(name="outer")
        middle_pool = SecureMemoryPool(name="middle")
        inner_pool = SecureMemoryPool(name="inner")

        with secure_memory_pool_context(outer_pool):
            assert get_current_memory_pool() is outer_pool

            with secure_memory_pool_context(middle_pool):
                assert get_current_memory_pool() is middle_pool

                with secure_memory_pool_context(inner_pool):
                    assert get_current_memory_pool() is inner_pool

                # Should revert to middle
                assert get_current_memory_pool() is middle_pool

            # Should revert to outer
            assert get_current_memory_pool() is outer_pool

        # Should revert to whatever was before outer
        get_current_memory_pool()

    def test_context_manager_with_pool_name(self) -> None:
        """Test context manager with pool name parameter."""
        with secure_memory_pool_context(pool_name="named-context") as pool:
            assert pool.name == "named-context"
            assert get_current_memory_pool() is pool

    def test_dependency_injection_pattern(self) -> None:
        """Test dependency injection pattern for pools."""
        # Create multiple pools with different purposes
        session_pool = SecureMemoryPool(name="user-session")
        request_pool = SecureMemoryPool(name="request-123")

        # Simulate using pools in different contexts
        with secure_memory_pool_context(session_pool):
            session_pool.allocate(b"user data")
            assert get_current_memory_pool() is session_pool

            with secure_memory_pool_context(request_pool):
                request_pool.allocate(b"request data")
                assert get_current_memory_pool() is request_pool

            # Back to session context
            assert get_current_memory_pool() is session_pool

        # Both pools should have their allocations
        session_stats = session_pool.get_stats()
        request_stats = request_pool.get_stats()
        assert session_stats["total_instances"] == 1
        assert request_stats["total_instances"] == 1

    def test_pool_statistics_with_names(self) -> None:
        """Test that pool statistics include pool names."""
        pool = SecureMemoryPool(name="stats-test")

        # Allocate some memory
        pool.allocate(b"test data 1")
        pool.allocate(b"test data 2")

        stats = pool.get_stats()
        assert stats["pool_name"] == "stats-test"
        assert stats["total_instances"] == 2
        assert stats["active_instances"] == 2
        assert stats["integrity_algorithm"] == "BLAKE2b-512"

    def test_pool_cleanup_operations(self) -> None:
        """Test pool cleanup operations."""
        pool = SecureMemoryPool(name="cleanup-test")

        # Allocate some memory
        mem1 = pool.allocate(b"test data 1")
        pool.allocate(b"test data 2")

        # Should have active instances
        stats = pool.get_stats()
        assert stats["active_instances"] == 2

        # Zeroize one instance
        mem1.zeroize()
        stats = pool.get_stats()
        assert stats["active_instances"] == 1
        assert stats["locked_instances"] == 1

        # Cleanup locked instances
        removed_count = pool.cleanup_locked()
        assert removed_count == 1
        stats = pool.get_stats()
        assert stats["total_instances"] == 1
        assert stats["locked_instances"] == 0

        # Cleanup remaining instances
        cleanup_count = pool.cleanup_all()
        assert cleanup_count == 1
        stats = pool.get_stats()
        assert stats["active_instances"] == 0
        assert stats["total_instances"] == 1

    def test_no_global_state_pollution(self) -> None:
        """Test that context managers don't pollute global state."""
        # Store original pool
        original_pool = get_current_memory_pool()
        original_name = original_pool.name

        # Use context manager multiple times
        for i in range(3):
            with secure_memory_pool_context(pool_name=f"test-{i}"):
                current = get_current_memory_pool()
                assert current.name == f"test-{i}"

        # Should revert to original state
        final_pool = get_current_memory_pool()
        assert final_pool is original_pool
        assert final_pool.name == original_name
