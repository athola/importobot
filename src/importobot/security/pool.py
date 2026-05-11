"""Secure memory pool management.

This module provides pool management for SecureMemory instances:
- SecureMemoryPool: Resource tracking and bulk cleanup
- SecureMemoryPoolContext: Thread-safe context management
- SecureMemoryPoolFactory: Pool creation patterns with thread-local management
"""

from __future__ import annotations

import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from importobot.security.memory import SecureMemory


class ThreadLocalPoolStorage:
    """Thread-local storage for SecureMemoryPool instances.

    Encapsulates thread-local storage creation and access for SecureMemoryPool
    instances. This pattern centralizes thread-local management and makes
    testing easier through dependency injection.

    Use ThreadLocalPoolStorageFactory.get_storage() to obtain the default
    instance instead of creating instances directly.
    """

    def __init__(self) -> None:
        """Initialize thread-local storage container."""
        self._storage = threading.local()

    def get_current_pool(self) -> SecureMemoryPool | None:
        """Get the current pool from thread-local storage.

        Returns:
            Current SecureMemoryPool or None if not set
        """
        return getattr(self._storage, "current_pool", None)

    def set_current_pool(self, pool: SecureMemoryPool | None) -> None:
        """Set the current pool in thread-local storage.

        Args:
            pool: Pool to set, or None to clear
        """
        if pool is None:
            if hasattr(self._storage, "current_pool"):
                delattr(self._storage, "current_pool")
        else:
            self._storage.current_pool = pool

    def has_pool(self) -> bool:
        """Check if a pool exists in thread-local storage.

        Returns:
            True if a pool is currently set
        """
        return hasattr(self._storage, "current_pool")


class ThreadLocalPoolStorageFactory:
    """Factory for ThreadLocalPoolStorage with lazy initialization.

    Provides controlled access to thread-local storage without module-level
    globals. Uses lazy initialization to defer storage creation until needed.

    Example:
        # Get the default storage instance
        storage = ThreadLocalPoolStorageFactory.get_storage()

        # For testing: create isolated storage
        test_storage = ThreadLocalPoolStorageFactory.create_storage()
    """

    _instance: ThreadLocalPoolStorage | None = None
    _lock = threading.Lock()

    @classmethod
    def get_storage(cls) -> ThreadLocalPoolStorage:
        """Get the default ThreadLocalPoolStorage instance.

        Uses lazy initialization with double-checked locking for thread safety.

        Returns:
            The default ThreadLocalPoolStorage instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ThreadLocalPoolStorage()
        return cls._instance

    @classmethod
    def create_storage(cls) -> ThreadLocalPoolStorage:
        """Create a new isolated ThreadLocalPoolStorage instance.

        Useful for testing or isolated execution contexts.

        Returns:
            A new ThreadLocalPoolStorage instance
        """
        return ThreadLocalPoolStorage()

    @classmethod
    def reset_storage(cls) -> None:
        """Reset the default storage instance.

        Primarily for testing purposes to ensure clean state.
        """
        with cls._lock:
            cls._instance = None


class SecureMemoryPool:
    """Pool manager for SecureMemory instances with resource tracking.

    This class manages a pool of SecureMemory instances to:
    1. Track memory usage
    2. Prevent memory leaks
    3. Provide bulk cleanup operations
    4. Monitor security metrics
    5. Use BLAKE2b for integrity verification across the pool
    """

    def __init__(self, name: str | None = None) -> None:
        """Initialize pool tracking structures.

        Args:
            name: Optional name for the pool instance for identification
        """
        self._pool: list[SecureMemory] = []
        self._mutex = threading.Lock()
        self._total_bytes = 0
        self._peak_usage = 0
        self._name = name or f"pool-{id(self)}"

    @property
    def name(self) -> str:
        """Get the pool name."""
        return self._name

    def allocate(self, data: bytes) -> SecureMemory:
        """Allocate SecureMemory from pool.

        Args:
            data: Data to secure

        Returns:
            SecureMemory instance with BLAKE2b integrity verification
        """
        secure_mem = SecureMemory(data)

        with self._mutex:
            self._pool.append(secure_mem)
            self._total_bytes += len(data)
            self._peak_usage = max(self._peak_usage, self._total_bytes)

        return secure_mem

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        with self._mutex:
            active_count = sum(1 for mem in self._pool if not mem.is_locked())
            locked_count = len(self._pool) - active_count

            return {
                "pool_name": self._name,
                "total_instances": len(self._pool),
                "active_instances": active_count,
                "locked_instances": locked_count,
                "total_bytes": self._total_bytes,
                "peak_usage": self._peak_usage,
                "average_size": self._total_bytes / max(len(self._pool), 1),
                "integrity_algorithm": "BLAKE2b-512",
            }

    def cleanup_all(self) -> int:
        """Zeroize all SecureMemory instances in pool.

        Returns:
            Number of instances zeroized
        """
        with self._mutex:
            count = 0
            for secure_mem in self._pool:
                if not secure_mem.is_locked():
                    secure_mem.zeroize()
                    count += 1

            return count

    def cleanup_locked(self) -> int:
        """Remove locked instances from pool.

        Returns:
            Number of instances removed
        """
        with self._mutex:
            original_size = len(self._pool)
            self._pool = [mem for mem in self._pool if not mem.is_locked()]
            return original_size - len(self._pool)


class SecureMemoryPoolContext:
    """Context manager for secure memory pool management.

    Provides thread-safe pool instances without relying on global state.
    Supports dependency injection while maintaining backward compatibility.
    Uses ThreadLocalPoolStorageFactory for thread-local access.
    """

    def __init__(
        self,
        pool: SecureMemoryPool | None = None,
        pool_name: str | None = None,
        storage: ThreadLocalPoolStorage | None = None,
    ):
        """Initialize pool context.

        Args:
            pool: Optional pool instance. If None, creates default pool.
            pool_name: Optional name for created pool (used only if pool is None)
            storage: Optional storage factory for dependency injection in tests
        """
        self._storage = storage or ThreadLocalPoolStorageFactory.get_storage()
        self.pool = pool or SecureMemoryPool(name=pool_name)
        self._has_context = self._storage.has_pool()
        self._previous_pool = self._storage.get_current_pool()

    def __enter__(self) -> SecureMemoryPool:
        """Enter context and set pool in thread-local storage."""
        self._storage.set_current_pool(self.pool)
        return self.pool

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and restore previous pool."""
        if self._has_context:
            self._storage.set_current_pool(self._previous_pool)
        else:
            self._storage.set_current_pool(None)


@contextmanager
def secure_memory_pool_context(
    pool: SecureMemoryPool | None = None,
    pool_name: str | None = None,
    storage: ThreadLocalPoolStorage | None = None,
) -> Generator[SecureMemoryPool, None, None]:
    """Context manager for secure memory pool management.

    Args:
        pool: Optional pool instance. If None, creates default pool.
        pool_name: Optional name for created pool (used only if pool is None)
        storage: Optional storage factory for dependency injection in tests

    Yields:
        SecureMemoryPool instance for use in the context

    Example:
        with secure_memory_pool_context() as pool:
            secure_mem = pool.allocate(b"secret data")
            # Pool is automatically managed within the context

        # Pool is automatically cleaned up when context exits
    """
    with SecureMemoryPoolContext(pool, pool_name, storage) as mem_pool:
        yield mem_pool


def get_current_memory_pool(
    storage: ThreadLocalPoolStorage | None = None,
) -> SecureMemoryPool:
    """Get the current thread-local secure memory pool.

    Args:
        storage: Optional storage factory for dependency injection in tests

    Returns:
        Current SecureMemoryPool instance from thread-local context,
        or creates a new default instance if none exists.

    Note:
        This replaces the global pool pattern.
    """
    storage = storage or ThreadLocalPoolStorageFactory.get_storage()
    current = storage.get_current_pool()
    if current is None:
        current = SecureMemoryPool(name="default")
        storage.set_current_pool(current)
    return current


class SecureMemoryPoolFactory:
    """Factory for creating and managing SecureMemoryPool instances.

    Provides various pool creation patterns and configuration options.
    """

    @staticmethod
    def create_pool(name: str | None = None) -> SecureMemoryPool:
        """Create a new SecureMemoryPool instance.

        Args:
            name: Optional name for the pool

        Returns:
            New SecureMemoryPool instance
        """
        return SecureMemoryPool(name=name)

    @staticmethod
    def create_isolated_pool(context: str) -> SecureMemoryPool:
        """Create an isolated pool for a specific context.

        Args:
            context: Context identifier (e.g., "session-1", "request-42")

        Returns:
            New SecureMemoryPool instance with context-based naming
        """
        return SecureMemoryPool(name=f"isolated-{context}")

    @staticmethod
    def create_temporary_pool() -> SecureMemoryPool:
        """Create a temporary pool for short-lived operations.

        Returns:
            New SecureMemoryPool instance marked as temporary
        """
        return SecureMemoryPool(name=f"temp-{int(time.time())}")


__all__ = [
    "SecureMemoryPool",
    "SecureMemoryPoolContext",
    "SecureMemoryPoolFactory",
    "ThreadLocalPoolStorage",
    "ThreadLocalPoolStorageFactory",
    "get_current_memory_pool",
    "secure_memory_pool_context",
]
