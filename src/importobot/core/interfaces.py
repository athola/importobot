"""Interfaces for modular test conversion components."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Tuple


class TestFileParser(ABC):
    """Interface for parsing test files in various formats."""

    @abstractmethod
    def find_tests(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find test structures anywhere in JSON, regardless of format."""
        raise NotImplementedError

    @abstractmethod
    def find_steps(self, test_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find step structures anywhere in test data."""
        raise NotImplementedError


class KeywordGenerator(ABC):
    """Interface for generating Robot Framework keywords."""

    @abstractmethod
    def generate_test_case(self, test_data: Dict[str, Any]) -> List[str]:
        """Generate Robot Framework test case."""
        raise NotImplementedError

    @abstractmethod
    def generate_step_keywords(self, step: Dict[str, Any]) -> List[str]:
        """Generate Robot Framework keywords for a step."""
        raise NotImplementedError

    @abstractmethod
    def detect_libraries(self, steps: List[Dict[str, Any]]) -> Set[str]:
        """Detect required Robot Framework libraries from step content."""
        raise NotImplementedError


class SuggestionEngine(ABC):
    """Interface for generating improvement suggestions for test files."""

    @abstractmethod
    def get_suggestions(self, json_data: Dict[str, Any]) -> List[str]:
        """Generate suggestions for improving JSON test data."""
        raise NotImplementedError

    @abstractmethod
    def apply_suggestions(
        self, json_data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Apply automatic improvements to JSON test data."""
        raise NotImplementedError


class ConversionEngine(ABC):
    """Interface for orchestrating the conversion process."""

    @abstractmethod
    def convert(self, json_data: Dict[str, Any]) -> str:
        """Convert JSON data to Robot Framework format."""
        raise NotImplementedError
