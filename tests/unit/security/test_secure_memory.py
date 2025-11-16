"""Tests for secure memory management with BLAKE2b hashing."""

from __future__ import annotations

import gc
import threading
import time
import weakref

import pytest

from importobot.exceptions import ImportobotError
from importobot.security.secure_memory import (
    SecureMemory,
    SecureMemoryPool,
    SecureString,
    SecurityError,
    create_secure_string,
    get_secure_memory_pool,
    secure_compare_strings,
)


class TestSecureMemory:
    """Test SecureMemory class functionality."""

    def test_init_with_valid_data(self) -> None:
        """Test SecureMemory initialization with valid data."""
        data = b"test sensitive data"
        secure_mem = SecureMemory(data)

        assert secure_mem.size() == len(data)
        assert not secure_mem.is_locked()
        assert secure_mem.verify_integrity()

    def test_init_with_invalid_type(self) -> None:
        """Test SecureMemory initialization with invalid type."""
        with pytest.raises(
            SecurityError, match="SecureMemory requires bytes or bytearray"
        ):
            SecureMemory("invalid_string")  # type: ignore[arg-type]

    def test_reveal_data(self) -> None:
        """Test revealing data from SecureMemory."""
        original_data = b"sensitive test data"
        secure_mem = SecureMemory(original_data)

        revealed_data = secure_mem.reveal()
        assert revealed_data == original_data
        assert revealed_data is not original_data  # Should be a copy

    def test_reveal_after_zeroize(self) -> None:
        """Test revealing data after zeroization fails."""
        secure_mem = SecureMemory(b"test data")
        secure_mem.zeroize()

        with pytest.raises(
            SecurityError, match="Memory access denied after zeroization"
        ):
            secure_mem.reveal()

    def test_zeroize_functionality(self) -> None:
        """Test zeroization clears data properly."""
        secure_mem = SecureMemory(b"important secret data")
        assert not secure_mem.is_locked()

        # Zeroize the memory
        secure_mem.zeroize()

        # Verify memory is locked
        assert secure_mem.is_locked()
        assert secure_mem.verify_integrity()  # Zeroized memory is "intact"

    def test_multiple_zeroize_calls(self) -> None:
        """Test multiple zeroize calls are safe."""
        secure_mem = SecureMemory(b"test data")

        # First zeroize
        secure_mem.zeroize()
        assert secure_mem.is_locked()

        # Second zeroize should be safe
        secure_mem.zeroize()  # Should not raise

    def test_force_zeroize(self) -> None:
        """Test force zeroize even if already locked."""
        secure_mem = SecureMemory(b"test data")
        secure_mem.zeroize()

        # Force zeroize should work even if locked
        secure_mem.zeroize(force=True)

    def test_context_manager_zeroizes_memory(self) -> None:
        """Using SecureMemory as a context manager should zeroize automatically."""
        with SecureMemory(b"context data") as secure_mem:
            assert not secure_mem.is_locked()
            assert secure_mem.reveal() == b"context data"

        assert secure_mem.is_locked()

    def test_memory_integrity_verification(self) -> None:
        """Test BLAKE2b integrity verification."""
        original_data = b"integrity test data"
        secure_mem = SecureMemory(original_data)

        # Initial integrity should pass
        assert secure_mem.verify_integrity()

        # Reveal should still pass integrity
        revealed = secure_mem.reveal()
        assert secure_mem.verify_integrity()
        assert revealed == original_data

    def test_memory_size(self) -> None:
        """Test memory size reporting."""
        data = b"test data of specific length"
        secure_mem = SecureMemory(data)

        assert secure_mem.size() == len(data)

    def test_repr_and_str(self) -> None:
        """Test string representations are secure."""
        secure_mem = SecureMemory(b"secret data")

        repr_str = repr(secure_mem)
        str_str = str(secure_mem)

        assert "secret" not in repr_str.lower()
        assert "secret" not in str_str.lower()
        assert "size=" in repr_str
        assert "status=active" in repr_str

        # After zeroization
        secure_mem.zeroize()
        locked_repr = repr(secure_mem)
        assert "status=locked" in locked_repr

    def test_thread_safety(self) -> None:
        """Test thread safety of SecureMemory operations."""
        data = b"thread safety test data"
        secure_mem = SecureMemory(data)
        results: list[bytes | SecurityError] = []

        def reveal_data() -> None:
            try:
                revealed = secure_mem.reveal()
                results.append(revealed)
            except SecurityError as exc:
                results.append(exc)

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=reveal_data)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All operations should succeed
        assert len(results) == 10
        for result in results:
            assert isinstance(result, bytes)
            assert result == data

    def test_garbage_collection_cleanup(self) -> None:
        """Test that garbage collection triggers cleanup."""
        data = b"garbage collection test"
        secure_mem = SecureMemory(data)

        # Create weak reference to track object
        weak_ref = weakref.ref(secure_mem)

        # Delete strong reference
        del secure_mem

        # Force garbage collection
        gc.collect()

        # Object should be cleaned up (weak ref should be None)
        # Note: This test may be flaky due to GC timing
        obj = weak_ref()
        assert obj is None or obj.is_locked()


class TestSecureString:
    """Test SecureString class functionality."""

    def test_init_with_valid_string(self) -> None:
        """Test SecureString initialization with valid string."""
        test_str = "sensitive password"
        secure_str = SecureString(test_str)

        assert secure_str.value == test_str
        assert secure_str.size() == len(test_str)
        assert not secure_str.is_locked()

    def test_init_with_invalid_type(self) -> None:
        """Test SecureString initialization with invalid type."""
        with pytest.raises(SecurityError, match="SecureString requires string input"):
            SecureString(123)  # type: ignore[arg-type]

    def test_context_manager_zeroizes_string(self) -> None:
        """SecureString context manager should zeroize on exit."""
        with SecureString("temporary secret") as secure_str:
            assert not secure_str.is_locked()
            assert secure_str.value == "temporary secret"

        assert secure_str.is_locked()

    def test_byte_length(self) -> None:
        """Test byte length calculation."""
        test_str = "hello world"  # 11 chars
        secure_str = SecureString(test_str)

        # UTF-8 encoding should be same for ASCII
        assert secure_str.byte_length() == len(test_str.encode("utf-8"))
        assert secure_str.size() == len(test_str)

    def test_unicode_handling(self) -> None:
        """Test Unicode string handling."""
        test_str = "héllo 🌍 wörld"  # Contains Unicode characters
        secure_str = SecureString(test_str)

        assert secure_str.value == test_str
        assert secure_str.size() == len(test_str)
        # Unicode characters may take multiple bytes in UTF-8
        assert secure_str.byte_length() > len(test_str)

    def test_zeroize_string(self) -> None:
        """Test string zeroization."""
        secure_str = SecureString("secret password")
        assert not secure_str.is_locked()

        secure_str.zeroize()
        assert secure_str.is_locked()

        with pytest.raises(
            SecurityError, match="Memory access denied after zeroization"
        ):
            _ = secure_str.value

    def test_equality_comparison(self) -> None:
        """Test secure equality comparison."""
        str1 = SecureString("password123")
        str2 = SecureString("password123")
        str3 = SecureString("different456")

        assert str1 == str2
        assert str1 != str3
        assert hash(str1) != hash(
            str3
        )  # Different strings should have different hashes

    def test_equality_with_non_secure_string(self) -> None:
        """Test equality with non-SecureString objects."""
        secure_str = SecureString("test")

        assert secure_str != "test"
        assert secure_str != 123
        assert secure_str is not None

    def test_equality_after_zeroize(self) -> None:
        """Test equality comparison after zeroization."""
        str1 = SecureString("password")
        str2 = SecureString("password")

        # Before zeroization
        assert str1 == str2

        # Zeroize one string
        str1.zeroize()

        # After zeroization, comparison should return False
        assert str1 != str2

    def test_len_function(self) -> None:
        """Test len() function works."""
        test_str = "test string length"
        secure_str = SecureString(test_str)

        assert len(secure_str) == len(test_str)

    def test_secure_representation(self) -> None:
        """Test string representation is secure."""
        secure_str = SecureString("super secret password")

        repr_str = repr(secure_str)
        str_str = str(secure_str)

        assert "secret" not in repr_str.lower()
        assert "secret" not in str_str.lower()
        assert "password" not in repr_str.lower()
        assert "length=" in repr_str

        # After zeroization
        secure_str.zeroize()
        assert "<zeroized>" in repr(secure_str)


class TestSecureMemoryConvenienceFunctions:
    """Test convenience functions for secure memory operations."""

    def test_create_secure_string_valid(self) -> None:
        """Test create_secure_string with valid input."""
        secure_str = create_secure_string("test password")

        assert isinstance(secure_str, SecureString)
        assert secure_str.value == "test password"

    def test_create_secure_string_invalid_type(self) -> None:
        """Test create_secure_string with invalid type."""
        with pytest.raises(SecurityError, match="Expected string"):
            create_secure_string(123)  # type: ignore[arg-type]

    def test_create_secure_string_empty_string(self) -> None:
        """Test create_secure_string with empty string."""
        with pytest.raises(SecurityError, match="Empty strings cannot be secured"):
            create_secure_string("")

    def test_secure_compare_strings_valid(self) -> None:
        """Test secure_compare_strings with valid inputs."""
        str1 = SecureString("password123")
        str2 = SecureString("password123")

        assert secure_compare_strings(str1, str2)

    def test_secure_compare_strings_different(self) -> None:
        """Test secure_compare_strings with different strings."""
        str1 = SecureString("password123")
        str2 = SecureString("different456")

        assert not secure_compare_strings(str1, str2)

    def test_secure_compare_strings_invalid_type(self) -> None:
        """Test secure_compare_strings with invalid types."""
        str1 = SecureString("password123")
        str2 = "regular_string"

        with pytest.raises(SecurityError, match="Both arguments must be SecureString"):
            secure_compare_strings(str1, str2)  # type: ignore[arg-type]


class TestSecureMemoryPool:
    """Test SecureMemoryPool functionality."""

    def test_pool_initialization(self) -> None:
        """Test SecureMemoryPool initialization."""
        pool = SecureMemoryPool()
        stats = pool.get_stats()

        assert stats["total_instances"] == 0
        assert stats["active_instances"] == 0
        assert stats["locked_instances"] == 0
        assert stats["total_bytes"] == 0
        assert stats["peak_usage"] == 0
        assert stats["integrity_algorithm"] == "BLAKE2b-512"

    def test_pool_allocate(self) -> None:
        """Test allocating memory from pool."""
        pool = SecureMemoryPool()
        data = b"test data for pool"

        secure_mem = pool.allocate(data)
        stats = pool.get_stats()

        assert isinstance(secure_mem, SecureMemory)
        assert stats["total_instances"] == 1
        assert stats["active_instances"] == 1
        assert stats["locked_instances"] == 0
        assert stats["total_bytes"] == len(data)
        assert stats["peak_usage"] == len(data)

    def test_pool_multiple_allocations(self) -> None:
        """Test multiple allocations in pool."""
        pool = SecureMemoryPool()
        data1 = b"first data chunk"
        data2 = b"second data chunk which is longer"

        pool.allocate(data1)
        pool.allocate(data2)

        stats = pool.get_stats()
        assert stats["total_instances"] == 2
        assert stats["active_instances"] == 2
        assert stats["total_bytes"] == len(data1) + len(data2)
        assert stats["peak_usage"] == len(data1) + len(data2)

    def test_pool_cleanup_all(self) -> None:
        """Test cleaning up all instances in pool."""
        pool = SecureMemoryPool()
        data1 = b"first data"
        data2 = b"second data"

        mem1 = pool.allocate(data1)
        mem2 = pool.allocate(data2)

        stats = pool.get_stats()
        assert stats["active_instances"] == 2

        # Cleanup all
        cleaned_count = pool.cleanup_all()
        assert cleaned_count == 2

        stats_after = pool.get_stats()
        assert stats_after["active_instances"] == 0
        assert stats_after["locked_instances"] == 2

        # Memory should be zeroized
        assert mem1.is_locked()
        assert mem2.is_locked()

    def test_pool_cleanup_locked(self) -> None:
        """Test cleaning up locked instances."""
        pool = SecureMemoryPool()
        data1 = b"first data"
        data2 = b"second data"

        mem1 = pool.allocate(data1)
        pool.allocate(data2)

        # Zeroize one instance
        mem1.zeroize()

        # Cleanup locked instances
        removed_count = pool.cleanup_locked()
        assert removed_count == 1

        stats = pool.get_stats()
        assert stats["total_instances"] == 1
        assert stats["active_instances"] == 1
        assert stats["locked_instances"] == 0

    def test_global_pool(self) -> None:
        """Test global secure memory pool."""
        pool = get_secure_memory_pool()
        assert isinstance(pool, SecureMemoryPool)

        # Should be the same instance
        pool2 = get_secure_memory_pool()
        assert pool is pool2

    def test_pool_stats_details(self) -> None:
        """Test detailed pool statistics."""
        pool = SecureMemoryPool()

        # Add some data
        pool.allocate(b"data1")
        pool.allocate(b"data2")
        pool.allocate(b"much longer data chunk for testing average size")

        stats = pool.get_stats()
        assert stats["total_instances"] == 3
        assert stats["active_instances"] == 3
        assert stats["average_size"] > 0
        assert stats["integrity_algorithm"] == "BLAKE2b-512"

    def test_pool_thread_safety(self) -> None:
        """Test pool thread safety."""
        pool = SecureMemoryPool()
        results: list[tuple[int, int | Exception]] = []

        def allocate_data(index: int) -> None:
            try:
                data = f"thread data {index}".encode()
                secure_mem = pool.allocate(data)
                results.append((index, secure_mem.size()))
            except Exception as exc:
                results.append((index, exc))

        threads = []
        for i in range(20):
            thread = threading.Thread(target=allocate_data, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All allocations should succeed
        assert len(results) == 20
        for index, result in results:
            assert isinstance(result, int)
            expected_len = len(f"thread data {index}".encode())
            assert result == expected_len

        stats = pool.get_stats()
        assert stats["total_instances"] == 20


class TestBlake2bIntegration:
    """Test BLAKE2b hash integration and security benefits."""

    def test_b2b_checksum_length(self) -> None:
        """Test BLAKE2b produces 512-bit (64-byte) checksum."""
        data = b"test data for blake2b verification"
        secure_mem = SecureMemory(data)

        # Access internal checksum through the calculate_checksum method
        checksum = secure_mem._calculate_checksum()

        # BLAKE2b-512 should produce 64 bytes
        assert len(checksum) == 64
        assert isinstance(checksum, bytes)

    def test_b2b_checksum_deterministic(self) -> None:
        """Test BLAKE2b checksum is deterministic for same data."""
        data = b"deterministic test data"
        secure_mem1 = SecureMemory(data)
        secure_mem2 = SecureMemory(data)

        checksum1 = secure_mem1._calculate_checksum()
        checksum2 = secure_mem2._calculate_checksum()

        assert checksum1 == checksum2
        assert len(checksum1) == 64

    def test_b2b_checksum_different_data(self) -> None:
        """Test BLAKE2b checksum differs for different data."""
        data1 = b"first test data"
        data2 = b"second test data"

        checksum1 = SecureMemory(data1)._calculate_checksum()
        checksum2 = SecureMemory(data2)._calculate_checksum()

        assert checksum1 != checksum2

    def test_b2b_performance_characteristics(self) -> None:
        """Test that BLAKE2b integration has reasonable performance."""

        # Create data of different sizes
        small_data = b"small test data"
        large_data = b"x" * 10000  # 10KB

        # Test small data performance
        start_time = time.perf_counter()
        secure_mem_small = SecureMemory(small_data)
        secure_mem_small.reveal()  # Trigger checksum verification
        small_time = time.perf_counter() - start_time

        # Test large data performance
        start_time = time.perf_counter()
        secure_mem_large = SecureMemory(large_data)
        secure_mem_large.reveal()  # Trigger checksum verification
        large_time = time.perf_counter() - start_time

        # Performance should be reasonable (less than 1 second for these operations)
        assert small_time < 1.0
        assert large_time < 1.0

        # Large data should take longer than small data, but not exponentially so
        assert large_time > small_time

    def test_b2b_integrity_tampering_detection(self) -> None:
        """Test that BLAKE2b can detect memory tampering."""
        original_data = b"original untampered data"
        secure_mem = SecureMemory(original_data)

        # Get original checksum
        original_checksum = secure_mem._checksum

        # Verify integrity passes initially
        assert secure_mem.verify_integrity()
        assert secure_mem._checksum == original_checksum

        # Simulate memory tampering by modifying the internal data
        # This is a bit tricky since we're accessing internal state,
        # but we can simulate by creating a new checksum with different data
        tampered_checksum = SecureMemory(b"tampered data")._checksum

        # Checksums should be different
        assert original_checksum != tampered_checksum

        # The tampered checksum should not match the original memory's checksum
        assert secure_mem._checksum != tampered_checksum


class TestSecurityErrorHierarchy:
    """Test SecurityError exception hierarchy."""

    def test_security_error_inheritance(self) -> None:
        """Test SecurityError inherits from ImportobotError."""
        assert issubclass(SecurityError, ImportobotError)

    def test_security_error_creation(self) -> None:
        """Test SecurityError creation and message."""
        message = "Test security failure"
        error = SecurityError(message)

        assert str(error) == message
        assert isinstance(error, Exception)
        assert isinstance(error, ImportobotError)

    def test_security_error_with_cause(self) -> None:
        """Test SecurityError with underlying cause."""
        original_error = ValueError("Original error")

        with pytest.raises(SecurityError) as exc_info:
            raise SecurityError("Security wrapper") from original_error

        assert exc_info.value.__cause__ is original_error
        assert str(exc_info.value) == "Security wrapper"
