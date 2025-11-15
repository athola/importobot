"""Tests for enhanced APIIngestConfig security features."""

from __future__ import annotations

from pathlib import Path

import pytest

from importobot.config import APIIngestConfig, _mask
from importobot.medallion.interfaces.enums import SupportedFormat
from importobot.security.secure_memory import SecureString, SecurityError

VALID_TOKEN_A = "token_value_alpha_1234"
VALID_TOKEN_B = "token_value_beta_5678"
VALID_TOKEN_C = "token_value_gamma_9012"
STRIPE_TEST_KEY = "sk_live_" + "51H1234567890abcdef1234567890abcdef12345678"
***REMOVED*** = "ghp_" + "1234567890abcdef1234567890abcdef12345678"
***REMOVED*** = "xoxb-" + "1234567890-1234567890-abcd1234abcd1234"
AWS_TEST_KEY = "AKIA" + "IOSFODNN7Z9PQLR"


class TestAPIIngestConfigSecurity:
    """Test security enhancements to APIIngestConfig."""

    def test_init_with_secure_strings(self) -> None:
        """Test initialization with SecureString tokens."""
        tokens = [SecureString(VALID_TOKEN_A), SecureString(VALID_TOKEN_B)]

        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=tokens,
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        assert len(config.tokens) == 2
        assert config.tokens[0].value == VALID_TOKEN_A  # type: ignore
        assert config.tokens[1].value == VALID_TOKEN_B  # type: ignore

    def test_init_with_string_tokens_conversion(self) -> None:
        """Test automatic conversion of string tokens to SecureString."""
        tokens = [VALID_TOKEN_A, VALID_TOKEN_B]

        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=tokens,  # Type: list[str]
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        # Should be converted to SecureString
        assert all(isinstance(token, SecureString) for token in config.tokens)
        assert isinstance(config.tokens[0], SecureString)
        assert isinstance(config.tokens[1], SecureString)
        assert config.tokens[0].value == VALID_TOKEN_A
        assert config.tokens[1].value == VALID_TOKEN_B

    def test_token_security_validation_length(self) -> None:
        """Test token validation rejects short tokens."""
        tokens = [SecureString("short")]  # Less than 16 chars

        with pytest.raises(SecurityError, match=r"Token 1 too short.*min 16 chars"):
            APIIngestConfig(
                fetch_format=SupportedFormat.ZEPHYR,
                api_url="https://example.com",
                tokens=tokens,
                user=None,
                project_name=None,
                project_id=None,
                output_dir=Path("/tmp"),
                max_concurrency=None,
                insecure=False,
            )

    def test_token_security_validation_insecure_patterns(self) -> None:
        """Test token validation rejects insecure patterns."""
        insecure_tokens = [
            "password_secret_value_123",  # Contains "password"
            "api_key_value_secure_456",  # Contains "key"
            "test_auth_token_active",  # Contains "test"
            "demo_access_code_secure",  # Contains "demo"
            "example_secret_payload",  # Contains "example"
        ]

        for insecure_token in insecure_tokens:
            with pytest.raises(
                SecurityError, match="Token 1 contains insecure indicator"
            ):
                APIIngestConfig(
                    fetch_format=SupportedFormat.ZEPHYR,
                    api_url="https://example.com",
                    tokens=[SecureString(insecure_token)],
                    user=None,
                    project_name=None,
                    project_id=None,
                    output_dir=Path("/tmp"),
                    max_concurrency=None,
                    insecure=False,
                )

    def test_placeholder_tokens_rejected(self) -> None:
        """Placeholder values such as 'token' should be rejected."""
        placeholder_values = ["token", "api-token", "bearer_token"]

        for placeholder in placeholder_values:
            with pytest.raises(SecurityError, match="placeholder value"):
                APIIngestConfig(
                    fetch_format=SupportedFormat.ZEPHYR,
                    api_url="https://example.com",
                    tokens=[SecureString(placeholder)],
                    user=None,
                    project_name=None,
                    project_id=None,
                    output_dir=Path("/tmp"),
                    max_concurrency=None,
                    insecure=False,
                )

    def test_tokens_with_token_substring_allowed(self) -> None:
        """Legitimate tokens that include the word 'token' should pass validation."""
        token_value = "cli-token-abcdef1234567890"

        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=[SecureString(token_value)],
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        assert isinstance(config.tokens[0], SecureString)
        assert config.tokens[0].value == token_value

    def test_token_security_validation_insufficient_entropy(self) -> None:
        """Test token validation rejects low-entropy tokens."""
        low_entropy_tokens = [
            "aaaaaaaaaaaaaaaa",  # All same character
            "1111111111111111",  # All same character
            "abababababababab",  # Only two unique characters
        ]

        for low_entropy_token in low_entropy_tokens:
            with pytest.raises(SecurityError, match="insufficient entropy"):
                APIIngestConfig(
                    fetch_format=SupportedFormat.ZEPHYR,
                    api_url="https://example.com",
                    tokens=[SecureString(low_entropy_token)],
                    user=None,
                    project_name=None,
                    project_id=None,
                    output_dir=Path("/tmp"),
                    max_concurrency=None,
                    insecure=False,
                )

    def test_token_security_validation_multiple_tokens(self) -> None:
        """Test token validation with multiple tokens."""
        # Mix of valid and invalid tokens
        tokens = [
            SecureString("valid_secure_token_12345"),  # Valid
            SecureString("short"),  # Invalid - too short
        ]

        with pytest.raises(SecurityError, match="Token 2 too short"):
            APIIngestConfig(
                fetch_format=SupportedFormat.ZEPHYR,
                api_url="https://example.com",
                tokens=tokens,
                user=None,
                project_name=None,
                project_id=None,
                output_dir=Path("/tmp"),
                max_concurrency=None,
                insecure=False,
            )

    def test_get_token_by_index(self) -> None:
        """Test retrieving token by index."""
        # Use valid tokens that pass security validation
        tokens = [
            SecureString("sk_live_" + "1234567890abcdef12"),
            SecureString(***REMOVED***),
            SecureString(***REMOVED***),
        ]

        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=tokens,
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        assert config.get_token(0) == "sk_live_" + "1234567890abcdef12"
        assert config.get_token(1) == ***REMOVED***
        assert config.get_token(2) == ***REMOVED***

    def test_get_token_index_out_of_range(self) -> None:
        """Test retrieving token with invalid index."""
        tokens = [SecureString(VALID_TOKEN_A)]

        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=tokens,
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        with pytest.raises(IndexError, match="Token index 5 out of range"):
            config.get_token(5)

    def test_get_all_tokens(self) -> None:
        """Test retrieving all tokens."""
        tokens = [SecureString(VALID_TOKEN_A), SecureString(VALID_TOKEN_B)]

        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=tokens,
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        all_tokens = config.get_all_tokens()
        assert all_tokens == [VALID_TOKEN_A, VALID_TOKEN_B]
        assert isinstance(all_tokens, list)
        assert all(isinstance(token, str) for token in all_tokens)

    def test_add_token(self) -> None:
        """Test adding a new token."""
        initial_tokens = [SecureString("initial_token_value_123")]

        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=initial_tokens,
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        assert len(config.tokens) == 1

        # Add a valid new token
        config.add_token("new_secure_token_12345")

        assert len(config.tokens) == 2
        token = config.tokens[1]
        assert isinstance(token, SecureString)
        assert token.value == "new_secure_token_12345"
        assert not token.is_locked()

    def test_mixed_token_conversion_preserves_secure_strings(self) -> None:
        """Ensure legacy strings convert without corrupting SecureString entries."""
        legacy_token = "legacycred_abcdefghijkl"
        secure_token = SecureString("alreadysecurecredentialvalue")

        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=[legacy_token, secure_token],  # type: ignore[arg-type]
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        assert len(config.tokens) == 2
        # Legacy string should be converted into a SecureString with the same value
        assert config.tokens[0].value == legacy_token  # type: ignore
        # Pre-existing SecureString should retain its original secret
        assert config.tokens[1].value == secure_token.value  # type: ignore

    def test_add_invalid_token(self) -> None:
        """Test adding an invalid token fails."""
        initial_tokens = [SecureString("valid_token_123456")]

        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=initial_tokens,
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        # Try to add invalid token
        with pytest.raises(SecurityError):
            config.add_token("short")  # Too short

        # Original token should still be there
        assert len(config.tokens) == 1
        assert config.tokens[0].value == "valid_token_123456"  # type: ignore

    def test_cleanup_on_destruction(self) -> None:
        """Test that tokens are cleaned up on destruction."""
        tokens = [SecureString("cleanup_alpha_value_01")]

        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=tokens,
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        # Tokens should not be locked initially
        assert not config.tokens[0].is_locked()  # type: ignore

        # Delete the config (trigger cleanup)
        del config

        # Note: We can't easily test that cleanup actually happened
        # since we no longer have references to the tokens
        # This is more of a smoke test to ensure no exceptions are raised

    def test_config_with_no_tokens(self) -> None:
        """Test config with empty token list."""
        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=[],
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        assert config.tokens == []
        assert config.get_all_tokens() == []

        with pytest.raises(IndexError):
            config.get_token(0)


class TestMaskingFunction:
    """Test the updated _mask function."""

    def test_mask_string_tokens(self) -> None:
        """Test masking regular string tokens."""
        tokens = [VALID_TOKEN_A, VALID_TOKEN_B, VALID_TOKEN_C]
        masked = _mask(tokens)

        assert masked == "***, ***, ***"

    def test_mask_secure_string_tokens(self) -> None:
        """Test masking SecureString tokens."""
        tokens = [SecureString("secret1"), SecureString("secret2")]
        masked = _mask(tokens)

        assert masked == "***, ***"

    def test_mask_mixed_tokens(self) -> None:
        """Test masking mixed token types."""
        tokens: list[str | SecureString] = [
            SecureString("secret_value_one_123"),
            VALID_TOKEN_B,
            SecureString("secret_value_three_789"),
        ]
        masked = _mask(tokens)

        # Should count all tokens regardless of type
        assert masked == "***, ***, ***"

    def test_mask_empty_tokens(self) -> None:
        """Test masking empty token list."""
        assert _mask([]) == "***"
        assert _mask(None) == "***"

    def test_mask_single_token(self) -> None:
        """Test masking single token."""
        secure_tokens = [SecureString("single_secret")]
        masked = _mask(secure_tokens)

        assert masked == "***"

        string_tokens = ["single_string"]
        masked = _mask(string_tokens)
        assert masked == "***"


class TestTokenSecurityValidation:
    """Detailed tests for token security validation."""

    def test_case_insensitive_pattern_detection(self) -> None:
        """Test that insecure pattern detection is case-insensitive."""
        insecure_variations = [
            "MyTOKEN1234567890",
            "PASSWORD_secret_alpha",
            "Api_Key_Value_guard99",
            "TEST_ACCESS_MODE999",
            "DEMO_MODE_PROFILE77",
            "EXAMPLE_VALUE_ALPHA",
            "SAMPLE_DATA_BUFFER",
            "DEFAULT_CONFIG_ZONE",
            "TEMP_SECRET_ACCESS",
            "TEMPORARY_ACCESS_ZONE",
        ]

        for insecure_token in insecure_variations:
            with pytest.raises(SecurityError, match="contains insecure indicator"):
                APIIngestConfig(
                    fetch_format=SupportedFormat.ZEPHYR,
                    api_url="https://example.com",
                    tokens=[SecureString(insecure_token)],
                    user=None,
                    project_name=None,
                    project_id=None,
                    output_dir=Path("/tmp"),
                    max_concurrency=None,
                    insecure=False,
                )

    def test_valid_tokens_acceptance(self) -> None:
        """Test that valid tokens are accepted."""
        valid_tokens = [
            STRIPE_TEST_KEY,
            ***REMOVED***,
            ***REMOVED***,
            "random_string_12345_abcd",  # Generic but valid
            "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",  # Hex-like
        ]

        for valid_token in valid_tokens:
            # Should not raise any exceptions
            config = APIIngestConfig(
                fetch_format=SupportedFormat.ZEPHYR,
                api_url="https://example.com",
                tokens=[SecureString(valid_token)],
                user=None,
                project_name=None,
                project_id=None,
                output_dir=Path("/tmp"),
                max_concurrency=None,
                insecure=False,
            )
            token = config.tokens[0]
            assert isinstance(token, SecureString)
            assert token.value == valid_token

    def test_unicode_token_validation(self) -> None:
        """Test token validation with Unicode characters."""
        unicode_token = "unîcode_token_12345_测试"  # Contains Unicode

        # Should be accepted if long enough and doesn't contain insecure patterns
        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=[SecureString(unicode_token)],
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )
        token = config.tokens[0]
        assert isinstance(token, SecureString)
        assert token.value == unicode_token

    def test_minimum_unique_characters(self) -> None:
        """Test minimum unique characters requirement."""
        # Exactly 4 unique characters should pass
        token_with_4_unique = "abcdabcdabcdabcd"
        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://example.com",
            tokens=[SecureString(token_with_4_unique)],
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )
        token = config.tokens[0]
        assert isinstance(token, SecureString)
        assert token.value == token_with_4_unique

        # Only 3 unique characters should fail
        token_with_3_unique = "aaabbbcccaaabbbccc"
        with pytest.raises(SecurityError, match="insufficient entropy"):
            APIIngestConfig(
                fetch_format=SupportedFormat.ZEPHYR,
                api_url="https://example.com",
                tokens=[SecureString(token_with_3_unique)],
                user=None,
                project_name=None,
                project_id=None,
                output_dir=Path("/tmp"),
                max_concurrency=None,
                insecure=False,
            )


class TestAPIIngestConfigIntegration:
    """Integration tests for APIIngestConfig with security features."""

    def test_real_world_token_scenarios(self) -> None:
        """Test real-world token scenarios."""
        real_tokens = {
            "stripe": STRIPE_TEST_KEY,
            "github": ***REMOVED***,
            "slack": ***REMOVED***,
            "aws": AWS_TEST_KEY,  # AWS access key format
        }

        for service, token in real_tokens.items():
            config = APIIngestConfig(
                fetch_format=SupportedFormat.ZEPHYR,
                api_url=f"https://{service}.example.com",
                tokens=[SecureString(token)],
                user=None,
                project_name=None,
                project_id=None,
                output_dir=Path("/tmp"),
                max_concurrency=None,
                insecure=False,
            )
            token_obj = config.tokens[0]
            assert isinstance(token_obj, SecureString)
            assert token_obj.value == token

    def test_multiple_service_tokens(self) -> None:
        """Test config with multiple service tokens."""
        tokens = [
            STRIPE_TEST_KEY,
            ***REMOVED***,
            ***REMOVED***,
        ]

        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://api.example.com",
            tokens=[SecureString(token) for token in tokens],
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        retrieved_tokens = config.get_all_tokens()
        assert retrieved_tokens == tokens

    def test_config_lifecycle_with_tokens(self) -> None:
        """Test complete config lifecycle with secure token handling."""
        initial_token = "initial_secure_token_12345678"

        # Create config
        config = APIIngestConfig(
            fetch_format=SupportedFormat.ZEPHYR,
            api_url="https://api.example.com",
            tokens=[SecureString(initial_token)],
            user=None,
            project_name=None,
            project_id=None,
            output_dir=Path("/tmp"),
            max_concurrency=None,
            insecure=False,
        )

        # Add more tokens
        config.add_token("second_token_12345678")
        config.add_token("third_token_12345678")

        # Retrieve tokens
        all_tokens = config.get_all_tokens()
        assert len(all_tokens) == 3
        assert all_tokens[0] == initial_token

        # Access individual tokens
        assert config.get_token(1) == "second_token_12345678"
        assert config.get_token(2) == "third_token_12345678"

        # Verify all tokens are still secure
        for token in config.tokens:
            assert isinstance(token, SecureString)
            assert not token.is_locked()

    def test_error_handling_in_validation(self) -> None:
        """Test error handling during token validation."""

        # Create a token that will cause an exception during validation
        class ProblematicSecureString(SecureString):
            @property
            def value(self) -> str:
                raise RuntimeError("Simulated access error")

        with pytest.raises(SecurityError, match="Failed to validate token 1"):
            APIIngestConfig(
                fetch_format=SupportedFormat.ZEPHYR,
                api_url="https://example.com",
                tokens=[ProblematicSecureString("token")],  # type: ignore[arg-type]
                user=None,
                project_name=None,
                project_id=None,
                output_dir=Path("/tmp"),
                max_concurrency=None,
                insecure=False,
            )
