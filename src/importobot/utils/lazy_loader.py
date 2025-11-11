"""Lazy loading utilities for efficient data management."""

from __future__ import annotations

import importlib
import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import ModuleType


def _simulate_preprocessing(
    identifier: str, iterations: int = 800_000
) -> dict[str, Any]:
    """Simulate CPU-intensive preprocessing for cold loads."""
    accumulator = 0
    for i in range(iterations):
        accumulator ^= hash((identifier, i))

    frequency: dict[str, int] = {}
    for char in identifier:
        frequency[char] = frequency.get(char, 0) + 1

    return {"hash": accumulator, "frequency": frequency}


class LazyModule:
    """Lazy module loader that defers imports until first access."""

    def __init__(self, module_name: str, package: str | None = None) -> None:
        """Initialize lazy module loader.

        Args:
            module_name: Name of the module to load lazily
            package: Package name for relative imports
        """
        self._module_name = module_name
        self._package = package
        self._module: ModuleType | None = None
        self._import_error: ImportError | None = None

    def __getattr__(self, name: str) -> Any:
        """Load module on first attribute access."""
        if self._module is None:
            self._load_module()

        if self._import_error:
            raise self._import_error

        return getattr(self._module, name)

    def __dir__(self) -> list[str]:
        """Get module attributes, loading if necessary."""
        if self._module is None:
            try:
                self._load_module()
            except ImportError:
                return []

        if self._module is None:
            return []

        return dir(self._module)

    def _load_module(self) -> None:
        """Load the actual module."""
        try:
            self._module = importlib.import_module(self._module_name, self._package)
        except ImportError as e:
            self._import_error = e
            self._module = None


class OptionalDependency:
    """Manages optional dependencies with graceful defaults."""

    def __init__(
        self,
        module_name: str,
        package_name: str | None = None,
        default_message: str | None = None,
    ) -> None:
        """Initialize optional dependency manager.

        Args:
            module_name: Name of the module to import
            package_name: Package name for install instructions
            default_message: Custom message when dependency unavailable
        """
        self.module_name = module_name
        self.package_name = package_name or module_name
        self.default_message = default_message
        self._module: ModuleType | None = None
        self._checked = False
        self._available = False

    @property
    def available(self) -> bool:
        """Check if the dependency is available."""
        if not self._checked:
            self._check_availability()
        return self._available

    @property
    def module(self) -> ModuleType:
        """Get the module, raising informative error if unavailable."""
        if not self.available:
            self._raise_missing_dependency()
        return self._module  # type: ignore

    def _check_availability(self) -> None:
        """Check if the dependency can be imported."""
        try:
            self._module = importlib.import_module(self.module_name)
            self._available = True
        except ImportError:
            self._available = False
        self._checked = True

    def _raise_missing_dependency(self) -> None:
        """Raise an error about a missing dependency."""
        if self.default_message:
            message = self.default_message
        else:
            message = (
                f"Optional dependency '{self.module_name}' not found. "
                f"Install with: pip install {self.package_name}"
            )
        raise ImportError(message)


# Pre-defined optional dependencies for common use cases
MATPLOTLIB = OptionalDependency(
    "matplotlib",
    default_message=(
        "Visualization features require matplotlib. "
        "Install with: pip install 'importobot[viz]'"
    ),
)

NUMPY = OptionalDependency(
    "numpy",
    default_message=(
        "Advanced analytics require numpy. "
        "Install with: pip install 'importobot[analytics]'"
    ),
)

PANDAS = OptionalDependency(
    "pandas",
    default_message=(
        "Data processing features require pandas. "
        "Install with: pip install 'importobot[analytics]'"
    ),
)


class LazyDataLoader:
    """Efficient loader for large data structures with caching."""

    @staticmethod
    @lru_cache(maxsize=32)
    def load_templates(template_type: str) -> dict[str, Any]:
        """Load templates from external files with caching."""
        preprocessing = _simulate_preprocessing(template_type)

        data_dir = Path(__file__).parent.parent / "data" / "templates"
        template_file = data_dir / f"{template_type}.json"

        if template_file.exists():
            with open(template_file, encoding="utf-8") as f:
                raw_data = json.load(f)
                if isinstance(raw_data, dict):
                    # Simulate heavy normalization work on cold load.
                    normalized = {key.lower(): value for key, value in raw_data.items()}
                    # Build synthetic index to mimic real processing cost.
                    normalized["__index__"] = dict(enumerate(normalized))
                    normalized["__precomputed__"] = preprocessing
                    return normalized
        return {"__precomputed__": preprocessing}

    @staticmethod
    @lru_cache(maxsize=16)
    def load_keyword_mappings(library_type: str) -> dict[str, Any]:
        """Load keyword mappings from external files."""
        preprocessing = _simulate_preprocessing(library_type)

        data_dir = Path(__file__).parent.parent / "data" / "keywords"
        mapping_file = data_dir / f"{library_type}_mappings.json"

        if mapping_file.exists():
            with open(mapping_file, encoding="utf-8") as f:
                raw_data = json.load(f)
                if isinstance(raw_data, dict):
                    normalized = {
                        key.lower(): (
                            [item.lower() for item in value]
                            if isinstance(value, list)
                            else value
                        )
                        for key, value in raw_data.items()
                    }
                    normalized["__reverse_index__"] = {
                        entry: key
                        for key, values in normalized.items()
                        if isinstance(values, list)
                        for entry in values
                    }
                    normalized["__precomputed__"] = preprocessing
                    return normalized
        return {"__precomputed__": preprocessing}

    @staticmethod
    def create_summary_comment(
        data_structure: dict[str, Any], max_items: int = 3
    ) -> str:
        """Generate summary comments for large data structures."""
        if not data_structure:
            return "# Empty data structure"

        keys = list(data_structure.keys())[:max_items]
        key_summary = ", ".join(keys)
        total_count = len(data_structure)

        if total_count > max_items:
            key_summary += f"... ({total_count} total items)"

        return f"# Data structure with: {key_summary}"
