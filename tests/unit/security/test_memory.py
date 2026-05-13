"""Direct-import and invariant tests for the SecureMemory source module.

Behavioural coverage of ``SecureMemory`` lives in
``tests/unit/security/test_secure_memory.py``, which imports through the
``importobot.security.secure_memory`` facade. These tests pin the
*source-of-truth path* in ``importobot.security.memory`` so that a
refactor renaming the canonical module would be caught.
"""

from __future__ import annotations

import pytest

from importobot.security import memory as memory_module
from importobot.security.memory import SecureMemory
from importobot.security.secure_memory import SecureMemory as FacadeSecureMemory
from importobot.security.types import SecurityError


class TestSourceOfTruthImport:
    """SecureMemory must be importable from memory.py directly."""

    def test_class_is_exported_from_memory_module(self) -> None:
        assert memory_module.__all__ == ["SecureMemory"]

    def test_facade_and_source_resolve_to_same_class(self) -> None:
        # The facade is a thin re-export — identity must hold so that
        # `isinstance(x, FacadeSecureMemory)` works for objects produced
        # via the source path and vice versa.
        assert SecureMemory is FacadeSecureMemory


class TestConstructorInputValidation:
    """Type validation is enforced at the source-module level."""

    def test_bytes_input_accepted(self) -> None:
        mem = SecureMemory(b"hello")
        assert mem.size() == 5
        assert mem.reveal() == b"hello"

    def test_bytearray_input_accepted(self) -> None:
        # Documented to also accept bytearray.
        mem = SecureMemory(bytearray(b"hello"))
        assert mem.size() == 5

    @pytest.mark.parametrize("bad", ["string", 42, None, [1, 2, 3], (1, 2)])
    def test_non_bytes_input_raises_security_error(self, bad: object) -> None:
        with pytest.raises(SecurityError):
            SecureMemory(bad)  # type: ignore[arg-type]


class TestLargeBufferChecksumPath:
    """The >=4096 byte branch in _calculate_checksum is otherwise hard to
    exercise from public APIs."""

    def test_large_buffer_round_trip(self) -> None:
        # 5 KiB exercises the iteration loop inside _calculate_checksum.
        payload = b"x" * 5120
        mem = SecureMemory(payload)
        try:
            assert mem.size() == 5120
            assert mem.reveal() == payload
            assert mem.verify_integrity() is True
        finally:
            mem.zeroize()


class TestReprPrivacy:
    """repr/str must never reveal protected bytes."""

    def test_repr_shows_size_and_status_only(self) -> None:
        mem = SecureMemory(b"top-secret-token")
        rendered = repr(mem)
        assert "top-secret" not in rendered
        assert "token" not in rendered
        assert "size=16" in rendered

    def test_str_matches_repr(self) -> None:
        # __str__ is aliased to __repr__ on the class.
        mem = SecureMemory(b"x")
        assert str(mem) == repr(mem)
