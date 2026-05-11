"""Tests for enhanced international language support in SecureString."""

from __future__ import annotations

import pytest

from importobot.security.secure_memory import (
    SecureString,
    SecurityError,
    StringEncoding,
    UnicodeNormalization,
    create_arabic_secure_string,
    create_chinese_secure_string,
    create_japanese_secure_string,
    create_korean_secure_string,
    create_multilingual_secure_string,
    create_russian_secure_string,
    detect_string_encoding,
    normalize_unicode_string,
    secure_compare_strings,
    validate_language_characters,
)


class TestStringEncodingDetection:
    """Test string encoding detection functionality."""

    def test_ascii_detection(self) -> None:
        """Test detection of ASCII-only strings."""
        ascii_text = "Hello, World! 123"
        encoding = detect_string_encoding(ascii_text)
        assert encoding == StringEncoding.ASCII

    def test_unicode_detection(self) -> None:
        """Test detection of Unicode strings."""
        unicode_text = "Héllo 🌍 Wörld"
        encoding = detect_string_encoding(unicode_text)
        assert encoding == StringEncoding.UTF8

    def test_japanese_detection(self) -> None:
        """Test detection of Japanese text."""
        japanese_text = "こんにちは世界"
        encoding = detect_string_encoding(japanese_text)
        assert encoding in [
            StringEncoding.SHIFT_JIS,
            StringEncoding.UTF8,
            StringEncoding.EUC_JP,
        ]

    def test_chinese_detection(self) -> None:
        """Test detection of Chinese text."""
        chinese_text = "你好世界"
        encoding = detect_string_encoding(chinese_text)
        assert encoding in [
            StringEncoding.GBK,
            StringEncoding.UTF8,
            StringEncoding.BIG5,
        ]

    def test_cyrillic_detection(self) -> None:
        """Test detection of Cyrillic text."""
        cyrillic_text = "Привет мир"
        encoding = detect_string_encoding(cyrillic_text)
        assert encoding == StringEncoding.KOI8_R

    def test_preferred_encoding(self) -> None:
        """Test preferred encoding specification."""
        text = "Hello, World!"
        encoding = detect_string_encoding(text, preferred_encoding=StringEncoding.UTF8)
        assert encoding == StringEncoding.UTF8

    def test_unsupported_preferred_encoding(self) -> None:
        """Test fallback when preferred encoding doesn't support the text."""
        # Use Japanese text with ASCII preferred encoding (should fallback)
        japanese_text = "こんにちは"
        encoding = detect_string_encoding(
            japanese_text, preferred_encoding=StringEncoding.ASCII
        )
        assert encoding != StringEncoding.ASCII


class TestUnicodeNormalization:
    """Test Unicode normalization functionality."""

    def test_nfc_normalization(self) -> None:
        """Test NFC normalization."""
        # Use combining characters that should be composed
        text = "e\u0301"  # e + combining acute accent
        normalized = normalize_unicode_string(text, UnicodeNormalization.NFC)
        assert normalized == "é"

    def test_nfd_normalization(self) -> None:
        """Test NFD normalization."""
        text = "é"  # Already composed character
        normalized = normalize_unicode_string(text, UnicodeNormalization.NFD)
        assert normalized == "e\u0301"  # Should be decomposed

    def test_nfkc_normalization(self) -> None:
        """Test NFKC normalization."""
        text = "K"  # Kelvin sign (compatibility)
        normalized = normalize_unicode_string(text, UnicodeNormalization.NFKC)
        assert normalized == "K"  # Should normalize to regular K

    def test_nfkd_normalization(self) -> None:
        """Test NFKD normalization."""
        text = "K"  # Kelvin sign (compatibility)
        normalized = normalize_unicode_string(text, UnicodeNormalization.NFKD)
        assert normalized == "K"  # Should normalize and decompose

    def test_normalization_idempotency(self) -> None:
        """Test that normalization is idempotent."""
        text = "café"
        normalized = normalize_unicode_string(text, UnicodeNormalization.NFC)
        normalized_twice = normalize_unicode_string(
            normalized, UnicodeNormalization.NFC
        )
        assert normalized == normalized_twice


class TestLanguageValidation:
    """Test language character validation."""

    def test_english_validation(self) -> None:
        """Test English character validation."""
        text = "Hello, World!"
        result = validate_language_characters(text, ["en"])
        assert result["valid"] is True
        assert "en" in result["detected_languages"]
        assert len(result["unexpected_chars"]) == 0

    def test_japanese_validation(self) -> None:
        """Test Japanese character validation."""
        text = "こんにちは"
        result = validate_language_characters(text, ["ja"])
        assert result["valid"] is True
        assert "ja" in result["detected_languages"]
        assert len(result["unexpected_chars"]) == 0

    def test_mixed_language_validation(self) -> None:
        """Test mixed language validation."""
        text = "Hello こんにちは"
        result = validate_language_characters(text, ["en", "ja"])
        assert result["valid"] is True
        assert "en" in result["detected_languages"]
        assert "ja" in result["detected_languages"]

    def test_unsupported_character_validation(self) -> None:
        """Test validation with unsupported characters."""
        text = "Hello العربية"  # English + Arabic
        result = validate_language_characters(text, ["en"])  # Only allow English
        assert result["valid"] is False
        assert "en" in result["detected_languages"]
        assert "ar" in result["detected_languages"]
        assert result["unexpected_count"] > 0

    def test_no_language_restriction(self) -> None:
        """Test validation with no language restrictions."""
        text = "Hello こんにちは العربية مرحبا"
        result = validate_language_characters(text, None)
        assert result["valid"] is True
        assert result["detected_languages"] == ["all"]


class TestEnhancedSecureString:
    """Test enhanced SecureString with Unicode support."""

    def test_basic_unicode_string(self) -> None:
        """Test basic Unicode string creation."""
        text = "Héllo 🌍 Wörld"
        secure_str = SecureString(text)

        assert secure_str.value == text
        assert secure_str.size() == len(text)
        assert secure_str.encoding == StringEncoding.UTF8
        assert secure_str.normalization == UnicodeNormalization.NFC

    def test_encoding_specification(self) -> None:
        """Test specifying encoding explicitly."""
        text = "Hello, World!"
        secure_str = SecureString(text, encoding=StringEncoding.UTF16)

        assert secure_str.value == text
        assert secure_str.encoding == StringEncoding.UTF16
        assert secure_str.byte_length() > len(text.encode("utf-8"))

    def test_normalization_specification(self) -> None:
        """Test specifying Unicode normalization."""
        # Use text with combining characters
        text = "cafe\u0301"  # cafe + combining acute accent
        secure_str = SecureString(text, normalization=UnicodeNormalization.NFC)

        # Should be normalized to composed form
        assert secure_str.value == "café"
        assert secure_str.normalization == UnicodeNormalization.NFC

    def test_language_restriction_success(self) -> None:
        """Test successful language restriction."""
        text = "Hello, World!"
        secure_str = SecureString(text, allowed_languages=["en"])

        assert secure_str.value == text
        assert secure_str.detected_languages() == ["en"]

    def test_language_restriction_failure(self) -> None:
        """Test language restriction failure."""
        text = "Hello العربية"  # English + Arabic

        with pytest.raises(SecurityError, match="unsupported languages"):
            SecureString(text, allowed_languages=["en"])

    def test_multilingual_string(self) -> None:
        """Test multilingual string creation."""
        text = "Hello こんにちは"
        secure_str = SecureString(text, allowed_languages=["en", "ja"])

        assert secure_str.value == text
        detected = set(secure_str.detected_languages())
        assert {"en", "ja"}.issubset(detected)

    def test_encoding_conversion(self) -> None:
        """Test encoding conversion."""
        text = "Hello, World!"
        original = SecureString(text, encoding=StringEncoding.UTF8)

        converted = original.convert_encoding(StringEncoding.UTF16)
        assert converted.value == text
        assert converted.encoding == StringEncoding.UTF16
        assert converted.encoding != original.encoding

    def test_normalization_conversion(self) -> None:
        """Test normalization conversion."""
        # Start with decomposed form
        text = "cafe\u0301"
        original = SecureString(text, normalization=UnicodeNormalization.NFD)

        # Convert to composed form
        converted = original.apply_normalization(UnicodeNormalization.NFC)
        assert converted.value == "café"
        assert converted.normalization == UnicodeNormalization.NFC

    def test_character_info(self) -> None:
        """Test character information analysis."""
        text = "Hello 世界 🌍"
        secure_str = SecureString(text)

        char_info = secure_str.get_char_info()
        assert char_info["total_chars"] == len(text)
        assert char_info["encoding"] == StringEncoding.UTF8.value
        assert char_info["normalization"] == UnicodeNormalization.NFC.value
        assert char_info["byte_length"] > len(text)

        # Should detect multiple character types
        breakdown = char_info["char_breakdown"]
        assert breakdown["ascii"] > 0  # Hello
        assert breakdown["bmp_extended"] > 0  # 世界
        assert breakdown["supplementary"] > 0  # 🌍

    def test_constant_time_comparison_with_normalization(self) -> None:
        """Test constant-time comparison with normalization."""
        # Same text in different normalization forms
        text1 = "café"  # Composed
        text2 = "cafe\u0301"  # Decomposed

        secure1 = SecureString(text1, normalization=UnicodeNormalization.NFC)
        secure2 = SecureString(text2, normalization=UnicodeNormalization.NFD)

        # Should be equal when normalized
        assert secure1.compare_with_normalization(secure2, UnicodeNormalization.NFC)
        assert secure2.compare_with_normalization(secure1, UnicodeNormalization.NFC)

    def test_empty_string_validation(self) -> None:
        """Test empty string validation."""
        with pytest.raises(SecurityError, match="Empty strings cannot be secured"):
            SecureString("")

    def test_invalid_type_validation(self) -> None:
        """Test invalid type validation."""
        with pytest.raises(SecurityError, match="SecureString requires string input"):
            SecureString(123)  # type: ignore[arg-type]


class TestLanguageSpecificHelpers:
    """Test language-specific SecureString creation helpers."""

    def test_japanese_helper(self) -> None:
        """Test Japanese SecureString helper."""
        text = "パスワード"
        secure_str = create_japanese_secure_string(text)

        assert secure_str.value == text
        assert "ja" in secure_str.detected_languages()
        assert secure_str.encoding == StringEncoding.UTF8

    def test_chinese_helper(self) -> None:
        """Test Chinese SecureString helper."""
        text = "密码"
        secure_str = create_chinese_secure_string(text)

        assert secure_str.value == text
        assert "zh" in secure_str.detected_languages()
        assert secure_str.encoding == StringEncoding.UTF8

    def test_korean_helper(self) -> None:
        """Test Korean SecureString helper."""
        text = "비밀번호"
        secure_str = create_korean_secure_string(text)

        assert secure_str.value == text
        assert "ko" in secure_str.detected_languages()
        assert secure_str.encoding == StringEncoding.UTF8

    def test_arabic_helper(self) -> None:
        """Test Arabic SecureString helper."""
        text = "كلمة السر"
        secure_str = create_arabic_secure_string(text)

        assert secure_str.value == text
        assert "ar" in secure_str.detected_languages()
        assert secure_str.encoding == StringEncoding.UTF8

    def test_russian_helper(self) -> None:
        """Test Russian SecureString helper."""
        text = "пароль"
        secure_str = create_russian_secure_string(text)

        assert secure_str.value == text
        assert "ru" in secure_str.detected_languages()
        assert secure_str.encoding == StringEncoding.KOI8_R

    def test_multilingual_helper(self) -> None:
        """Test multilingual SecureString helper."""
        text = "Hello 你好"
        secure_str = create_multilingual_secure_string(text, ["en", "zh"])

        assert secure_str.value == text
        detected = set(secure_str.detected_languages())
        assert {"en", "zh"}.issubset(detected)


class TestSecureComparisonWithNormalization:
    """Test secure string comparison with normalization."""

    def test_comparison_without_normalization(self) -> None:
        """Test comparison without explicit normalization."""
        text = "Hello, World!"
        str1 = SecureString(text)
        str2 = SecureString(text)

        assert secure_compare_strings(str1, str2)

    def test_comparison_with_normalization(self) -> None:
        """Test comparison with explicit normalization."""
        # Same text in different forms
        composed = SecureString("café", normalization=UnicodeNormalization.NFC)
        decomposed = SecureString("cafe\u0301", normalization=UnicodeNormalization.NFD)

        # Should be equal when normalized
        assert secure_compare_strings(composed, decomposed, UnicodeNormalization.NFC)

    def test_comparison_inequality(self) -> None:
        """Test comparison inequality."""
        str1 = SecureString("password1")
        str2 = SecureString("password2")

        assert not secure_compare_strings(str1, str2)

    def test_comparison_invalid_types(self) -> None:
        """Test comparison with invalid types."""
        str1 = SecureString("test")

        with pytest.raises(
            SecurityError, match="Both arguments must be SecureString instances"
        ):
            secure_compare_strings(str1, "regular_string")  # type: ignore[arg-type]


class TestComplexUnicodeScenarios:
    """Test complex Unicode scenarios."""

    def test_emoji_and_symbols(self) -> None:
        """Test handling of emojis and symbols."""
        text = "Password 🔐🔑🛡️"
        secure_str = SecureString(text)

        assert secure_str.value == text
        char_info = secure_str.get_char_info()
        assert (
            char_info["char_breakdown"]["supplementary"] > 0
        )  # Should have supplementary characters

    def test_right_to_left_text(self) -> None:
        """Test right-to-left text (Arabic, Hebrew)."""
        text = "مرحبا بالعالم"
        secure_str = SecureString(text, allowed_languages=["ar"])

        assert secure_str.value == text
        assert "ar" in secure_str.detected_languages()

    def test_mixed_direction_text(self) -> None:
        """Test mixed direction text."""
        text = "Hello مرحبا こんにちは"
        secure_str = SecureString(text, allowed_languages=["en", "ar", "ja"])

        assert secure_str.value == text
        detected = set(secure_str.detected_languages())
        assert {"en", "ar", "ja"}.issubset(detected)

    def test_very_long_unicode_text(self) -> None:
        """Test long Unicode text handling."""
        # Create a long multilingual string
        parts = [
            "English text with numbers 1234567890 and symbols !@#$%^&*()",
            "中文文本包含数字1234567890和符号!@#￥%……&*()",
            "日本語のテキスト数字1234567890記号!@#￥%…&*()",
        ]
        text = " ".join(parts)
        secure_str = SecureString(text)

        assert secure_str.value == text
        assert secure_str.size() == len(text)
        # Should handle long Unicode text properly
        assert secure_str.byte_length() >= len(
            text
        )  # At least as many bytes as characters

    def test_zero_width_characters(self) -> None:
        """Test handling of zero-width characters."""
        text = "password\u200b\u200c\u200d"  # Zero-width characters
        secure_str = SecureString(text)

        assert secure_str.value == text
        assert secure_str.size() == len(text)

    def test_control_characters(self) -> None:
        """Test handling of control characters."""
        text = "password\t\n\r"  # Tab, newline, carriage return
        secure_str = SecureString(text)

        assert secure_str.value == text
        assert secure_str.size() == len(text)


class TestBackwardCompatibility:
    """Test backward compatibility with existing SecureString usage."""

    def test_simple_creation_still_works(self) -> None:
        """Test that simple creation still works."""
        text = "simple password"
        secure_str = SecureString(text)

        assert secure_str.value == text
        assert secure_str.encoding in [
            StringEncoding.UTF8,
            StringEncoding.ASCII,
        ]  # Both are valid
        assert secure_str.normalization == UnicodeNormalization.NFC

    def test_existing_methods_still_work(self) -> None:
        """Test that existing methods still work as before."""
        text = "test password"
        secure_str = SecureString(text)

        # Original methods should still work
        assert secure_str.size() == len(text)
        assert secure_str.byte_length() == len(text.encode("utf-8"))
        assert not secure_str.is_locked()

        # Context manager should still work
        with secure_str:
            assert secure_str.value == text
        assert secure_str.is_locked()

    def test_equality_comparison_still_works(self) -> None:
        """Test that equality comparison still works."""
        text = "password"
        str1 = SecureString(text)
        str2 = SecureString(text)

        assert str1 == str2
        assert hash(str1) == hash(str2)
