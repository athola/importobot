"""Enhanced lazy loading utilities for efficient data management."""

from __future__ import annotations

import importlib
import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from types import ModuleType


class LazyModule:
    """Lazy module loader that defers imports until first access."""

    def __init__(self, module_name: str, package: Optional[str] = None) -> None:
        """Initialize lazy module loader.

        Args:
            module_name: Name of the module to load lazily
            package: Package name for relative imports
        """
        self._module_name = module_name
        self._package = package
        self._module: Optional[ModuleType] = None
        self._import_error: Optional[ImportError] = None

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
    """Manages optional dependencies with graceful fallbacks."""

    def __init__(
        self,
        module_name: str,
        package_name: Optional[str] = None,
        fallback_message: Optional[str] = None,
    ) -> None:
        """Initialize optional dependency manager.

        Args:
            module_name: Name of the module to import
            package_name: Package name for install instructions
            fallback_message: Custom message when dependency unavailable
        """
        self.module_name = module_name
        self.package_name = package_name or module_name
        self.fallback_message = fallback_message
        self._module: Optional[ModuleType] = None
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
        """Raise informative error about missing dependency."""
        if self.fallback_message:
            message = self.fallback_message
        else:
            message = (
                f"Optional dependency '{self.module_name}' not found. "
                f"Install with: pip install {self.package_name}"
            )
        raise ImportError(message)


# Pre-defined optional dependencies for common use cases
MATPLOTLIB = OptionalDependency(
    "matplotlib",
    fallback_message=(
        "Visualization features require matplotlib. "
        "Install with: pip install 'importobot[viz]'"
    ),
)

NUMPY = OptionalDependency(
    "numpy",
    fallback_message=(
        "Advanced analytics require numpy. "
        "Install with: pip install 'importobot[analytics]'"
    ),
)

PANDAS = OptionalDependency(
    "pandas",
    fallback_message=(
        "Data processing features require pandas. "
        "Install with: pip install 'importobot[data]'"
    ),
)


class LazyDataLoader:
    """Efficient loader for large data structures with caching."""

    @staticmethod
    @lru_cache(maxsize=32)
    def load_templates(template_type: str) -> Dict[str, Any]:
        """Load templates from external files with caching."""
        data_dir = Path(__file__).parent.parent / "data" / "templates"
        template_file = data_dir / f"{template_type}.json"

        if template_file.exists():
            with open(template_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        return {}

    @staticmethod
    @lru_cache(maxsize=16)
    def load_keyword_mappings(library_type: str) -> Dict[str, Any]:
        """Load keyword mappings from external files."""
        data_dir = Path(__file__).parent.parent / "data" / "keywords"
        mapping_file = data_dir / f"{library_type}_mappings.json"

        if mapping_file.exists():
            with open(mapping_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        return {}

    @staticmethod
    def create_summary_comment(
        data_structure: Dict[str, Any], max_items: int = 3
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
