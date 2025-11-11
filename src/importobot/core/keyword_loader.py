"""Load keyword libraries from external JSON configuration files."""

import json
from pathlib import Path
from typing import Any

from importobot.utils.defaults import LIBRARY_MAPPING
from importobot.utils.logging import get_logger
from importobot.utils.security import extract_security_warnings

logger = get_logger()


class KeywordLibraryLoader:
    """Manages loading keyword libraries from external JSON configuration files."""

    def __init__(self) -> None:
        """Initialize the loader with the keywords data directory."""
        self.data_dir = Path(__file__).parent.parent / "data" / "keywords"
        self._cache: dict[str, dict[str, Any]] = {}
        self.logger = logger

    def load_library(self, library_name: str) -> dict[str, Any]:
        """Load a specific keyword library configuration."""
        if library_name in self._cache:
            cached_result = self._cache[library_name]
            return cached_result if isinstance(cached_result, dict) else {}

        # Use configurable library mapping
        filename_map = {}
        for canonical_name, aliases in LIBRARY_MAPPING.library_aliases.items():
            json_filename = f"{canonical_name}.json"
            for alias in aliases:
                filename_map[alias] = json_filename

        filename = filename_map.get(library_name)
        if not filename:
            available_libraries = ", ".join(filename_map.keys())
            self.logger.warning(
                "No configuration file found for library: '%s'. "
                "Available libraries: %s",
                library_name,
                available_libraries,
            )
            return {}

        filepath = self.data_dir / filename
        if not filepath.exists():
            self.logger.warning(
                "Configuration file not found: %s. "
                "Expected library config for '%s' but file is missing. "
                "Please ensure data directory exists with required JSON files.",
                filepath,
                library_name,
            )
            return {}

        try:
            with open(filepath, encoding="utf-8") as f:
                config_raw = json.load(f)
                config = config_raw if isinstance(config_raw, dict) else {}
                self._cache[library_name] = config
                return config
        except json.JSONDecodeError as e:
            self.logger.error(
                "Failed to parse JSON for keyword library '%s' from %s: "
                "Line %d, Column %d: %s. "
                "Please check the JSON syntax in the configuration file.",
                library_name,
                filepath,
                e.lineno,
                e.colno,
                e.msg,
            )
            return {}
        except OSError as e:
            self.logger.error(
                "Failed to read keyword library '%s' from %s: %s. "
                "Check file permissions and ensure the file is accessible.",
                library_name,
                filepath,
                e,
            )
            return {}

    def load_all_libraries(self) -> dict[str, dict[str, Any]]:
        """Load all available keyword library configurations."""
        libraries: dict[str, dict[str, Any]] = {}

        if not self.data_dir.exists():
            self.logger.warning(
                "Keywords data directory not found: %s. "
                "No keyword libraries will be available. Please create directory "
                "and add JSON configuration files for keyword libraries.",
                self.data_dir,
            )
            return libraries

        for json_file in self.data_dir.glob("*.json"):
            config = self._load_library_from_path(json_file)
            if not config:
                continue
            library_name = config.get("library_name", json_file.stem)
            libraries[library_name] = config

        return libraries

    def _load_library_from_path(self, json_file: Path) -> dict[str, Any] | None:
        """Load a single library configuration file."""
        try:
            with open(json_file, encoding="utf-8") as file_handle:
                config = json.load(file_handle)
        except json.JSONDecodeError as error:
            self.logger.error(
                "Failed to parse JSON in %s: Line %d, Column %d: %s. "
                "Skipping this library configuration.",
                json_file,
                error.lineno,
                error.colno,
                error.msg,
            )
            return None
        except OSError as error:
            self.logger.error(
                "Failed to read %s: %s. "
                "Check permissions and accessibility. Skipping this config.",
                json_file,
                error,
            )
            return None

        return config if isinstance(config, dict) else None

    def get_keywords_for_library(self, library_name: str) -> dict[str, dict[str, Any]]:
        """Retrieve all keywords for a specific library."""
        config = self.load_library(library_name)
        keywords_raw = config.get("keywords", {})
        return keywords_raw if isinstance(keywords_raw, dict) else {}

    def get_available_libraries(self) -> list[str]:
        """Retrieve a list of available library names."""
        libraries = self.load_all_libraries()
        return list(libraries.keys())

    def get_security_warnings_for_keyword(
        self, library: str, keyword: str
    ) -> list[str]:
        """Retrieve security warnings for a specific keyword."""
        warnings = []
        keywords = self.get_keywords_for_library(library)

        if keyword in keywords:
            keyword_info = keywords[keyword]
            warnings.extend(extract_security_warnings(keyword_info))

        return warnings

    def refresh_cache(self) -> None:
        """Clear the cache to force a reload of configurations."""
        self._cache.clear()
        self.logger.info("Keyword library cache cleared")

    def validate_configurations(self) -> dict[str, list[str]]:
        """Validate all keyword library configurations."""
        validation_results = {}

        for json_file in self.data_dir.glob("*.json"):
            errors = self._validate_single_configuration(json_file)
            validation_results[json_file.name] = errors

        return validation_results

    def _validate_single_configuration(self, json_file: Path) -> list[str]:
        """Validate a single configuration file."""
        try:
            with open(json_file, encoding="utf-8") as f:
                config = json.load(f)
            return self._validate_config_structure(config)
        except (OSError, json.JSONDecodeError) as e:
            return [f"Failed to parse JSON: {e}"]

    def _validate_config_structure(self, config: dict[str, Any]) -> list[str]:
        """Validate the structure of a configuration object."""
        errors = []

        # Validate required fields
        errors.extend(self._validate_required_fields(config))

        # Validate keyword structure
        errors.extend(self._validate_keywords_structure(config))

        return errors

    def _validate_required_fields(self, config: dict[str, Any]) -> list[str]:
        """Validate required top-level fields."""
        errors = []
        if "library_name" not in config:
            errors.append("Missing required field: library_name")
        if "keywords" not in config:
            errors.append("Missing required field: keywords")
        elif not isinstance(config["keywords"], dict):
            errors.append("keywords field must be a dictionary")
        return errors

    def _validate_keywords_structure(self, config: dict[str, Any]) -> list[str]:
        """Validate the structure of keywords within the configuration."""
        errors = []
        for keyword_name, keyword_info in config.get("keywords", {}).items():
            if not isinstance(keyword_info, dict):
                errors.append(f"Keyword {keyword_name} is not a dictionary")
                continue

            if "description" not in keyword_info:
                errors.append(f"Keyword {keyword_name} missing description")
            if "args" not in keyword_info:
                errors.append(f"Keyword {keyword_name} missing args")
            elif not isinstance(keyword_info["args"], list):
                errors.append(f"Keyword {keyword_name} args must be a list")
        return errors
