"""Tests for enhanced credential pattern detection."""

from __future__ import annotations

import re
import tempfile
import threading
import time
from pathlib import Path

import pytest

from importobot.security import credential_patterns
from importobot.security.credential_patterns import (
    CredentialPattern,
    CredentialPatternRegistry,
    CredentialRegistryContext,
    CredentialType,
    credential_registry_context,
    get_credential_registry,
    get_current_registry,
    scan_for_credentials,
)

STRIPE_TEST_KEY = "sk_live_" + "1234567890abcdef1234567890"


class TestCredentialPattern:
    """Test individual credential pattern functionality."""

    def test_pattern_creation(self) -> None:
        """Test credential pattern creation."""
        pattern = CredentialPattern(
            credential_type=CredentialType.API_KEY,
            regex_pattern=re.compile(r"api_key:\s*(\w+)"),
            confidence=0.9,
            context_keywords=["api", "key"],
            description="API key pattern",
            remediation="Use environment variables",
            examples=["api_key: abc123"],
        )

        assert pattern.credential_type == CredentialType.API_KEY
        assert pattern.confidence == 0.9
        assert pattern.description == "API key pattern"

    def test_pattern_matching(self) -> None:
        """Test pattern matching functionality."""
        pattern = CredentialPattern(
            credential_type=CredentialType.PASSWORD,
            regex_pattern=re.compile(r"password:\s*(\w+)", re.IGNORECASE),
            confidence=0.95,
            context_keywords=["password"],
            description="Password pattern",
            remediation="Use credential manager",
            examples=["password: secret123"],
        )

        # Test matching
        assert pattern.matches("password: secret123")
        assert pattern.matches("PASSWORD: secret123")
        assert not pattern.matches("username: user123")

        # Test finding matches
        text = "password: secret123 and username: user123"
        matches = pattern.find_matches(text)
        assert len(matches) == 1
        assert matches[0].group(1) == "secret123"

    def test_pattern_examples(self) -> None:
        """Test pattern examples are properly handled."""
        examples = ["api_key: abc123", "API_KEY=xyz789"]
        pattern = CredentialPattern(
            credential_type=CredentialType.API_KEY,
            regex_pattern=re.compile(r"api_key:\s*(\w+)"),
            confidence=0.9,
            context_keywords=["api", "key"],
            description="API key pattern",
            remediation="Use environment variables",
            examples=examples,
        )

        assert pattern.examples == examples


class TestCredentialPatternRegistry:
    """Test credential pattern registry functionality."""

    def test_registry_initialization(self) -> None:
        """Test registry initialization with default patterns."""
        registry = CredentialPatternRegistry()

        stats = registry.get_statistics()
        assert stats["total_patterns"] > 0
        assert stats["patterns_by_type"][CredentialType.AWS.value] >= 3
        assert stats["patterns_by_type"][CredentialType.API_KEY.value] >= 2

    def test_get_patterns_by_confidence(self) -> None:
        """Test filtering patterns by confidence threshold."""
        registry = CredentialPatternRegistry()

        # High confidence (>= 0.9)
        high_conf_patterns = registry.get_patterns_by_confidence(0.9)
        assert all(p.confidence >= 0.9 for p in high_conf_patterns)

        # Medium confidence (>= 0.7)
        med_conf_patterns = registry.get_patterns_by_confidence(0.7)
        assert all(p.confidence >= 0.7 for p in med_conf_patterns)
        assert len(med_conf_patterns) >= len(high_conf_patterns)

    def test_get_patterns_by_type(self) -> None:
        """Test filtering patterns by credential type."""
        registry = CredentialPatternRegistry()

        aws_patterns = registry.get_patterns_by_type(CredentialType.AWS)
        assert all(p.credential_type == CredentialType.AWS for p in aws_patterns)
        assert len(aws_patterns) >= 3

        # Test AWS Access Key pattern
        aws_key_pattern = next(
            (p for p in aws_patterns if "Access Key" in p.description), None
        )
        assert aws_key_pattern is not None
        assert aws_key_pattern.confidence == 0.95
        assert aws_key_pattern.severity == "critical"

    def test_get_patterns_by_severity(self) -> None:
        """Test filtering patterns by severity level."""
        registry = CredentialPatternRegistry()

        critical_patterns = registry.get_patterns_by_severity("critical")
        assert all(p.severity == "critical" for p in critical_patterns)
        assert len(critical_patterns) > 0

        high_patterns = registry.get_patterns_by_severity("high")
        assert all(p.severity == "high" for p in high_patterns)

    def test_search_text_aws_credentials(self) -> None:
        """Test searching for AWS credentials."""
        registry = CredentialPatternRegistry()

        test_text = """
        aws_access_key_id: AKIAIOSFODNN7EXAMPLE
        aws_secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
        aws_session_token: (
            AQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjrBs=
        )
        """

        matches = registry.search_text(test_text, min_confidence=0.7)
        assert len(matches) >= 3

        # Check AWS Access Key match
        aws_access_matches = [
            m
            for m in matches
            if m["credential_type"] == "aws" and "Access Key" in m["pattern"]
        ]
        assert len(aws_access_matches) >= 1
        assert aws_access_matches[0]["severity"] == "critical"
        assert aws_access_matches[0]["confidence"] == 0.95

        # Check AWS Secret Key match
        aws_secret_matches = [
            m
            for m in matches
            if m["credential_type"] == "aws" and "Secret" in m["pattern"]
        ]
        assert len(aws_secret_matches) >= 1
        assert aws_secret_matches[0]["severity"] == "critical"

    def test_search_text_api_keys(self) -> None:
        """Test searching for API keys."""
        registry = CredentialPatternRegistry()

        test_text = f"""
        api_key: {STRIPE_TEST_KEY}
        x-api-key: abcdef1234567890abcdef
        Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        """

        matches = registry.search_text(test_text, min_confidence=0.8)
        assert len(matches) >= 2

        # Check API key matches
        api_key_matches = [m for m in matches if m["credential_type"] == "api_key"]
        assert len(api_key_matches) >= 2

        # Check different API key formats
        api_key_texts = [m["match_text"] for m in api_key_matches]
        assert any("sk_live_" in text for text in api_key_texts)
        assert any("x-api-key" in text.lower() for text in api_key_texts)

    def test_search_text_jwts(self) -> None:
        """Test searching for JWT tokens."""
        registry = CredentialPatternRegistry()

        test_text = """
        Authorization: Bearer (
            eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
        )
        """

        matches = registry.search_text(test_text, min_confidence=0.8)
        jwt_matches = [m for m in matches if m["credential_type"] == "jwt"]
        assert len(jwt_matches) >= 1

        # JWT should be detected
        jwt_match = jwt_matches[0]
        assert jwt_match["confidence"] == 0.9
        assert jwt_match["severity"] == "high"

    def test_search_text_database_connections(self) -> None:
        """Test searching for database connection strings."""
        registry = CredentialPatternRegistry()

        test_text = """
        mongodb://user:password@localhost:27017/mydb
        postgresql://user:secret@localhost:5432/mydb
        redis://:password@localhost:6379
        """

        matches = registry.search_text(test_text, min_confidence=0.8)
        db_matches = [m for m in matches if m["credential_type"] == "database"]
        assert len(db_matches) >= 3

        # All should be high severity
        assert all(m["severity"] == "high" for m in db_matches)

    def test_search_text_private_keys(self) -> None:
        """Test searching for private keys."""
        registry = CredentialPatternRegistry()

        test_text = """
        -----BEGIN PRIVATE KEY-----
        MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7VJTUt9Us8cKBw...
        -----END PRIVATE KEY-----
        -----BEGIN RSA PRIVATE KEY-----
        MIIEpAIBAAKCAQEA4f5wg5l2hKsTeNem/V41fGnJm6gOdrj8ym3rFkEjWT2btZb5...
        -----END RSA PRIVATE KEY-----
        -----BEGIN OPENSSH PRIVATE KEY-----
        b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABFwAAA...
        -----END OPENSSH PRIVATE KEY-----
        """

        matches = registry.search_text(test_text, min_confidence=0.7)
        pk_matches = [
            m for m in matches if m["credential_type"] in ["private_key", "ssh_key"]
        ]
        assert len(pk_matches) >= 3

        # All should be critical severity
        critical_matches = [m for m in pk_matches if m["severity"] == "critical"]
        assert len(critical_matches) >= 3

    def test_scan_file(self) -> None:
        """Test scanning files for credentials."""
        registry = CredentialPatternRegistry()

        # Create a temporary test file

        test_content = f"""
        # Configuration file with credentials
        api_key: {STRIPE_TEST_KEY}
        database_url: postgresql://user:password@localhost:5432/db
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write(test_content)
            temp_file = Path(f.name)

        try:
            matches = registry.scan_file(str(temp_file), min_confidence=0.8)
            assert len(matches) >= 2
            assert all(m["file_path"] == str(temp_file) for m in matches)
        finally:
            temp_file.unlink()  # Clean up

    def test_statistics_accuracy(self) -> None:
        """Test that statistics are accurate."""
        registry = CredentialPatternRegistry()
        stats = registry.get_statistics()

        # Validate basic statistics
        assert stats["total_patterns"] > 0
        assert "patterns_by_type" in stats
        assert "patterns_by_severity" in stats

        # Validate type counts
        total_by_type = sum(stats["patterns_by_type"].values())
        assert total_by_type == stats["total_patterns"]

        # Validate severity counts
        total_by_severity = sum(stats["patterns_by_severity"].values())
        assert total_by_severity == stats["total_patterns"]


class TestConvenienceFunctions:
    """Test convenience functions for credential detection."""

    def test_get_credential_registry(self) -> None:
        """Test getting the global credential registry."""
        registry1 = get_credential_registry()
        registry2 = get_credential_registry()

        # Should return the same instance
        assert registry1 is registry2
        assert isinstance(registry1, CredentialPatternRegistry)

        # Should have patterns loaded
        stats = registry1.get_statistics()
        assert stats["total_patterns"] > 0

    def test_scan_for_credentials_function(self) -> None:
        """Test the convenience scan function."""
        test_text = """
        aws_access_key_id: AKIAIOSFODNN7EXAMPLE
        password: secret123
        """

        matches = scan_for_credentials(test_text, min_confidence=0.7)
        assert len(matches) >= 2

        # Should have same structure as registry search
        for match in matches:
            assert "credential_type" in match
            assert "confidence" in match
            assert "severity" in match
            assert "match_text" in match
            assert "remediation" in match

    def test_confidence_filtering(self) -> None:
        """Test confidence filtering in convenience function."""
        test_text = """
        # High confidence patterns
        aws_access_key_id: AKIAIOSFODNN7EXAMPLE
        password: secret123

        # Lower confidence patterns might be filtered out
        some_api_key: abc123
        """

        # High confidence threshold
        high_matches = scan_for_credentials(test_text, min_confidence=0.9)
        assert len(high_matches) >= 2

        # Lower confidence threshold
        low_matches = scan_for_credentials(test_text, min_confidence=0.6)
        assert len(low_matches) >= len(high_matches)


class TestPatternQuality:
    """Test quality and correctness of patterns."""

    def test_aws_patterns_completeness(self) -> None:
        """Test that AWS patterns cover common formats."""
        registry = CredentialPatternRegistry()
        aws_patterns = registry.get_patterns_by_type(CredentialType.AWS)

        # Should have patterns for all three AWS credential types
        pattern_descriptions = [p.description.lower() for p in aws_patterns]
        assert any("access key" in desc for desc in pattern_descriptions)
        assert any("secret" in desc for desc in pattern_descriptions)
        assert any("session token" in desc for desc in pattern_descriptions)

    def test_pattern_regex_validity(self) -> None:
        """Test that all regex patterns are valid."""
        registry = CredentialPatternRegistry()
        all_patterns = registry.get_all_patterns()

        for pattern in all_patterns:
            # All patterns should be compiled regex objects
            assert hasattr(pattern.regex_pattern, "search")

            # Test that patterns can be used without errors
            try:
                pattern.regex_pattern.search("")
                pattern.matches("")
            except Exception as exc:
                pytest.fail(f"Pattern regex error for {pattern.description}: {exc}")

    def test_confidence_values(self) -> None:
        """Test that confidence values are within valid range."""
        registry = CredentialPatternRegistry()
        all_patterns = registry.get_all_patterns()

        for pattern in all_patterns:
            assert 0.0 <= pattern.confidence <= 1.0
            assert isinstance(pattern.confidence, float)

    def test_severity_values(self) -> None:
        """Test that severity values are valid."""
        registry = CredentialPatternRegistry()
        all_patterns = registry.get_all_patterns()

        valid_severities = {"low", "medium", "high", "critical"}
        for pattern in all_patterns:
            assert pattern.severity in valid_severities

    def test_remediation_and_examples(self) -> None:
        """Test that all patterns have remediation and examples."""
        registry = CredentialPatternRegistry()
        all_patterns = registry.get_all_patterns()

        for pattern in all_patterns:
            assert pattern.remediation  # Should not be empty
            assert len(pattern.remediation.strip()) > 0
            assert pattern.examples  # Should have examples
            assert len(pattern.examples) > 0
            assert all(isinstance(ex, str) for ex in pattern.examples)


class TestFalsePositiveReduction:
    """Test that patterns minimize false positives."""

    def test_safe_keywords_not_detected(self) -> None:
        """Test that safe keywords don't trigger false positives."""
        registry = CredentialPatternRegistry()

        safe_text = """
        # These should not trigger credential detection
        api_key_example: use_your_key_here
        password_example: replace_with_real_password
        your_secret_key_here
        test_api_key_format
        demo_password_value
        placeholder_token_value
        """

        matches = registry.search_text(safe_text, min_confidence=0.8)
        # Should have very few or no high-confidence matches
        high_conf_matches = [m for m in matches if m["confidence"] >= 0.8]
        assert len(high_conf_matches) == 0

    def test_example_code_not_detected(self) -> None:
        """Test that example code doesn't trigger false positives."""
        registry = CredentialPatternRegistry()

        example_code = """
        # Example code snippets
        def get_api_key():
            return "sk_live_" + "example_key_placeholder"

        # Documentation examples
        # aws_access_key_id: YOUR_ACCESS_KEY_HERE
        # aws_secret_access_key: YOUR_SECRET_KEY_HERE

        # Test data
        test_password = "test_password_123"
        fake_api_key = "fake_api_key_for_testing"
        """

        matches = registry.search_text(example_code, min_confidence=0.8)
        # Example code should not trigger high-confidence detections
        high_conf_matches = [m for m in matches if m["confidence"] >= 0.9]
        assert len(high_conf_matches) == 0

    def test_context_sensitive_matching(self) -> None:
        """Test that patterns consider context appropriately."""
        registry = CredentialPatternRegistry()

        # This should match (real looking credential)
        real_credential = "sk_live_" + "1234567890abcdef1234567890abcdef123456"

        # This should not match (clearly fake/test)
        fake_credential = "sk_live_" + "test_key_example_placeholder_12345"

        real_matches = registry.search_text(
            f"api_key: {real_credential}", min_confidence=0.8
        )
        fake_matches = registry.search_text(
            f"api_key: {fake_credential}", min_confidence=0.8
        )

        # Real credential should be detected with higher confidence
        assert len(real_matches) >= 1
        assert real_matches[0]["confidence"] >= 0.8

        # Fake credential should have lower or no matches
        assert len(fake_matches) == 0 or fake_matches[0]["confidence"] < 0.8


class TestThreadLocalRegistryManagement:
    """Test the new thread-local registry management system."""

    def test_get_current_registry_creates_instance(self) -> None:
        """Test that get_current_registry creates an instance when none exists."""
        # Ensure we start with no registry in thread-local using the storage API
        credential_patterns._registry_storage.clear_registry()

        registry = get_current_registry()
        assert isinstance(registry, CredentialPatternRegistry)

        # Should have patterns loaded
        stats = registry.get_statistics()
        assert stats["total_patterns"] > 0

    def test_get_current_registry_returns_same_instance(self) -> None:
        """Test that get_current_registry returns the same instance
        within the same thread."""
        registry1 = get_current_registry()
        registry2 = get_current_registry()

        # Should return the same instance
        assert registry1 is registry2
        assert isinstance(registry1, CredentialPatternRegistry)

    def test_credential_registry_context_manager(self) -> None:
        """Test the credential_registry_context context manager."""
        # Create a custom registry
        custom_registry = CredentialPatternRegistry()

        with credential_registry_context(custom_registry) as registry:
            # Should be the custom registry we passed in
            assert registry is custom_registry
            assert get_current_registry() is custom_registry

        # After context exits, should revert to previous state
        # Note: If no previous registry existed, a new one is created
        current_registry = get_current_registry()
        assert current_registry is not custom_registry

    def test_credential_registry_context_creates_default(self) -> None:
        """Test that context manager creates default registry when none provided."""
        with credential_registry_context() as registry:
            assert isinstance(registry, CredentialPatternRegistry)
            assert get_current_registry() is registry

        # Should revert after context exits
        new_registry = get_current_registry()
        assert new_registry is not registry

    def test_nested_context_managers(self) -> None:
        """Test nested context manager behavior."""
        outer_registry = CredentialPatternRegistry()
        inner_registry = CredentialPatternRegistry()

        with credential_registry_context(outer_registry):
            assert get_current_registry() is outer_registry

            with credential_registry_context(inner_registry):
                assert get_current_registry() is inner_registry
                assert get_current_registry() is not outer_registry

            # After inner context exits, should revert to outer
            assert get_current_registry() is outer_registry

        # After outer context exits, should revert to original state
        final_registry = get_current_registry()
        assert final_registry is not outer_registry
        assert final_registry is not inner_registry

    def test_context_manager_with_none_registry(self) -> None:
        """Test context manager behavior when None is passed."""
        original_registry = get_current_registry()

        with credential_registry_context(None) as registry:
            # Should create a new default registry
            assert isinstance(registry, CredentialPatternRegistry)
            assert registry is not original_registry
            assert get_current_registry() is registry

        # Should revert to original
        assert get_current_registry() is original_registry

    def test_scan_for_credentials_with_custom_registry(self) -> None:
        """Test scan_for_credentials with a custom registry."""
        custom_registry = CredentialPatternRegistry()

        test_text = "password: secret123"

        # Test with custom registry
        matches = scan_for_credentials(
            test_text, min_confidence=0.7, registry=custom_registry
        )
        assert len(matches) >= 1
        assert matches[0]["credential_type"] == "password"

    def test_scan_for_credentials_uses_context_registry(self) -> None:
        """Test that scan_for_credentials uses context registry when none specified."""
        custom_registry = CredentialPatternRegistry()

        with credential_registry_context(custom_registry):
            test_text = "password: secret123"
            matches = scan_for_credentials(test_text, min_confidence=0.7)

            # Should have used the context registry
            assert len(matches) >= 1

    def test_backward_compatibility_get_credential_registry(self) -> None:
        """Test that get_credential_registry still works for backward compatibility."""
        # This should work without errors
        registry = get_credential_registry()
        assert isinstance(registry, CredentialPatternRegistry)

        # Should be the same as get_current_registry
        current_registry = get_current_registry()
        assert registry is current_registry

    def test_registry_context_class_direct_usage(self) -> None:
        """Test direct usage of CredentialRegistryContext class."""
        custom_registry = CredentialPatternRegistry()

        context = CredentialRegistryContext(custom_registry)

        with context as registry:
            assert registry is custom_registry
            assert get_current_registry() is custom_registry

        # Should revert after context
        assert get_current_registry() is not custom_registry

    def test_thread_safety_isolated_registries(self) -> None:
        """Test that different threads can have isolated registries."""

        results = {}

        def thread_worker(thread_id: int) -> None:
            # Each thread gets its own registry
            custom_registry = CredentialPatternRegistry()
            with credential_registry_context(custom_registry):
                time.sleep(0.1)  # Small delay to ensure threads overlap
                current = get_current_registry()
                results[thread_id] = id(current)  # Store object ID

        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=thread_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Each thread should have had its own registry
        registry_ids = list(results.values())
        assert len(registry_ids) == 3
        # All IDs should be different (different registry instances)
        assert len(set(registry_ids)) == 3
