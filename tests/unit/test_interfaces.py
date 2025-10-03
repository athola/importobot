"""Unit tests for core interfaces module.

Tests the abstract base classes and interfaces used across importobot.
Following TDD principles with interface contract validation.
"""

from abc import ABC
from typing import Any

import pytest

from importobot.core.interfaces import (
    ConversionEngine,
    KeywordGenerator,
    SuggestionEngine,
    TestFileParser,
)


class TestTestFileParserInterface:
    """Test TestFileParser interface definition."""

    def test_test_file_parser_is_abstract_base_class(self):
        """Test that TestFileParser is an abstract base class."""
        assert issubclass(TestFileParser, ABC)

    def test_test_file_parser_cannot_be_instantiated(self):
        """Test that TestFileParser cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            # pylint: disable=abstract-class-instantiated
            TestFileParser()  # type: ignore[abstract]

    def test_test_file_parser_has_required_abstract_methods(self):
        """Test that TestFileParser has the required abstract methods."""
        abstract_methods = TestFileParser.__abstractmethods__
        expected_methods = {"find_tests", "find_steps"}
        assert abstract_methods == expected_methods

    def test_test_file_parser_find_tests_signature(self):
        """Test that find_tests method has correct signature."""
        method = TestFileParser.find_tests
        assert hasattr(method, "__annotations__")
        annotations = method.__annotations__
        assert "data" in annotations
        assert "return" in annotations


class TestKeywordGeneratorInterface:
    """Test KeywordGenerator interface definition."""

    def test_keyword_generator_is_abstract_base_class(self):
        """Test that KeywordGenerator is an abstract base class."""
        assert issubclass(KeywordGenerator, ABC)

    def test_keyword_generator_cannot_be_instantiated(self):
        """Test that KeywordGenerator cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            # pylint: disable=abstract-class-instantiated
            KeywordGenerator()  # type: ignore[abstract]

    def test_keyword_generator_has_required_abstract_methods(self):
        """Test that KeywordGenerator has the required abstract methods."""
        abstract_methods = KeywordGenerator.__abstractmethods__
        expected_methods = {
            "generate_test_case",
            "generate_step_keywords",
            "detect_libraries",
        }
        assert abstract_methods == expected_methods

    def test_keyword_generator_method_signatures(self):
        """Test that KeywordGenerator methods have correct signatures."""
        # Test generate_test_case signature
        method = KeywordGenerator.generate_test_case
        assert hasattr(method, "__annotations__")
        annotations = method.__annotations__
        assert "test_data" in annotations
        assert "return" in annotations

        # Test generate_step_keywords signature
        method = KeywordGenerator.generate_step_keywords  # type: ignore[assignment]
        assert hasattr(method, "__annotations__")
        annotations = method.__annotations__
        assert "step" in annotations
        assert "return" in annotations

        # Test detect_libraries signature
        method = KeywordGenerator.detect_libraries  # type: ignore[assignment]
        assert hasattr(method, "__annotations__")
        annotations = method.__annotations__
        assert "steps" in annotations
        assert "return" in annotations


class TestSuggestionEngineInterface:
    """Test SuggestionEngine interface definition."""

    def test_suggestion_engine_is_abstract_base_class(self):
        """Test that SuggestionEngine is an abstract base class."""
        assert issubclass(SuggestionEngine, ABC)

    def test_suggestion_engine_cannot_be_instantiated(self):
        """Test that SuggestionEngine cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            # pylint: disable=abstract-class-instantiated
            SuggestionEngine()  # type: ignore[abstract]

    def test_suggestion_engine_has_required_abstract_methods(self):
        """Test that SuggestionEngine has the required abstract methods."""
        abstract_methods = SuggestionEngine.__abstractmethods__
        expected_methods = {"get_suggestions", "apply_suggestions"}
        assert abstract_methods == expected_methods

    def test_suggestion_engine_method_signatures(self):
        """Test that SuggestionEngine methods have correct signatures."""
        # Test get_suggestions signature
        method = SuggestionEngine.get_suggestions
        assert hasattr(method, "__annotations__")
        annotations = method.__annotations__
        assert "json_data" in annotations
        assert "return" in annotations

        # Test apply_suggestions signature
        method = SuggestionEngine.apply_suggestions  # type: ignore[assignment]
        assert hasattr(method, "__annotations__")
        annotations = method.__annotations__
        assert "json_data" in annotations
        assert "return" in annotations


class TestConversionEngineInterface:
    """Test ConversionEngine interface definition."""

    def test_conversion_engine_is_abstract_base_class(self):
        """Test that ConversionEngine is an abstract base class."""
        assert issubclass(ConversionEngine, ABC)

    def test_conversion_engine_cannot_be_instantiated(self):
        """Test that ConversionEngine cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            # pylint: disable=abstract-class-instantiated
            ConversionEngine()  # type: ignore[abstract]

    def test_conversion_engine_has_required_abstract_methods(self):
        """Test that ConversionEngine has the required abstract methods."""
        abstract_methods = ConversionEngine.__abstractmethods__
        expected_methods = {"convert"}
        assert abstract_methods == expected_methods

    def test_conversion_engine_method_signature(self):
        """Test that ConversionEngine convert method has correct signature."""
        method = ConversionEngine.convert
        assert hasattr(method, "__annotations__")
        annotations = method.__annotations__
        assert "json_data" in annotations
        assert "return" in annotations


class MockTestFileParser(TestFileParser):
    """Mock implementation of TestFileParser for testing."""

    def find_tests(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    def find_steps(self, test_data: dict[str, Any]) -> list[dict[str, Any]]:
        return []


class MockKeywordGenerator(KeywordGenerator):
    """Mock implementation of KeywordGenerator for testing."""

    def generate_test_case(self, test_data: dict[str, Any]) -> list[str]:
        return []

    def generate_step_keywords(self, step: dict[str, Any]) -> list[str]:
        return []

    def detect_libraries(self, steps: list[dict[str, Any]]) -> set[str]:
        return set()


class MockSuggestionEngine(SuggestionEngine):
    """Mock implementation of SuggestionEngine for testing."""

    def get_suggestions(self, json_data: Any) -> list[str]:
        return []

    def apply_suggestions(self, json_data: Any) -> tuple[Any, list[dict[str, Any]]]:
        return json_data, []


class MockConversionEngine(ConversionEngine):
    """Mock implementation of ConversionEngine for testing."""

    def convert(self, json_data: dict[str, Any]) -> str:
        return ""


class TestInterfaceImplementation:
    """Test that interfaces can be properly implemented."""

    def test_test_file_parser_can_be_implemented(self):
        """Test that TestFileParser can be implemented."""
        parser = MockTestFileParser()
        assert isinstance(parser, TestFileParser)

        # Test methods can be called
        result_tests = parser.find_tests({})
        assert isinstance(result_tests, list)

        result_steps = parser.find_steps({})
        assert isinstance(result_steps, list)

    def test_keyword_generator_can_be_implemented(self):
        """Test that KeywordGenerator can be implemented."""
        generator = MockKeywordGenerator()
        assert isinstance(generator, KeywordGenerator)

        # Test methods can be called
        result_case = generator.generate_test_case({})
        assert isinstance(result_case, list)

        result_keywords = generator.generate_step_keywords({})
        assert isinstance(result_keywords, list)

        result_libraries = generator.detect_libraries([])
        assert isinstance(result_libraries, set)

    def test_suggestion_engine_can_be_implemented(self):
        """Test that SuggestionEngine can be implemented."""
        engine = MockSuggestionEngine()
        assert isinstance(engine, SuggestionEngine)

        # Test methods can be called
        suggestions = engine.get_suggestions({})
        assert isinstance(suggestions, list)

        _, changes = engine.apply_suggestions({})
        assert isinstance(changes, list)

    def test_conversion_engine_can_be_implemented(self):
        """Test that ConversionEngine can be implemented."""
        engine = MockConversionEngine()
        assert isinstance(engine, ConversionEngine)

        # Test methods can be called
        result = engine.convert({})
        assert isinstance(result, str)


class TestInterfaceInheritance:
    """Test interface inheritance patterns."""

    def test_all_interfaces_inherit_from_abc(self):
        """Test that all interfaces inherit from ABC."""
        interfaces = [
            TestFileParser,
            KeywordGenerator,
            SuggestionEngine,
            ConversionEngine,
        ]

        for interface in interfaces:
            assert issubclass(interface, ABC)

    def test_interfaces_define_expected_contracts(self):
        """Test that interfaces define the expected method contracts."""
        # TestFileParser should have methods for finding tests and steps
        assert hasattr(TestFileParser, "find_tests")
        assert hasattr(TestFileParser, "find_steps")

        # KeywordGenerator should have methods for generating keywords and detecting
        # libraries
        assert hasattr(KeywordGenerator, "generate_test_case")
        assert hasattr(KeywordGenerator, "generate_step_keywords")
        assert hasattr(KeywordGenerator, "detect_libraries")

        # SuggestionEngine should have methods for getting and applying suggestions
        assert hasattr(SuggestionEngine, "get_suggestions")
        assert hasattr(SuggestionEngine, "apply_suggestions")

        # ConversionEngine should have a convert method
        assert hasattr(ConversionEngine, "convert")

    def test_interface_method_documentation(self):
        """Test that interface methods have proper documentation."""
        # Check that abstract methods have docstrings
        assert TestFileParser.find_tests.__doc__ is not None
        assert TestFileParser.find_steps.__doc__ is not None
        assert KeywordGenerator.generate_test_case.__doc__ is not None
        assert KeywordGenerator.generate_step_keywords.__doc__ is not None
        assert KeywordGenerator.detect_libraries.__doc__ is not None
        assert SuggestionEngine.get_suggestions.__doc__ is not None
        assert SuggestionEngine.apply_suggestions.__doc__ is not None
        assert ConversionEngine.convert.__doc__ is not None
