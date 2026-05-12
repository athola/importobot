"""Direct tests for SecureString and language-helper convenience functions.

Behavioural coverage of basic SecureString operations (init, value,
zeroize, equality, context manager) lives in
``tests/unit/security/test_secure_memory.py`` and
``tests/unit/security/test_international_strings.py``. These tests
pin the *source-of-truth path* in ``importobot.security.secure_string``
and the methods that the existing facade-driven tests don't exercise
(``convert_encoding``, ``apply_normalization``,
``compare_with_normalization``, ``get_char_info``, hashing).
"""

from __future__ import annotations

import pytest

from importobot.security import secure_string as ss_mod
from importobot.security.secure_memory import SecureString as FacadeSecureString
from importobot.security.secure_string import (
    SecureString,
    create_arabic_secure_string,
    create_chinese_secure_string,
    create_japanese_secure_string,
    create_korean_secure_string,
    create_multilingual_secure_string,
    create_russian_secure_string,
    create_secure_string,
    secure_compare_strings,
)
from importobot.security.types import (
    SecurityError,
    StringEncoding,
    UnicodeNormalization,
)


class TestSourceOfTruthImport:
    """secure_string.py is the canonical home for SecureString."""

    def test_facade_and_source_resolve_to_same_class(self) -> None:
        assert SecureString is FacadeSecureString

    def test_all_lists_documented_exports(self) -> None:
        assert set(ss_mod.__all__) == {
            "SecureString",
            "create_arabic_secure_string",
            "create_chinese_secure_string",
            "create_japanese_secure_string",
            "create_korean_secure_string",
            "create_multilingual_secure_string",
            "create_russian_secure_string",
            "create_secure_string",
            "secure_compare_strings",
        }


class TestEncodingAndNormalizationProperties:
    """Properties expose construction-time settings."""

    def test_encoding_property_returns_set_encoding(self) -> None:
        s = SecureString("hello", encoding=StringEncoding.UTF8)
        assert s.encoding == StringEncoding.UTF8

    def test_normalization_property_returns_set_normalization(self) -> None:
        s = SecureString("hello", normalization=UnicodeNormalization.NFD)
        assert s.normalization == UnicodeNormalization.NFD

    def test_size_returns_char_count_byte_length_returns_byte_count(self) -> None:
        # ASCII: char_count == byte_count when encoded as UTF-8.
        s = SecureString("hello", encoding=StringEncoding.UTF8)
        assert s.size() == 5
        assert s.byte_length() == 5

    def test_size_and_byte_length_differ_for_multibyte_utf8(self) -> None:
        # The kanji '日' takes 3 bytes in UTF-8 but is 1 character.
        s = SecureString("日", encoding=StringEncoding.UTF8)
        assert s.size() == 1
        assert s.byte_length() == 3


class TestConvertEncoding:
    """convert_encoding produces a new SecureString with the same value."""

    def test_round_trip_preserves_value(self) -> None:
        original = SecureString("hello", encoding=StringEncoding.UTF8)
        try:
            converted = original.convert_encoding(StringEncoding.LATIN1)
            try:
                assert converted.value == "hello"
                assert converted.encoding == StringEncoding.LATIN1
                # The byte length changes when the encoding differs in
                # bytes-per-character, but for an ASCII string both
                # encodings agree.
                assert converted.byte_length() == 5
            finally:
                converted.zeroize()
        finally:
            original.zeroize()

    def test_conversion_does_not_mutate_original(self) -> None:
        original = SecureString("hello", encoding=StringEncoding.UTF8)
        try:
            _ = original.convert_encoding(StringEncoding.LATIN1)
            # Original retains its encoding and value after the new
            # instance is constructed.
            assert original.encoding == StringEncoding.UTF8
            assert original.value == "hello"
        finally:
            original.zeroize()


class TestApplyNormalization:
    """apply_normalization returns a new SecureString with the new form."""

    def test_changing_normalization_preserves_value(self) -> None:
        original = SecureString("cafe", normalization=UnicodeNormalization.NFC)
        try:
            converted = original.apply_normalization(UnicodeNormalization.NFD)
            try:
                assert converted.normalization == UnicodeNormalization.NFD
                # For ASCII, both NFC and NFD produce the same bytes.
                assert converted.value == "cafe"
            finally:
                converted.zeroize()
        finally:
            original.zeroize()


class TestCompareWithNormalization:
    """compare_with_normalization handles equivalent-but-differing forms."""

    def test_equal_strings_compare_equal(self) -> None:
        a = SecureString("hello")
        b = SecureString("hello")
        try:
            assert a.compare_with_normalization(b) is True
        finally:
            a.zeroize()
            b.zeroize()

    def test_different_strings_compare_not_equal(self) -> None:
        a = SecureString("hello")
        b = SecureString("world")
        try:
            assert a.compare_with_normalization(b) is False
        finally:
            a.zeroize()
            b.zeroize()

    def test_compare_with_non_secure_string_returns_false(self) -> None:
        a = SecureString("hello")
        try:
            # The contract is: if other is not a SecureString, return
            # False (not raise) — keeps the call site simple.
            wrong_type: object = "hello"
            result = a.compare_with_normalization(wrong_type)  # type: ignore[arg-type]
            assert result is False
        finally:
            a.zeroize()


class TestGetCharInfoAndLanguages:
    """get_char_info reports the encoded shape; detected_languages reflects content."""

    def test_char_info_ascii_breakdown(self) -> None:
        s = SecureString("hello")
        try:
            info = s.get_char_info()
            assert info["total_chars"] == 5
            assert info["byte_length"] == 5
            assert info["char_breakdown"]["ascii"] == 5
            assert info["char_breakdown"]["bmp_extended"] == 0
            assert "languages" in info
        finally:
            s.zeroize()

    def test_detected_languages_returns_allowed_when_set(self) -> None:
        s = SecureString("hello", allowed_languages=["en"])
        try:
            # When allowed_languages is provided, detected_languages
            # echoes that list rather than rerunning detection.
            assert s.detected_languages() == ["en"]
        finally:
            s.zeroize()


class TestHashing:
    """Hash equality must agree with __eq__ for non-zeroized instances."""

    def test_equal_strings_have_equal_hashes(self) -> None:
        a = SecureString("hello")
        b = SecureString("hello")
        try:
            assert a == b
            assert hash(a) == hash(b)
        finally:
            a.zeroize()
            b.zeroize()

    def test_zeroized_string_has_stable_hash(self) -> None:
        a = SecureString("hello")
        a.zeroize()
        # The hash must remain well-defined after zeroization so the
        # instance does not crash hash-based containers it may still
        # live in.
        assert isinstance(hash(a), int)


class TestSecureCompareStringsWrapper:
    """The free function delegates to SecureString.compare_with_normalization."""

    def test_explicit_normalization_uses_compare_with_normalization(self) -> None:
        a = SecureString("hello")
        b = SecureString("hello")
        try:
            assert secure_compare_strings(a, b, UnicodeNormalization.NFC) is True
        finally:
            a.zeroize()
            b.zeroize()

    def test_without_normalization_falls_back_to_eq(self) -> None:
        a = SecureString("hello")
        b = SecureString("world")
        try:
            assert secure_compare_strings(a, b) is False
        finally:
            a.zeroize()
            b.zeroize()

    def test_non_securestring_arg_raises(self) -> None:
        a = SecureString("hello")
        try:
            with pytest.raises(SecurityError):
                secure_compare_strings(a, "hello")  # type: ignore[arg-type]
        finally:
            a.zeroize()


class TestLanguageSpecificHelpers:
    """Each language helper uses UTF-8 except Russian which uses KOI8-R."""

    def test_japanese_helper_uses_utf8(self) -> None:
        s = create_japanese_secure_string("こんにちは")
        try:
            assert s.encoding == StringEncoding.UTF8
            assert s.value == "こんにちは"
        finally:
            s.zeroize()

    def test_chinese_helper_uses_utf8(self) -> None:
        s = create_chinese_secure_string("你好")
        try:
            assert s.encoding == StringEncoding.UTF8
            assert s.value == "你好"
        finally:
            s.zeroize()

    def test_korean_helper_uses_utf8(self) -> None:
        s = create_korean_secure_string("안녕")
        try:
            assert s.encoding == StringEncoding.UTF8
            assert s.value == "안녕"
        finally:
            s.zeroize()

    def test_arabic_helper_uses_utf8(self) -> None:
        s = create_arabic_secure_string("مرحبا")
        try:
            assert s.encoding == StringEncoding.UTF8
            assert s.value == "مرحبا"
        finally:
            s.zeroize()

    def test_russian_helper_uses_koi8r_encoding(self) -> None:
        # KOI8-R is the documented choice for Russian helpers; encoding
        # choice affects byte_length and any export/serialise paths.
        s = create_russian_secure_string("Привет")
        try:
            assert s.encoding == StringEncoding.KOI8_R
            assert s.value == "Привет"
        finally:
            s.zeroize()


class TestCreateMultilingualSecureString:
    """The multilingual factory drives the per-language helpers above."""

    def test_creates_with_explicit_language_list(self) -> None:
        s = create_multilingual_secure_string("hello", languages=["en"])
        try:
            assert s.value == "hello"
            assert s.detected_languages() == ["en"]
        finally:
            s.zeroize()

    def test_disallowed_language_raises_security_error(self) -> None:
        # Russian Cyrillic should not pass language validation when only
        # English is allowed.
        with pytest.raises(SecurityError):
            create_multilingual_secure_string("Привет", languages=["en"])


class TestCreateSecureStringValidationEdge:
    """Edges already partially tested in test_secure_memory; lock the rest."""

    def test_non_string_input_raises(self) -> None:
        with pytest.raises(SecurityError):
            create_secure_string(42)  # type: ignore[arg-type]

    def test_empty_string_raises(self) -> None:
        with pytest.raises(SecurityError):
            create_secure_string("")
