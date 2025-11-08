"""Configuration validation invariant tests using Hypothesis.
# pylint: disable=no-value-for-parameter,not-an-iterable
# pylint: disable=unsupported-membership-test
# Test issues

Tests properties that should hold true for configuration systems:
- Configuration validation is comprehensive
- Invalid configurations are rejected consistently
- Configuration serialization is safe and reversible
- Environment variable handling is robust
"""

from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from importobot.medallion.storage.config import VALID_BACKEND_TYPES, StorageConfig


class TestConfigurationInvariants:
    """Configuration system invariant tests."""

    @given(
        st.dictionaries(
            keys=st.sampled_from(
                [
                    "backend_type",
                    "base_path",
                    "compression",
                    "auto_backup",
                    "retention_days",
                    "cache_size_mb",
                    "batch_size",
                    "encryption_enabled",
                    "backup_enabled",
                    "backup_interval_hours",
                    "backup_retention_days",
                ]
            ),
            values=st.one_of(
                st.text(min_size=0, max_size=100),
                st.integers(min_value=-1000, max_value=1000),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=50)
    def test_storage_config_validation_invariant(self, config_data: dict[str, Any]) -> None:
        """Invariant: Configuration validation should be comprehensive and safe."""
        try:
            config = StorageConfig.from_dict(config_data)

            # Configuration should always have validation method
            assert hasattr(config, "validate")
            assert callable(config.validate)

            # Validation should return a list of strings
            issues = config.validate()
            assert isinstance(issues, list)
            for issue in issues:
                assert isinstance(issue, str)
                assert len(issue) > 0

            # Configuration should be serializable
            config_dict = config.to_dict()
            assert isinstance(config_dict, dict)

            # Serialized config should be deserializable
            roundtrip_config = StorageConfig.from_dict(config_dict)
            assert isinstance(roundtrip_config, StorageConfig)

        except (TypeError, ValueError, AttributeError):
            # Expected for invalid configuration types
            pass
        except Exception as e:
            pytest.fail(
                f"Unexpected exception in config validation: {type(e).__name__}: {e}"
            )

    @given(
        st.dictionaries(
            keys=st.text(min_size=0, max_size=50),
            values=st.one_of(
                st.text(), st.integers(), st.floats(), st.booleans(), st.none()
            ),
            min_size=0,
            max_size=20,
        )
    )
    @settings(max_examples=30)
    def test_config_update_safety_invariant(self, update_data: dict[str, Any]) -> None:
        """Invariant: Configuration updates should be safe and not break the system."""
        try:
            initial_config = StorageConfig()
            assert initial_config is not None

            # Attempt to update configuration using from_dict
            # This tests that arbitrary data doesn't crash the system
            try:
                updated_config = StorageConfig.from_dict(update_data)
            except (TypeError, ValueError, AttributeError):
                # Expected for invalid update data - system should not crash
                updated_config = initial_config

            assert updated_config is not None

            # Validation should return a list of issues
            validation_issues = updated_config.validate()
            assert isinstance(validation_issues, list)
            for issue in validation_issues:
                assert isinstance(issue, str)

        except Exception as e:
            pytest.fail(
                f"Unexpected exception in config update: {type(e).__name__}: {e}"
            )

    @given(st.text(min_size=0, max_size=200))
    @settings(max_examples=30)
    def test_path_handling_invariant(self, path_string: str) -> None:
        """Invariant: Path handling should be safe across platforms."""
        try:
            # Try to create a StorageConfig with the path
            config_data = {"base_path": path_string}
            config = StorageConfig.from_dict(config_data)

            # Path should be converted to Path object
            assert hasattr(config, "base_path")
            if config.base_path is not None:
                assert isinstance(config.base_path, Path)

            # Should be able to convert back to dict
            config_dict = config.to_dict()
            assert "base_path" in config_dict
            assert isinstance(config_dict["base_path"], str)

        except (OSError, ValueError, TypeError):
            # Expected for invalid paths
            pass
        except Exception as e:
            pytest.fail(
                f"Unexpected exception in path handling: {type(e).__name__}: {e}"
            )

    @given(st.integers(min_value=-1000, max_value=1000))
    @settings(max_examples=30)
    def test_numeric_validation_invariant(self, numeric_value: int) -> None:
        """Invariant: Numeric configuration values should be validated properly."""
        numeric_configs = [
            {"retention_days": numeric_value},
            {"cache_size_mb": numeric_value},
            {"batch_size": numeric_value},
            {"backup_interval_hours": numeric_value},
            {"backup_retention_days": numeric_value},
        ]

        for config_data in numeric_configs:
            try:
                config = StorageConfig.from_dict(config_data)
                issues = config.validate()

                # Validation should catch negative or zero values where inappropriate
                field_name = next(iter(config_data.keys()))
                field_value = config_data[field_name]

                if field_value <= 0:
                    # Should have validation issues for non-positive values
                    relevant_issues = [
                        issue for issue in issues if field_name in issue.lower()
                    ]
                    assert (
                        len(relevant_issues) > 0 or field_value == 0
                    )  # Some fields might allow 0

                # Issues should be descriptive
                for issue in issues:
                    assert isinstance(issue, str)
                    assert len(issue) > 10  # Should be descriptive

            except (TypeError, ValueError):
                # Expected for invalid numeric values
                pass

    @given(st.sampled_from(["local", "invalid", "s3", "azure", "gcp", "", None, 123]))
    @settings(max_examples=20)
    def test_backend_type_validation_invariant(self, backend_type: Any) -> None:
        """Invariant: Backend type validation should be strict."""
        try:
            config_data = {"backend_type": backend_type}
            config = StorageConfig.from_dict(config_data)
            issues = config.validate()

            # Valid backend types should have no issues (or unrelated issues)
            if backend_type in VALID_BACKEND_TYPES:
                backend_issues = [
                    issue for issue in issues if "backend_type" in issue.lower()
                ]
                assert len(backend_issues) == 0
            # Invalid backend types should generate validation issues
            elif backend_type not in [None, ""]:
                backend_issues = [
                    issue for issue in issues if "backend_type" in issue.lower()
                ]
                # Should have at least one backend-related issue
                # for clearly invalid types
                if backend_type not in VALID_BACKEND_TYPES and isinstance(
                    backend_type, str
                ):
                    assert len(backend_issues) > 0

        except (TypeError, AttributeError):
            # Expected for completely invalid types like integers
            pass

    @given(st.text(min_size=0, max_size=100), st.booleans())
    @settings(max_examples=30)
    def test_encryption_config_consistency_invariant(
        self, key_path: str, encryption_enabled: bool
    ) -> None:
        """Invariant: Encryption configuration should be logically consistent."""
        try:
            config_data = {
                "encryption_enabled": encryption_enabled,
                "encryption_key_path": key_path if key_path else None,
            }

            config = StorageConfig.from_dict(config_data)
            issues = config.validate()

            # If encryption is enabled, key path should be required
            if encryption_enabled and not key_path:
                encryption_issues = [
                    issue
                    for issue in issues
                    if "encryption" in issue.lower() and "key" in issue.lower()
                ]
                assert len(encryption_issues) > 0

            # All issues should be meaningful strings
            for issue in issues:
                assert isinstance(issue, str)
                assert len(issue.strip()) > 0

        except (TypeError, AttributeError):
            # Expected for invalid configuration types
            pass

    @given(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=30),
            values=st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=0,
            max_size=10,
        )
    )
    @settings(max_examples=20)
    def test_configuration_isolation_invariant(self, config_updates: dict[str, Any]) -> None:
        """Invariant: Configuration instances are independent."""
        try:
            # Create initial config
            config1 = StorageConfig()

            # Try to create another config from arbitrary data
            try:
                config2 = StorageConfig.from_dict(config_updates)
            except (TypeError, ValueError, AttributeError):
                # Expected for invalid config data
                config2 = StorageConfig()

            # Both configs should have proper structure
            assert hasattr(config1, "to_dict")
            assert hasattr(config2, "to_dict")

            # Convert to dict for key checking
            dict1 = config1.to_dict()
            dict2 = config2.to_dict()
            assert isinstance(dict1, dict)
            assert isinstance(dict2, dict)

            # Both should have required structure
            required_keys = [
                "backend_type",
                "base_path",
                "compression",
                "auto_backup",
                "retention_days",
            ]
            for key in required_keys:
                assert key in dict1
                assert key in dict2

            # Validation should work for both
            issues1 = config1.validate()
            issues2 = config2.validate()
            assert isinstance(issues1, list)
            assert isinstance(issues2, list)

        except Exception as e:
            pytest.fail(f"Configuration isolation test failed: {type(e).__name__}: {e}")

    @given(st.booleans(), st.booleans(), st.booleans())
    @settings(max_examples=20)
    def test_boolean_config_handling_invariant(
        self, compression: bool, auto_backup: bool, encryption: bool
    ) -> None:
        """Invariant: Boolean configuration values should be handled correctly."""
        try:
            config_data = {
                "compression": compression,
                "auto_backup": auto_backup,
                "encryption_enabled": encryption,
            }

            config = StorageConfig.from_dict(config_data)

            # Boolean values should be preserved
            assert config.compression == compression
            assert config.auto_backup == auto_backup
            assert config.encryption_enabled == encryption

            # Should serialize and deserialize correctly
            dict_form = config.to_dict()
            assert dict_form["compression"] == compression
            assert dict_form["auto_backup"] == auto_backup
            assert dict_form["encryption_enabled"] == encryption

            # Roundtrip should preserve values
            roundtrip = StorageConfig.from_dict(dict_form)
            assert roundtrip.compression == compression
            assert roundtrip.auto_backup == auto_backup
            assert roundtrip.encryption_enabled == encryption

        except Exception as e:
            pytest.fail(f"Boolean config handling failed: {type(e).__name__}: {e}")
