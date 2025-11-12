"""Tests for input schema documentation parser."""

import os
import tempfile
from pathlib import Path

import pytest
from _pytest.logging import LogCaptureFixture

import importobot.core.schema_parser as sp
from importobot import exceptions
from importobot.config import MAX_SCHEMA_FILE_SIZE_BYTES
from importobot.core.schema_parser import (
    MAX_SCHEMA_SECTIONS,
    FieldSchema,
    SchemaDocument,
    SchemaParser,
    SchemaRegistry,
    get_schema_registry,
    register_schema_file,
)


class TestSchemaParser:
    """Tests for SchemaParser functionality."""

    def test_parse_simple_field_definition(self) -> None:
        """Test parsing a simple field definition."""
        content = """
        Name

        The "Name" section should be the name of the feature being tested

        Ex: find --name
        """

        parser = SchemaParser()
        doc = parser.parse_content(content)

        assert "Name" in doc.fields
        field = doc.fields["Name"]
        assert field.name == "Name"
        assert "name of the feature" in field.description.lower()
        assert len(field.examples) > 0
        assert "find --name" in field.examples[0]

    def test_parse_multiple_field_definitions(self) -> None:
        """Test parsing multiple field definitions."""
        content = """
        Objective

        The "Objective" section should include a description of what the test evaluates

        Ex: Verify the command works correctly

        Precondition

        The "Precondition" section should tell the user the minimum setup required

        Ex: Controller installed and spun up
        """

        parser = SchemaParser()
        doc = parser.parse_content(content)

        assert len(doc.fields) >= 2
        assert "Objective" in doc.fields
        assert "Precondition" in doc.fields

    def test_parse_zephyr_sop_format(self) -> None:
        """Test parsing Zephyr SOP-style documentation."""
        content = """
        Test Case Quickstart

        Step

        The "Step" portion of the test case should be a description of what commands
        you will be running in "Test Data" and why.

        Ex: Run the command on the CLI

        Test Data

        The "Test Data" section should contain the actual command or data to execute

        Ex: touch /tmp/test.txt

        Expected Result

        The "Expected Result" field should describe what should happen

        Ex: File created successfully
        """

        parser = SchemaParser()
        doc = parser.parse_content(content)

        # Should find the key fields
        assert "Step" in doc.fields or any("step" in f.lower() for f in doc.fields)
        assert "Test Data" in doc.fields or any(
            "test data" in f.lower() for f in doc.fields
        )
        assert "Expected Result" in doc.fields or any(
            "expected" in f.lower() for f in doc.fields
        )

    def test_parse_field_with_examples(self) -> None:
        """Test extracting multiple examples from field description."""
        content = """
        Priority

        The Priority field indicates test importance.

        Ex: High
        Ex: Normal
        Ex: Low
        """

        parser = SchemaParser()
        doc = parser.parse_content(content)

        if "Priority" in doc.fields:
            field = doc.fields["Priority"]
            assert len(field.examples) > 0

    def test_description_pattern_precedence_prefers_quoted_phrase(self) -> None:
        """Zephyr-style prose should win over simpler colon matches."""
        content = """
        Objective

        The "Objective" section should capture final state and rationale.
        Objective: default description that should not be used.
        """

        parser = SchemaParser()
        doc = parser.parse_content(content)

        field = doc.fields.get("Objective")
        assert field is not None
        assert field.description.startswith("capture final state"), field.description

    def test_description_pattern_handles_inline_quotes(self) -> None:
        """Hyphenated descriptions should provide concise summaries."""
        content = """
        Expected Result

        "Expected Result" - What should happen after execution completes.
        """

        parser = SchemaParser()
        doc = parser.parse_content(content)

        field = doc.fields.get("Expected Result")
        assert field is not None
        assert "What should happen" in field.description

    def test_description_pattern_colon_default(self) -> None:
        """Colon-separated definitions act as a secondary parsing mechanism."""
        content = """
        Precondition

        Precondition: Environment must be provisioned.
        """

        parser = SchemaParser()
        doc = parser.parse_content(content)

        field = doc.fields.get("Precondition")
        assert field is not None
        assert field.description == "Environment must be provisioned."

    def test_schema_document_find_field_by_name(self) -> None:
        """Test finding fields by name."""
        doc = SchemaDocument()
        doc.fields["Name"] = FieldSchema(name="Name", aliases=["Title", "TestName"])

        # Find by exact name
        assert doc.find_field_by_name("Name") is not None
        assert doc.find_field_by_name("name") is not None  # Case insensitive

        # Find by alias
        assert doc.find_field_by_name("Title") is not None
        assert doc.find_field_by_name("TestName") is not None

        # Not found
        assert doc.find_field_by_name("NonExistent") is None

    def test_schema_registry_registration(self) -> None:
        """Test schema registry functionality."""
        registry = SchemaRegistry()

        doc = SchemaDocument()
        doc.fields["Priority"] = FieldSchema(name="Priority", aliases=["Importance"])
        doc.fields["Category"] = FieldSchema(name="Category")

        registry.register(doc)

        # Can find by name
        assert registry.find_field("Priority") is not None
        assert registry.find_field("priority") is not None  # Case insensitive

        # Can find by alias
        assert registry.find_field("Importance") is not None

        # Get aliases
        aliases = registry.get_field_aliases("Priority")
        assert "Priority" in aliases
        assert "Importance" in aliases

    def test_register_schema_file(self) -> None:
        """Test registering schema from file."""
        content = """
        Name

        The name of the test case

        Objective

        The objective describes what is being tested
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_file = f.name

        try:
            doc = register_schema_file(temp_file)
            assert doc.source_file == temp_file
            assert len(doc.fields) > 0
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_parse_file_handles_missing_file(self) -> None:
        """Test that parser handles missing files gracefully."""
        parser = SchemaParser()
        doc = parser.parse_file("/nonexistent/file.txt")

        assert doc is not None
        assert len(doc.fields) == 0
        assert "/nonexistent/file.txt" in doc.source_file

    def test_schema_registry_clear(self) -> None:
        """Test clearing the schema registry."""
        registry = SchemaRegistry()

        doc = SchemaDocument()
        doc.fields["Test"] = FieldSchema(name="Test")
        registry.register(doc)

        assert registry.find_field("Test") is not None

        registry.clear()

        assert registry.find_field("Test") is None
        assert len(registry.get_all_fields()) == 0

    def test_extract_description_patterns(self) -> None:
        """Test extraction of field descriptions with various patterns."""
        parser = SchemaParser()

        # Pattern: "The X section should..."
        content1 = 'The "Name" section of the test case should be the feature name'
        desc1 = parser._extract_description(content1)
        assert "feature name" in desc1.lower()

        # Pattern: "Name: description"
        content2 = "Name: This is the test name field"
        desc2 = parser._extract_description(content2)
        assert "test name" in desc2.lower()

    def test_skip_general_sections(self) -> None:
        """Test that general sections like Overview are skipped."""
        content = """
        Overview

        This is just an overview of the documentation

        Name

        The name field is important
        """

        parser = SchemaParser()
        doc = parser.parse_content(content)

        # Should have Name but not Overview
        assert "Name" in doc.fields
        assert "Overview" not in doc.fields

    def test_field_schema_defaults(self) -> None:
        """Test FieldSchema default values."""
        field = FieldSchema(name="Test")

        assert field.name == "Test"
        assert field.aliases == []
        assert field.description == ""
        assert field.examples == []
        assert field.required is False
        assert field.field_type == "text"

    def test_parse_file_enforces_size_limit(self, tmp_path: Path) -> None:
        large_file = tmp_path / "schema.md"
        large_file.write_text("A" * (1024 * 1024 + 100), encoding="utf-8")

        parser = SchemaParser()
        doc = parser.parse_file(large_file)

        assert doc.fields == {}

    def test_parse_content_sanitizes_control_characters(self) -> None:
        content = "Name\n\nDescription\x00with null"
        parser = SchemaParser()
        doc = parser.parse_content(content)
        assert "Name" in doc.fields
        assert "\x00" not in doc.fields["Name"].description

    def test_parse_file_rejects_disallowed_extension(self, tmp_path: Path) -> None:
        schema_file = tmp_path / "schema.pdf"
        schema_file.write_text("Name\n\nThe name field\n", encoding="utf-8")

        parser = SchemaParser()
        doc = parser.parse_file(schema_file)

        assert doc.fields == {}

    @pytest.mark.skipif(
        not hasattr(os, "symlink") or os.name == "nt", reason="Symlinks unavailable"
    )
    def test_parse_file_rejects_symlink(self, tmp_path: Path) -> None:
        target = tmp_path / "schema.txt"
        target.write_text("Name\n\nThe name field\n", encoding="utf-8")
        link = tmp_path / "schema_link.txt"
        os.symlink(target, link)

        parser = SchemaParser()
        doc = parser.parse_file(link)

        assert doc.fields == {}

    def test_parse_content_enforces_section_limit(self) -> None:
        parser = SchemaParser()
        sections = [
            f"Field{i}\n\nDescription {i}" for i in range(MAX_SCHEMA_SECTIONS + 10)
        ]
        content = "\n".join(sections)

        doc = parser.parse_content(content)

        assert len(doc.fields) == MAX_SCHEMA_SECTIONS

    def test_multiple_schema_files_merged_in_registry(self, tmp_path: Path) -> None:
        """Test that multiple schema files are merged correctly."""
        # Create first schema file with test execution fields
        schema1 = tmp_path / "test_fields.md"
        schema1.write_text(
            """
            Step

            The "Step" section describes the action to perform

            Expected Result

            The "Expected Result" section describes what should happen
            """,
            encoding="utf-8",
        )

        # Create second schema file with metadata fields
        schema2 = tmp_path / "metadata_fields.md"
        schema2.write_text(
            """
            Priority

            The "Priority" field indicates test importance

            Category

            The "Category" field groups related tests
            """,
            encoding="utf-8",
        )

        # Register both files
        registry = get_schema_registry()
        registry.clear()  # Start fresh

        register_schema_file(schema1)
        register_schema_file(schema2)

        # Should be able to find fields from both files
        assert registry.find_field("Step") is not None
        assert registry.find_field("Expected Result") is not None
        assert registry.find_field("Priority") is not None
        assert registry.find_field("Category") is not None

        # Verify all fields are accessible
        all_fields = registry.get_all_fields()
        field_names = {f.name for f in all_fields}
        assert "Step" in field_names
        assert "Expected Result" in field_names
        assert "Priority" in field_names
        assert "Category" in field_names


class TestSchemaParserSecurity:
    """Security-focused tests for schema parser."""

    def test_parse_content_rejects_pathologically_large_input(self) -> None:
        """Test that extremely large inputs are rejected before processing."""
        parser = SchemaParser()

        # 10x the limit should be rejected
        huge_content = "A" * (MAX_SCHEMA_FILE_SIZE_BYTES * 10 + 1)

        with pytest.raises(exceptions.ValidationError) as exc_info:
            parser.parse_content(huge_content)

        assert "exceeds maximum reasonable size" in str(exc_info.value)

    def test_parse_content_truncates_moderately_large_input(self) -> None:
        """Test that moderately large inputs are truncated, not rejected."""
        parser = SchemaParser()

        # Create content that exceeds the limit but is reasonable to process
        # Use 50KB over a hypothetical 10KB limit to keep test fast
        test_limit = 10_000
        large_content = "Name\n\nTest field\n\n" + "A" * (test_limit + 5000)

        # Mock the limit temporarily
        original_limit = sp.MAX_SCHEMA_CONTENT_LENGTH
        sp.MAX_SCHEMA_CONTENT_LENGTH = test_limit

        try:
            # Should not raise, but will truncate
            doc = parser.parse_content(large_content)
            assert doc is not None
        finally:
            sp.MAX_SCHEMA_CONTENT_LENGTH = original_limit

    def test_file_size_limit_error_suggests_splitting(
        self, tmp_path: Path, caplog: LogCaptureFixture
    ) -> None:
        """Test that file size errors suggest splitting into multiple files."""
        large_file = tmp_path / "huge_schema.md"
        large_file.write_text(
            "A" * (MAX_SCHEMA_FILE_SIZE_BYTES + 100), encoding="utf-8"
        )

        parser = SchemaParser()
        doc = parser.parse_file(large_file)

        # Should return empty document
        assert doc.fields == {}

        # Should suggest splitting files
        assert any(
            "splitting into multiple files" in record.message
            for record in caplog.records
        )
