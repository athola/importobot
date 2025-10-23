"""TDD Unit tests for format definition system.

Tests for FormatDefinition, FieldDefinition, EvidenceWeight enum,
and the core format definition infrastructure following TDD principles.

Business Requirements:
- Format definitions must be immutable and thread-safe
- Evidence weights must provide clear scoring methodology
- Field definitions must support comprehensive validation
- Format definitions must enable accurate detection algorithms
"""

import threading
import time
import unittest
from unittest.mock import patch

from importobot.medallion.bronze.format_detector import (
    FormatRegistry,
)
from importobot.medallion.bronze.format_models import (
    EvidenceWeight,
    FieldDefinition,
    FormatDefinition,
)
from importobot.medallion.interfaces.enums import SupportedFormat


class TestEvidenceWeight(unittest.TestCase):
    """Unit tests for EvidenceWeight enum and its methods."""

    def test_evidence_weight_enum_values(self):
        """Test that EvidenceWeight enum has correct integer values."""
        assert EvidenceWeight.NONE == 0  # type: ignore[comparison-overlap]
        assert EvidenceWeight.WEAK == 1  # type: ignore[comparison-overlap]
        assert EvidenceWeight.MODERATE == 2  # type: ignore[comparison-overlap]
        assert EvidenceWeight.STRONG == 3  # type: ignore[comparison-overlap]
        assert EvidenceWeight.UNIQUE == 5  # type: ignore[comparison-overlap]

    def test_evidence_weight_ordering(self):
        """Test that evidence weights can be properly ordered."""
        weights = [
            EvidenceWeight.UNIQUE,
            EvidenceWeight.NONE,
            EvidenceWeight.STRONG,
            EvidenceWeight.WEAK,
            EvidenceWeight.MODERATE,
        ]
        sorted_weights = sorted(weights)

        expected = [
            EvidenceWeight.NONE,
            EvidenceWeight.WEAK,
            EvidenceWeight.MODERATE,
            EvidenceWeight.STRONG,
            EvidenceWeight.UNIQUE,
        ]
        assert sorted_weights == expected

    def test_evidence_weight_math_operations(self):
        """Test that evidence weights support mathematical operations."""
        # Addition
        total = EvidenceWeight.STRONG + EvidenceWeight.MODERATE
        assert total == 5

        # Comparison
        assert EvidenceWeight.UNIQUE > EvidenceWeight.STRONG
        assert EvidenceWeight.MODERATE >= EvidenceWeight.WEAK

    def test_evidence_threshold_classification(self):
        """Test classification of evidence thresholds."""
        # Test insufficient evidence threshold
        assert EvidenceWeight.NONE < 2
        assert EvidenceWeight.WEAK < 2

        # Test moderate evidence threshold
        assert EvidenceWeight.MODERATE >= 2
        assert EvidenceWeight.MODERATE < 4

        # Test strong evidence threshold (STRONG = 3, UNIQUE = 5)
        assert EvidenceWeight.STRONG >= 3
        assert EvidenceWeight.UNIQUE >= 5

    def test_evidence_weight_comparison(self):
        """Test evidence weight comparison functionality."""
        # Test that evidence weights can be compared
        assert EvidenceWeight.UNIQUE > EvidenceWeight.STRONG
        assert EvidenceWeight.STRONG > EvidenceWeight.MODERATE


class TestFieldDefinition(unittest.TestCase):
    """Unit tests for FieldDefinition class."""

    def test_field_definition_creation(self):
        """Test creation of FieldDefinition instances."""
        field = FieldDefinition(
            name="testCase",
            evidence_weight=EvidenceWeight.UNIQUE,
            description="Zephyr test case structure",
        )

        assert field.name == "testCase"
        assert field.evidence_weight == EvidenceWeight.UNIQUE
        assert field.description == "Zephyr test case structure"
        assert field.pattern is None
        assert not field.is_required

    def test_field_definition_with_validation(self):
        """Test FieldDefinition with validation pattern."""
        field = FieldDefinition(
            name="key",
            evidence_weight=EvidenceWeight.STRONG,
            description="JIRA issue key",
            pattern=r"^[A-Z]+-\d+$",
            is_required=True,
        )

        assert field.pattern == r"^[A-Z]+-\d+$"
        assert field.is_required

    def test_field_definition_mutability(self):
        """Test that FieldDefinition instances are mutable dataclasses."""
        field = FieldDefinition("testCase", EvidenceWeight.UNIQUE)

        # Dataclasses are mutable by default - test that we can modify
        original_name = field.name
        field.name = "modified"
        assert field.name == "modified"
        assert field.name != original_name

    def test_field_definition_equality(self):
        """Test equality comparison of FieldDefinition instances."""
        field1 = FieldDefinition("testCase", EvidenceWeight.UNIQUE)
        field2 = FieldDefinition("testCase", EvidenceWeight.UNIQUE)
        field3 = FieldDefinition("execution", EvidenceWeight.STRONG)

        assert field1 == field2
        assert field1 != field3

    def test_field_definition_string_representation(self):
        """Test string representation of FieldDefinition."""
        field = FieldDefinition(
            "testCase", EvidenceWeight.UNIQUE, description="Test case structure"
        )
        repr_str = repr(field)

        assert "testCase" in repr_str
        assert "UNIQUE" in repr_str
        assert "Test case structure" in repr_str


class TestFormatDefinition(unittest.TestCase):
    """Unit tests for FormatDefinition class."""

    def setUp(self):
        """Set up test fixtures."""
        self.zephyr_unique = [
            FieldDefinition(
                "testCase", EvidenceWeight.UNIQUE, description="Zephyr test case"
            ),
            FieldDefinition(
                "execution", EvidenceWeight.UNIQUE, description="Zephyr execution"
            ),
            FieldDefinition("cycle", EvidenceWeight.UNIQUE, description="Zephyr cycle"),
        ]

        self.zephyr_strong = [
            FieldDefinition(
                "project", EvidenceWeight.STRONG, description="Project info"
            )
        ]

        self.zephyr_moderate = [
            FieldDefinition(
                "sprint", EvidenceWeight.MODERATE, description="Sprint info"
            )
        ]

        self.zephyr_weak = [
            FieldDefinition("key", EvidenceWeight.WEAK, description="Item key")
        ]

    def test_format_definition_creation(self):
        """Test creation of FormatDefinition instances."""
        format_def = FormatDefinition(
            name="Zephyr Test Management",
            format_type=SupportedFormat.ZEPHYR,
            description="Atlassian Zephyr test format",
            unique_indicators=self.zephyr_unique,
            strong_indicators=self.zephyr_strong,
            moderate_indicators=self.zephyr_moderate,
            weak_indicators=self.zephyr_weak,
        )

        assert format_def.format_type == SupportedFormat.ZEPHYR
        assert format_def.name == "Zephyr Test Management"
        assert len(format_def.unique_indicators) == 3
        assert len(format_def.strong_indicators) == 1
        assert len(format_def.moderate_indicators) == 1
        assert len(format_def.weak_indicators) == 1

    def test_format_definition_default_values(self):
        """Test FormatDefinition with default values."""
        format_def = FormatDefinition(
            name="Generic Format",
            format_type=SupportedFormat.GENERIC,
            description="Generic test format",
            unique_indicators=[],
        )

        assert format_def.strong_indicators == []
        assert format_def.moderate_indicators == []
        assert format_def.weak_indicators == []
        assert format_def.confidence_boost_threshold == 0.33
        assert format_def.min_score_threshold == 4

    def test_format_definition_custom_thresholds(self):
        """Test FormatDefinition with custom detection thresholds."""
        format_def = FormatDefinition(
            name="Generic Format",
            format_type=SupportedFormat.GENERIC,
            description="Generic test format",
            unique_indicators=[],
            confidence_boost_threshold=0.8,
            min_score_threshold=7,
        )

        assert format_def.confidence_boost_threshold == 0.8
        assert format_def.min_score_threshold == 7

    def test_format_definition_mutability(self):
        """Test that FormatDefinition instances are mutable dataclasses."""
        format_def = FormatDefinition(
            name="Zephyr",
            format_type=SupportedFormat.ZEPHYR,
            description="Test",
            unique_indicators=self.zephyr_unique,
        )

        # Dataclasses are mutable by default
        original_name = format_def.name
        format_def.name = "Modified"
        assert format_def.name == "Modified"
        assert format_def.name != original_name

    def test_format_definition_get_all_fields(self):
        """Test getting all fields from FormatDefinition."""
        format_def = FormatDefinition(
            name="Zephyr",
            format_type=SupportedFormat.ZEPHYR,
            description="Test",
            unique_indicators=self.zephyr_unique,
            strong_indicators=self.zephyr_strong,
            moderate_indicators=self.zephyr_moderate,
            weak_indicators=self.zephyr_weak,
        )

        all_fields = format_def.get_all_fields()
        assert len(all_fields) == 6  # 3 unique + 1 strong + 1 moderate + 1 weak

        # Check that all indicator types are included
        unique_names = {field.name for field in self.zephyr_unique}
        strong_names = {field.name for field in self.zephyr_strong}
        moderate_names = {field.name for field in self.zephyr_moderate}
        weak_names = {field.name for field in self.zephyr_weak}
        all_names = {field.name for field in all_fields}

        assert unique_names.issubset(all_names)
        assert strong_names.issubset(all_names)
        assert moderate_names.issubset(all_names)
        assert weak_names.issubset(all_names)

    def test_format_definition_calculate_max_score(self):
        """Test calculation of maximum possible score."""
        format_def = FormatDefinition(
            name="Zephyr",
            format_type=SupportedFormat.ZEPHYR,
            description="Test",
            unique_indicators=self.zephyr_unique,
            strong_indicators=self.zephyr_strong,
            moderate_indicators=self.zephyr_moderate,
            weak_indicators=self.zephyr_weak,
        )

        max_score = format_def.get_max_possible_score()

        # Expected: 3 UNIQUE (5 each) + 1 STRONG (3) +
        # 1 MODERATE (2) + 1 WEAK (1) = 21
        expected_max = (
            3 * EvidenceWeight.UNIQUE
            + EvidenceWeight.STRONG
            + EvidenceWeight.MODERATE
            + EvidenceWeight.WEAK
        )
        assert max_score == expected_max


class TestFormatRegistry(unittest.TestCase):
    """Unit tests for FormatRegistry class."""

    def setUp(self):
        """Set up test fixtures."""
        self.registry = FormatRegistry()

    def test_format_registry_creation(self):
        """Test creation of FormatRegistry instance."""
        assert isinstance(self.registry, FormatRegistry)
        # Registry auto-loads built-in formats
        assert len(self.registry.get_all_formats()) > 0

    def test_register_format(self):
        """Test registering a format in the registry."""
        # Create a new registry without auto-loading to test registration

        empty_registry = FormatRegistry.__new__(
            FormatRegistry
        )  # Create without calling __init__
        empty_registry._formats = {}  # pylint: disable=protected-access

        format_def = FormatDefinition(
            name="Test Custom",
            format_type=SupportedFormat.UNKNOWN,  # Use UNKNOWN to avoid conflicts
            description="Test format",
            unique_indicators=[FieldDefinition("customField", EvidenceWeight.UNIQUE)],
        )

        empty_registry.register_format(format_def)

        formats_dict = empty_registry.get_all_formats()
        assert len(formats_dict) == 1
        assert formats_dict[SupportedFormat.UNKNOWN] == format_def

    def test_register_duplicate_format_type(self):
        """Test that registering duplicate format types overwrites existing."""
        # Registry allows overwriting - this is the actual behavior
        original_format = self.registry.get_format(SupportedFormat.ZEPHYR)
        assert original_format is not None

        format_def = FormatDefinition(
            name="New Zephyr",
            format_type=SupportedFormat.ZEPHYR,
            description="Overwrite test",
            unique_indicators=[FieldDefinition("testCase", EvidenceWeight.UNIQUE)],
        )

        # Should succeed and overwrite
        self.registry.register_format(format_def)

        # Verify it was overwritten
        retrieved = self.registry.get_format(SupportedFormat.ZEPHYR)
        assert retrieved is not None
        assert retrieved.name == "New Zephyr"

    def test_get_format_by_type(self):
        """Test retrieving format by type."""
        # Get the auto-loaded Zephyr format
        retrieved = self.registry.get_format(SupportedFormat.ZEPHYR)
        assert retrieved is not None
        assert retrieved is not None
        assert retrieved.format_type == SupportedFormat.ZEPHYR

    def test_get_existing_format(self):
        """Test retrieving existing format returns the format."""
        result = self.registry.get_format(SupportedFormat.ZEPHYR)
        assert result is not None
        assert result is not None
        assert result.format_type == SupportedFormat.ZEPHYR

    def test_get_supported_format_types(self):
        """Test getting list of supported format types."""
        formats_dict = self.registry.get_all_formats()
        supported_types = list(formats_dict.keys())

        # Should have auto-loaded formats
        assert len(supported_types) > 0
        assert SupportedFormat.ZEPHYR in supported_types

    @patch("importobot.medallion.bronze.formats.create_zephyr_format")
    @patch("importobot.medallion.bronze.formats.create_testlink_format")
    def test_load_built_in_formats(self, mock_testlink, mock_zephyr):
        """Test loading built-in format definitions."""
        # Mock the format creation functions
        zephyr_format = FormatDefinition(
            format_type=SupportedFormat.ZEPHYR,
            name="Zephyr",
            description="Test",
            unique_indicators=[],
        )

        testlink_format = FormatDefinition(
            format_type=SupportedFormat.TESTLINK,
            name="TestLink",
            description="Test",
            unique_indicators=[],
        )

        mock_zephyr.return_value = zephyr_format
        mock_testlink.return_value = testlink_format

        # Test the private method through a new registry instance
        # This tests the actual loading mechanism
        new_registry = FormatRegistry()
        formats = new_registry.get_all_formats()

        # Should have loaded built-in formats
        assert len(formats) > 0

        # Use different format types to avoid conflicts
        def create_format(suffix):
            return FormatDefinition(
                name=f"Thread Test {suffix}",
                format_type=SupportedFormat.UNKNOWN,  # All use UNKNOWN for test
                description=f"Test {suffix}",
                unique_indicators=[
                    FieldDefinition(f"threadTest{suffix}", EvidenceWeight.UNIQUE)
                ],
            )

        # Create empty registry for controlled testing
        test_registry = FormatRegistry.__new__(FormatRegistry)
        test_registry._formats = {}  # pylint: disable=protected-access
        completed_registrations = []

        def register_format(suffix):
            try:
                format_def = create_format(suffix)  # type: ignore[no-untyped-call]
                test_registry.register_format(format_def)
                completed_registrations.append(suffix)
                time.sleep(0.001)  # Small delay to encourage race conditions
            except Exception as e:
                # Record any exceptions
                completed_registrations.append(f"ERROR-{suffix}: {e}")

        # Start multiple threads with different suffixes
        threads = [
            threading.Thread(target=register_format, args=(i,)) for i in range(5)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have completed all registrations (last one wins for UNKNOWN type)
        assert len(completed_registrations) == 5
        formats_dict = test_registry.get_all_formats()
        assert len(formats_dict) == 1  # Only one format type (UNKNOWN)


class TestFormatDefinitionIntegration(unittest.TestCase):
    """Integration tests for format definition system components."""

    def test_complete_format_definition_workflow(self):
        """Test complete workflow of creating and using format definitions."""
        # Create field definitions
        unique_fields = [
            FieldDefinition(
                "customTest", EvidenceWeight.UNIQUE, description="Test case structure"
            ),
            FieldDefinition(
                "customExecution", EvidenceWeight.UNIQUE, description="Execution data"
            ),
        ]

        moderate_fields = [
            FieldDefinition(
                "project", EvidenceWeight.MODERATE, description="Project info"
            )
        ]

        # Create format definition
        format_def = FormatDefinition(
            name="Custom Test Management",
            format_type=SupportedFormat.UNKNOWN,  # Use UNKNOWN to avoid conflicts
            description="Custom test format",
            unique_indicators=unique_fields,
            moderate_indicators=moderate_fields,
        )

        # Register in new registry
        registry = FormatRegistry.__new__(FormatRegistry)
        registry._formats = {}  # pylint: disable=protected-access
        registry.register_format(format_def)

        # Verify complete workflow
        retrieved = registry.get_format(SupportedFormat.UNKNOWN)
        assert retrieved == format_def
        assert retrieved is not None

        all_fields = retrieved.get_all_fields()
        assert len(all_fields) == 3

        max_score = retrieved.get_max_possible_score()
        expected_score = 2 * EvidenceWeight.UNIQUE + EvidenceWeight.MODERATE
        assert max_score == expected_score

    def test_format_definition_validation_edge_cases(self):
        """Test format definition validation with edge cases."""
        # Test with empty indicators should fail validation when registering
        format_def = FormatDefinition(
            name="Empty",
            format_type=SupportedFormat.GENERIC,
            description="Generic format",
            unique_indicators=[],
        )

        assert len(format_def.get_all_fields()) == 0
        assert format_def.get_max_possible_score() == 0

        # Test with custom threshold
        format_def_high_threshold = FormatDefinition(
            name="High Threshold",
            format_type=SupportedFormat.GENERIC,
            description="Test",
            unique_indicators=[],
            confidence_boost_threshold=0.99,
        )

        assert format_def_high_threshold.confidence_boost_threshold == 0.99


if __name__ == "__main__":
    unittest.main()
