"""Parameter analysis and improvement suggestions."""

import re
from typing import Any

from importobot.core.constants import (
    EXPECTED_RESULT_FIELD_NAMES,
    STEP_DESCRIPTION_FIELD_NAMES,
    STEPS_FIELD_NAME,
    TEST_DATA_FIELD_NAMES,
)
from importobot.core.field_definitions import PARAMETERS_FIELDS, TEST_SCRIPT_FIELDS
from importobot.utils.logging import get_logger

logger = get_logger()


class ParameterAnalyzer:
    """Analyzes and suggests improvements for test parameters."""

    def check_parameter_mapping(
        self,
        test_case: dict[str, Any],
        steps: list[dict[str, Any]],
        case_num: int,
        suggestions: list[str],
    ) -> None:
        """Check parameter placeholders and suggest Robot Framework variable mapping."""
        # Extract defined parameters
        defined_parameters = self._extract_defined_parameters(test_case)

        # Collect all text sources that might contain parameters
        text_sources = self._collect_text_sources(test_case, steps)
        detected_params, incomplete_params = self._analyze_parameter_patterns(
            text_sources
        )

        # Additional suggestions for undefined parameters
        undefined_params = self._get_undefined_parameters(
            detected_params, incomplete_params, defined_parameters
        )

        if undefined_params:
            var_list = ", ".join(sorted(undefined_params))
            if len(var_list) > 60:
                suggestions.append(
                    f"Test case {case_num}: Consider adding Robot Framework "
                    f"variable mappings for parameters: {var_list[:60]}..."
                )
            else:
                suggestions.append(
                    f"Test case {case_num}: Consider adding Robot Framework "
                    f"variable mappings for parameters: {var_list}"
                )

            # Suggest specific parameter definitions for undefined parameters
            self._suggest_parameter_definitions(undefined_params, case_num, suggestions)

    def improve_parameters(
        self,
        test_case: dict[str, Any],
        test_index: int,
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Improve parameter definitions and usage in test case."""
        # Initialize parameters field if not present using field definitions
        param_field, _ = PARAMETERS_FIELDS.find_first(test_case)
        if not param_field:
            param_field = "parameters"  # Use canonical name
            test_case[param_field] = []

        # Extract text sources from test steps
        text_sources = self._extract_text_sources(test_case)

        # Detect parameters and references
        param_patterns = self._get_parameter_patterns()
        detected_params = self._extract_parameters_from_text(
            text_sources, param_patterns
        )
        parameter_refs = self._extract_parameter_references_for_improvement(
            text_sources
        )

        # Get existing parameters
        existing_params = self._get_existing_parameters(test_case)
        defined_param_names = {
            param.get("name", "")
            for param in existing_params
            if isinstance(param, dict)
        }

        # Add missing parameter definitions
        new_params = self._create_missing_parameters(
            detected_params | parameter_refs, defined_param_names
        )

        # Add new parameters to test case
        self._add_parameters_to_test_case(test_case, new_params)

        # Record changes
        if new_params:
            self._record_parameter_changes(changes_made, test_index, new_params)

    def _extract_text_sources(self, test_case: dict[str, Any]) -> list[str]:
        """Extract text sources from test case steps."""
        text_sources: list[str] = []
        # Use field definitions to access test script
        script_field, script_data = TEST_SCRIPT_FIELDS.find_first(test_case)
        if script_field and isinstance(script_data, dict):
            steps = script_data.get(STEPS_FIELD_NAME, [])
            field_names = TEST_DATA_FIELD_NAMES + STEP_DESCRIPTION_FIELD_NAMES
            text_sources.extend(
                step[field_name]
                for step in steps
                if isinstance(step, dict)
                for field_name in field_names
                if isinstance(step.get(field_name), str)
            )
        return text_sources

    def _get_existing_parameters(self, test_case: dict[str, Any]) -> list[Any]:
        """Get existing parameters from test case, handling different formats."""
        parameters_field = test_case.get("parameters", [])

        if isinstance(parameters_field, dict):
            # If it's a dict, look for entries, variables, or params arrays
            result = (
                parameters_field.get("entries", [])
                or parameters_field.get("variables", [])
                or parameters_field.get("params", [])
            )
            return list(result)
        if isinstance(parameters_field, list):
            return parameters_field
        return []

    def _create_missing_parameters(
        self, all_params: set[str], defined_param_names: set[str]
    ) -> list[dict[str, Any]]:
        """Create parameter definitions for missing parameters."""
        new_params = []
        for param in all_params:
            if param not in defined_param_names:
                default_value, description = self._suggest_default_value_for_param(
                    param
                )
                new_param = {
                    "name": param,
                    "defaultValue": default_value,
                    "description": description,
                }
                new_params.append(new_param)
        return new_params

    def _add_parameters_to_test_case(
        self, test_case: dict[str, Any], new_params: list[dict[str, Any]]
    ) -> None:
        """Add new parameters to test case, handling different formats."""
        if not new_params:
            return

        if isinstance(test_case["parameters"], dict):
            # Add to the appropriate sub-array
            param_field = test_case["parameters"]
            if "entries" in param_field:
                param_field["entries"].extend(new_params)
            elif "variables" in param_field:
                param_field["variables"].extend(new_params)
            elif "params" in param_field:
                param_field["params"].extend(new_params)
            else:
                # Create entries array if none exists
                param_field["entries"] = new_params
        elif isinstance(test_case["parameters"], list):
            test_case["parameters"].extend(new_params)

    def _record_parameter_changes(
        self,
        changes_made: list[dict[str, Any]],
        test_index: int,
        new_params: list[dict[str, Any]],
    ) -> None:
        """Record parameter addition changes."""
        changes_made.append(
            {
                "type": "parameters_added",
                "location": f"test_case_{test_index}",
                "test_case_index": test_index,
                "field": "parameters",
                "original": None,
                "improved": new_params,
                "reason": f"Added parameter definitions: {len(new_params)} params",
            }
        )

    def _get_parameter_patterns(self) -> list[str]:
        """Get regex patterns for parameter detection."""
        return [
            r"\$\{([^}]+)\}",  # Robot Framework variables: ${var}
            r"\{([^}]+)\}",  # Simple placeholders: {var}
            r"<([^>]+)>",  # Angle bracket placeholders: <var>
            r"\[([^\]]+)\]",  # Square bracket placeholders: [var]
        ]

    def _collect_text_sources(
        self, test_case: dict[str, Any], steps: list[dict[str, Any]]
    ) -> list[str]:
        """Collect all text from test case that might contain parameters."""
        text_sources: list[str] = []

        # From test case itself
        text_sources.extend(
            test_case[field]
            for field in ["name", "description", "summary"]
            if isinstance(test_case.get(field), str)
        )

        relevant_fields = (
            TEST_DATA_FIELD_NAMES
            + STEP_DESCRIPTION_FIELD_NAMES
            + EXPECTED_RESULT_FIELD_NAMES
        )
        text_sources.extend(
            step[field_name]
            for step in steps
            if isinstance(step, dict)
            for field_name in relevant_fields
            if isinstance(step.get(field_name), str)
        )

        return text_sources

    def _extract_parameters_from_text(
        self, text_sources: list[str], param_patterns: list[str]
    ) -> set[str]:
        """Extract parameter names from text using multiple patterns."""
        detected_params = set()

        for text in text_sources:
            if not isinstance(text, str):
                continue

            for pattern in param_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    # Clean up parameter name
                    clean_param = match.strip()
                    if clean_param and len(clean_param) > 1:
                        detected_params.add(clean_param)

        return detected_params

    def _extract_parameter_references_for_improvement(
        self, text_sources: list[str]
    ) -> set[str]:
        """Extract parameter references that need Robot Framework conversion."""
        references = set()
        for text in text_sources:
            # Look for various parameter formats that need improvement
            patterns = [r"\{([^}]+)\}", r"<([^>]+)>", r"\[([^\]]+)\]"]
            for pattern in patterns:
                matches = re.findall(pattern, text)
                references.update(matches)
        return references

    def _convert_to_robot_variable_name(self, param_name: str) -> str:
        """Convert parameter name to Robot Framework variable format."""
        # Remove special characters and spaces, keep alphanumeric and underscores
        clean_name = re.sub(r"[^\w\s]", "", param_name)
        clean_name = re.sub(r"\s+", "_", clean_name.strip())
        return f"${{{clean_name}}}"

    def _extract_defined_parameters(self, test_case: dict[str, Any]) -> set[str]:
        """Extract defined parameter names from test case."""
        defined_parameters = set()
        if "parameters" in test_case and isinstance(test_case["parameters"], list):
            for param in test_case["parameters"]:
                if isinstance(param, dict) and "name" in param:
                    defined_parameters.add(param["name"])
        return defined_parameters

    def _analyze_parameter_patterns(
        self, all_text_sources: list[str]
    ) -> tuple[set[str], set[str]]:
        """Analyze text for parameter patterns and return detected parameters.

        Scan through all text sources to identify parameter patterns and classify
        them as either detected or incomplete parameters.
        """
        detected_params = set()
        incomplete_params = set()

        param_patterns = [
            (r"\$\{([^}]+)\}", "robot"),  # Robot Framework variables
            (r"\{([^}]+)\}", "simple"),  # Simple braces
            (r"<([^>]+)>", "angle"),  # Angle brackets
            (r"\[([^\]]+)\]", "square"),  # Square brackets
        ]

        for text in all_text_sources:
            if not isinstance(text, str):
                continue

            for pattern, pattern_type in param_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    clean_param = match.strip()
                    if clean_param and len(clean_param) > 1:
                        if pattern_type == "robot":
                            detected_params.add(clean_param)
                        else:
                            incomplete_params.add(clean_param)

        return detected_params, incomplete_params

    def _suggest_parameter_improvements(
        self, detected_params: set[str], incomplete_params: set[str], case_num: int
    ) -> list[str]:
        """Generate parameter improvement suggestions."""
        # detected_params parameter is kept for interface consistency
        # but not used in this implementation
        _ = detected_params  # Mark as intentionally unused
        suggestions = []

        # Suggest Robot Framework format for incomplete parameters
        for param in incomplete_params:
            if param in ["username", "password", "host", "file", "content"]:
                suggested_format = f"${{{param}}}"
                if param.startswith("(") and param.endswith(")"):
                    original_format = f"({param})"
                elif param.startswith("<") and param.endswith(">"):
                    original_format = f"<{param}>"
                elif param.startswith("[") and param.endswith("]"):
                    original_format = f"[{param}]"
                else:
                    original_format = f"({param})"

                suggestions.append(
                    f"Test case {case_num}: Replace '{original_format}' with "
                    f"proper syntax '{suggested_format}' for Robot Framework "
                    "compatibility"
                )

        return suggestions

    def _get_undefined_parameters(
        self,
        detected_params: set[str],
        incomplete_params: set[str],
        defined_parameters: set[str],
    ) -> set[str]:
        """Get parameters that are used but not defined."""
        all_used_params = detected_params | incomplete_params
        return all_used_params - defined_parameters

    def _suggest_default_value_for_param(self, param: str) -> tuple[str, str]:
        """Suggest appropriate default value and description based on parameter name."""
        name_lower = param.lower()

        if "file" in name_lower:
            # Handle numbered files like test_file_1, test_file_2
            if any(num in param for num in ["1", "2", "3", "4", "5"]):
                number = re.search(r"\d+", param)
                base_name = re.sub(r"[_\s]*\d+[_\s]*", "", param.lower())
                if number and base_name:
                    default_value = f"{base_name}{number.group()}.txt"
                    description = f"Test file {param} for hash verification operations."
                    return default_value, description
            default_value = f"{param.replace('_', '').lower()}.txt"
            description = f"The {param.replace('_', ' ')} parameter."
            return default_value, description

        if "content" in name_lower:
            content_desc = (
                param.replace("_", " ").replace("content", "").strip() or "testing"
            )
            return "Sample content for testing", f"The content for {content_desc}."

        if "url" in name_lower:
            return (
                f"${{BASE_URL}}/{param.lower()}",
                f"URL parameter for {param.replace('_', ' ')}.",
            )

        if "host" in name_lower:
            return "localhost", f"Host parameter for {param.replace('_', ' ')}."

        if "port" in name_lower:
            return "8080", f"Port parameter for {param.replace('_', ' ')}."

        # Default case
        return f"value_for_{param.lower()}", f"Parameter for {param.replace('_', ' ')}."

    def _suggest_parameter_definitions(
        self, undefined_params: set[str], case_num: int, suggestions: list[str]
    ) -> None:
        """Suggest specific parameter definitions for undefined parameters."""
        for param in sorted(undefined_params):
            default_value, description = self._suggest_default_value_for_param(param)
            param_def = (
                f'{{ "name": "{param}", "defaultValue": "{default_value}", '
                f'"description": "{description}" }}'
            )
            suggestions.append(
                f"Test case {case_num}: Add parameter definition: {param_def}"
            )
