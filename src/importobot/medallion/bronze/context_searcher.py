"""Context-aware search algorithms for format-specific patterns."""

from __future__ import annotations

from typing import Any

from .format_models import EvidenceWeight


class ContextSearcher:
    """Provides context-aware search for format-specific patterns."""

    @staticmethod
    def search_with_testlink_context(data: dict[str, Any], key: str) -> dict[str, Any]:
        """TestLink-specific context search - accept XML export patterns."""
        # TestLink XML has testsuites -> testsuite -> testcase structure
        if key == "testsuites" and key in data:
            return {
                "found": True,
                "at_root": True,
                "appropriate_nesting": True,
                "context_info": "at root level (TestLink XML export)",
            }

        if (
            key == "testsuite"
            and "testsuites" in data
            and isinstance(data["testsuites"], list)
        ):
            # Look for testsuite nested under testsuites
            for suite_container in data["testsuites"]:
                if isinstance(suite_container, dict) and "testsuite" in suite_container:
                    return {
                        "found": True,
                        "at_root": False,
                        "appropriate_nesting": True,
                        "context_info": "nested under testsuites (TestLink XML)",
                    }

        # Generic search for other TestLink keys
        return ContextSearcher.search_with_generic_context(data, key)

    @staticmethod
    def search_with_jira_context(data: dict[str, Any], key: str) -> dict[str, Any]:
        """JIRA-specific context search."""
        # JIRA structure: issues -> array of issue objects
        if key == "issues" and key in data:
            return {
                "found": True,
                "at_root": True,
                "appropriate_nesting": True,
                "context_info": "at root level (JIRA API response)",
            }

        # For single JIRA issue structure (no issues wrapper)
        if key == "issues" and "key" in data and "fields" in data:
            # This is a single JIRA issue, treat as if "issues" is present
            fields = data.get("fields", {})
            if isinstance(fields, dict):
                jira_indicators = ["issuetype", "summary", "customfield"]
                if any(
                    indicator in str(fields).lower() for indicator in jira_indicators
                ):
                    return {
                        "found": True,
                        "at_root": True,
                        "appropriate_nesting": True,
                        "context_info": (
                            "single JIRA issue structure (no issues wrapper)"
                        ),
                    }

        # Look for JIRA-specific keys in appropriate context
        return ContextSearcher.search_with_generic_context(data, key)

    @staticmethod
    def search_with_testrail_context(data: dict[str, Any], key: str) -> dict[str, Any]:
        """TestRail-specific context search."""
        # TestRail API responses have runs/tests/cases at root
        if key in ["runs", "tests", "cases"] and key in data:
            return {
                "found": True,
                "at_root": True,
                "appropriate_nesting": True,
                "context_info": "at root level (TestRail API response)",
            }

        # Look for TestRail IDs nested in appropriate structures
        if key in ["suite_id", "project_id", "milestone_id"]:
            for root_key, root_value in data.items():
                if root_key in ["runs", "tests", "cases"] and isinstance(
                    root_value, list
                ):
                    for item in root_value:
                        if isinstance(item, dict) and key in item:
                            return {
                                "found": True,
                                "at_root": False,
                                "appropriate_nesting": True,
                                "context_info": (
                                    f"nested in {root_key} (TestRail structure)"
                                ),
                            }

        return {
            "found": False,
            "at_root": False,
            "appropriate_nesting": False,
            "context_info": "not found",
        }

    @staticmethod
    def search_with_generic_context(data: dict[str, Any], key: str) -> dict[str, Any]:
        """Search with generic context as default behavior."""

        def search_recursive(
            obj: Any, target_key: str, path: str = ""
        ) -> dict[str, Any]:
            """Perform simple recursive search with basic context info."""
            if isinstance(obj, dict):
                if target_key in obj:
                    level = "root" if not path else f"nested at {path}"
                    return {
                        "found": True,
                        "at_root": not path,
                        "appropriate_nesting": True,
                        "context_info": level,
                    }
                for k, v in obj.items():
                    result = search_recursive(
                        v, target_key, f"{path}.{k}" if path else k
                    )
                    if result["found"]:
                        return result
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    result = search_recursive(
                        item, target_key, f"{path}[{i}]" if path else f"[{i}]"
                    )
                    if result["found"]:
                        return result

            return {
                "found": False,
                "at_root": False,
                "appropriate_nesting": False,
                "context_info": "not found",
            }

        return search_recursive(data, key)

    @staticmethod
    def get_evidence_weight_for_key(
        key: str, format_name: str
    ) -> tuple[EvidenceWeight, float]:
        """Determine the appropriate evidence weight and confidence for a key.

        Args:
            key: The key to evaluate
            format_name: The format being considered

        Returns:
            Tuple of evidence weight and confidence value based on specificity.
        """
        # Define highly specific keys that are unique to certain formats
        unique_indicators = {
            "jira_xray": ["testExecutions", "testInfo", "evidences"],
            "testrail": ["suite_id", "project_id", "milestone_id"],
            "testlink": ["testsuites", "testsuite"],
            "zephyr": ["testCase", "execution", "cycle"],
        }

        # Check if this key is unique to this format
        format_indicators = unique_indicators.get(format_name.lower(), [])
        if key in format_indicators:
            return EvidenceWeight.STRONG, 0.95

        # Common but somewhat specific keys
        specific_indicators = [
            "tests",
            "runs",
            "cases",
            "issues",
            "steps",
            "customfield",
            "summary",
            "description",
            "status",
        ]
        if key in specific_indicators:
            return EvidenceWeight.MODERATE, 0.75

        # Generic keys that appear in many formats
        return EvidenceWeight.WEAK, 0.5


__all__ = ["ContextSearcher"]
