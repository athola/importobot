"""Test MongoDB library integration and functionality.

This module tests the MongoDB library integration that replaced the broken
robotframework-mongodblibrary with the modern robot-mongodb-library.
"""

# Import check for RobotMongoDBLibrary compatibility testing
# Using importlib to avoid mypy stub issues
import importlib.util

import pytest

from importobot.core.keywords_registry import RobotFrameworkKeywordRegistry
from importobot.core.pattern_matcher import LibraryDetector, RobotFrameworkLibrary

_MONGODB_AVAILABLE = importlib.util.find_spec("RobotMongoDBLibrary") is not None


class TestMongoDBLibraryIntegration:
    """Test MongoDB library integration and keyword generation."""

    def test_mongodb_library_enum_value(self) -> None:
        """Test that MongoDB library enum has the correct value."""
        assert RobotFrameworkLibrary.MONGODB_LIBRARY.value == "RobotMongoDBLibrary"

    def test_mongodb_library_in_conflict_groups(self) -> None:
        """Test that MongoDB library is properly categorized in conflict groups."""
        conflict_groups = RobotFrameworkLibrary.get_conflict_groups()

        # MongoDB should not be in the web automation conflict group
        web_group = conflict_groups.get("web_automation", set())
        assert RobotFrameworkLibrary.MONGODB_LIBRARY not in web_group

    def test_mongodb_functions_available_in_registry(self) -> None:
        """Test that MongoDB functions are properly registered."""
        mongodb_keywords = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES.get(
            "RobotMongoDBLibrary"
        )

        assert mongodb_keywords is not None
        assert "InsertOne" in mongodb_keywords
        assert "FindOneByID" in mongodb_keywords
        assert "Find" in mongodb_keywords
        assert "Update" in mongodb_keywords
        assert "DeleteOne" in mongodb_keywords
        assert "DeleteOneByID" in mongodb_keywords

    def test_mongodb_keyword_descriptions(self) -> None:
        """Test that MongoDB keywords have proper descriptions."""
        mongodb_keywords = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES[
            "RobotMongoDBLibrary"
        ]

        insert_one = mongodb_keywords["InsertOne"]
        assert "description" in insert_one
        assert "Insert one document" in insert_one["description"]
        assert "collection" in insert_one["description"]

        find_one = mongodb_keywords["FindOneByID"]
        assert "description" in find_one
        assert "Find one document" in find_one["description"]
        assert "ID" in find_one["description"]

    def test_mongodb_keyword_arguments(self) -> None:
        """Test that MongoDB keywords have proper argument definitions."""
        mongodb_keywords = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES[
            "RobotMongoDBLibrary"
        ]

        # Check InsertOne arguments
        insert_one = mongodb_keywords["InsertOne"]
        assert "args" in insert_one
        assert len(insert_one["args"]) == 2  # connection_config, data

        # Check FindOneByID arguments
        find_one = mongodb_keywords["FindOneByID"]
        assert "args" in find_one
        assert len(find_one["args"]) == 2  # connection_config, id

    def test_mongodb_library_detected_from_text(self) -> None:
        """Test MongoDB library can be detected from text containing MongoDB ops."""

        # Test text that should indicate MongoDB usage
        mongodb_text = "connect to mongodb database and insert documents"
        detected_libraries = LibraryDetector.detect_libraries_from_text(mongodb_text)

        # Should detect MongoDB library
        library_values = {lib.value for lib in detected_libraries}
        assert "RobotMongoDBLibrary" in library_values

    def test_mongodb_library_name_in_all_exports(self) -> None:
        """Test that MongoDB functions are properly available in the registry."""
        mongodb_keywords = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES[
            "RobotMongoDBLibrary"
        ]

        # Check that the expected functions are available
        expected_functions = [
            "InsertOne",
            "FindOneByID",
            "Find",
            "Update",
            "DeleteOne",
            "DeleteOneByID",
        ]
        for func in expected_functions:
            assert func in mongodb_keywords, (
                f"Function {func} should be available in MongoDB library"
            )

    def test_legacy_mongodb_library_not_present(self) -> None:
        """Test that the old MongoDBLibrary is not used anymore."""
        # Should not find the old library name in any enum values
        all_lib_values = {lib.value for lib in RobotFrameworkLibrary}
        assert "MongoDBLibrary" not in all_lib_values

    def test_mongodb_function_signatures(self) -> None:
        """Test that MongoDB functions have consistent signature patterns."""
        mongodb_keywords = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES[
            "RobotMongoDBLibrary"
        ]

        # All functions should have connection_config as first argument
        for func_name, func_info in mongodb_keywords.items():
            if func_name not in ["__all__", "__doc__"]:  # Skip metadata
                assert "args" in func_info
                assert (
                    len(func_info["args"]) >= 2
                )  # At least connection_config and one other arg
                assert func_info["args"][0] == "connection_config"

    def test_mongodb_library_compatibility(self) -> None:
        """Test that the MongoDB library integration maintains compatibility."""
        # Test that the library can be imported (basic check)
        if _MONGODB_AVAILABLE:
            # Dynamic import to avoid mypy stub issues
            spec = importlib.util.find_spec("RobotMongoDBLibrary")
            assert spec is not None
            assert spec.loader is not None  # Type guard for mypy
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            assert module is not None
        else:
            pytest.skip("RobotMongoDBLibrary not available for testing")

    def test_mongodb_operations_coverage(self) -> None:
        """Test that all major MongoDB operations are covered."""
        mongodb_keywords = RobotFrameworkKeywordRegistry.KEYWORD_LIBRARIES[
            "RobotMongoDBLibrary"
        ]

        # CRUD operations should be covered
        expected_operations = [
            "InsertOne",
            "FindOneByID",
            "Find",
            "Update",
            "DeleteOne",
            "DeleteOneByID",
        ]

        for operation in expected_operations:
            assert operation in mongodb_keywords, (
                f"Missing MongoDB operation: {operation}"
            )
