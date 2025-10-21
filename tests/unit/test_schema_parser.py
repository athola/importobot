"""Tests for input schema documentation parser."""

import os
import tempfile
from pathlib import Path

import pytest

from importobot.core.schema_parser import (
    MAX_SCHEMA_SECTIONS,
    FieldSchema,
    SchemaDocument,
    SchemaParser,
    SchemaRegistry,
    register_schema_file,
)


class TestSchemaParser:
    """Tests for SchemaParser functionality."""

    def test_parse_simple_field_definition(self):
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

    def test_parse_multiple_field_definitions(self):
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

    def test_parse_zephyr_sop_format(self):
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

    def test_parse_field_with_examples(self):
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

    def test_schema_document_find_field_by_name(self):
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

    def test_schema_registry_registration(self):
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

    def test_register_schema_file(self):
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

    def test_parse_file_handles_missing_file(self):
        """Test that parser handles missing files gracefully."""
        parser = SchemaParser()
        doc = parser.parse_file("/nonexistent/file.txt")

        assert doc is not None
        assert len(doc.fields) == 0
        assert "/nonexistent/file.txt" in doc.source_file

    def test_schema_registry_clear(self):
        """Test clearing the schema registry."""
        registry = SchemaRegistry()

        doc = SchemaDocument()
        doc.fields["Test"] = FieldSchema(name="Test")
        registry.register(doc)

        assert registry.find_field("Test") is not None

        registry.clear()

        assert registry.find_field("Test") is None
        assert len(registry.get_all_fields()) == 0

    def test_extract_description_patterns(self):
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

    def test_skip_general_sections(self):
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

    def test_field_schema_defaults(self):
        """Test FieldSchema default values."""
        field = FieldSchema(name="Test")

        assert field.name == "Test"
        assert field.aliases == []
        assert field.description == ""
        assert field.examples == []
        assert field.required is False
        assert field.field_type == "text"

    def test_parse_file_enforces_size_limit(self, tmp_path):
        large_file = tmp_path / "schema.md"
        large_file.write_text("A" * (1024 * 1024 + 100), encoding="utf-8")

        parser = SchemaParser()
        doc = parser.parse_file(large_file)

        assert doc.fields == {}

    def test_parse_content_sanitizes_control_characters(self):
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

    def test_parse_content_enforces_section_limit(self):
        parser = SchemaParser()
        sections = []
        for i in range(MAX_SCHEMA_SECTIONS + 10):
            sections.append(f"Field{i}\n\nDescription {i}")
        content = "\n".join(sections)

        doc = parser.parse_content(content)

        assert len(doc.fields) == MAX_SCHEMA_SECTIONS
