"""Comparison and result analysis suggestions."""

import re
import shlex
from typing import Any

from importobot.core.constants import STEPS_FIELD_NAME
from importobot.core.field_definitions import (
    STEP_ACTION_FIELDS,
    STEP_DATA_FIELDS,
    TEST_SCRIPT_FIELDS,
    TEST_STEP_FIELDS,
    get_field_value,
)
from importobot.utils.logging import get_logger
from importobot.utils.step_processing import collect_command_steps

logger = get_logger()


class ComparisonAnalyzer:
    """Analyzes and suggests improvements for result comparisons."""

    def check_result_comparison_opportunities(
        self, steps: list[dict[str, Any]], case_num: int, suggestions: list[str]
    ) -> None:
        """Check for opportunities to add result comparison steps."""
        command_steps = self._collect_command_steps(steps)
        comparison_candidates = self._group_comparable_commands(command_steps)

        if len(comparison_candidates) >= 2 and not self._comparison_step_exists(steps):
            self._suggest_comparison(comparison_candidates, case_num, suggestions)

    def _collect_command_steps(
        self, steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Collect steps that contain command execution."""
        return collect_command_steps(steps)

    def _comparison_step_exists(self, steps: list[dict[str, Any]]) -> bool:
        """Check whether a generated comparison step already exists."""
        for step in steps:
            if not isinstance(step, dict):
                continue
            metadata = step.get("metadata")
            if (
                isinstance(metadata, dict)
                and metadata.get("generator") == "command_comparison"
            ):
                return True
        return False

    def _group_comparable_commands(
        self, command_steps: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Group commands that share a comparable command signature."""
        grouped: dict[str, list[dict[str, Any]]] = {}
        for step in command_steps:
            if not isinstance(step, dict):
                continue
            command_text = get_field_value(step, STEP_DATA_FIELDS)
            if not command_text:
                command_text = get_field_value(step, STEP_ACTION_FIELDS)

            if command_text:
                content = command_text.lower()
                if not self._is_comparison_candidate(content, step):
                    continue
                signature = self._normalize_command_signature(command_text)
                if not signature:
                    continue
                grouped.setdefault(signature, []).append(
                    {"step": step, "command": command_text, "signature": signature}
                )
        # Flatten but keep signature info
        comparable = [
            entry
            for entries in grouped.values()
            if len(entries) >= 2
            for entry in entries
        ]
        return comparable

    def _is_comparison_candidate(self, content: str, step: dict[str, Any]) -> bool:
        """Determine if a step looks like a comparison-type command."""
        keywords = ["hash", "checksum", "digest", "compare", "diff", "verify"]
        if any(token in content for token in keywords):
            return True
        description = get_field_value(step, STEP_ACTION_FIELDS)
        if description and isinstance(description, str):
            lowered = description.lower()
            if any(token in lowered for token in keywords):
                return True
        return False

    def _normalize_command_signature(self, command: str) -> str | None:
        """Produce a normalized signature for a command."""
        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()
        if not tokens:
            return None
        base = tokens[0].lower()
        flags = sorted(token.lower() for token in tokens[1:] if token.startswith("-"))
        return "|".join([base, *flags]) if flags else base

    def _suggest_comparison(
        self,
        commands: list[dict[str, Any]],
        case_num: int,
        suggestions: list[str],
    ) -> None:
        """Suggest that similar command outputs should be compared."""
        if not commands:
            return

        signature = commands[0].get("signature", "command")
        suggestions.append(
            f"Test case {case_num}: Consider adding a comparison step after repeated "
            f"'{signature.split('|')[0]}' commands to verify outputs remain consistent"
        )

        files_involved = []
        for cmd_info in commands:
            command = cmd_info.get("command", "")
            if isinstance(command, str):
                param_matches = re.findall(r"\{([^}]*)\}", command)
                files_involved.extend(param_matches)

        unique_files = list(dict.fromkeys(files_involved))
        if len(unique_files) >= 2:
            files_list = ", ".join(unique_files)
            suggestions.append(
                f"Test case {case_num}: Use Robot Framework keywords like "
                f"'Should Be Equal' to compare outputs for: {files_list}"
            )

    def add_comparison_steps(
        self,
        test_case: dict[str, Any],
        steps: list[dict[str, Any]],
        test_index: int,
        changes_made: list[dict[str, Any]],
    ) -> None:
        """Insert comparison steps directly into the test case when appropriate."""
        steps_container = self._resolve_steps_container(test_case)
        if steps_container is None:
            return

        hash_entries = self._group_comparable_commands(
            self._collect_command_steps(steps)
        )
        indexed_commands = self._index_comparable_commands(
            steps_container, hash_entries
        )
        if len(indexed_commands) < 2:
            return

        inserted_pairs = 0
        cursor = 0
        while cursor + 1 < len(indexed_commands):
            first_entry = indexed_commands[cursor]
            second_entry = indexed_commands[cursor + 1]

            inserted = self._insert_hash_comparison_step(
                steps_container=steps_container,
                parser_steps=steps,
                first_entry=first_entry,
                second_entry=second_entry,
                test_index=test_index,
                pair_index=inserted_pairs,
                changes_made=changes_made,
            )

            if inserted:
                inserted_pairs += 1
            cursor += 2

    def _resolve_steps_container(
        self, test_case: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Return the mutable list that holds step dictionaries."""
        script_field, script_data = TEST_SCRIPT_FIELDS.find_first(test_case)
        if script_field and isinstance(script_data, dict):
            steps_list = script_data.get(STEPS_FIELD_NAME)
            if isinstance(steps_list, list):
                return steps_list
            if steps_list is None:
                new_steps_list: list[dict[str, Any]] = []
                script_data[STEPS_FIELD_NAME] = new_steps_list
                return new_steps_list

        steps_field, steps_value = TEST_STEP_FIELDS.find_first(test_case)
        if steps_field and isinstance(steps_value, list):
            return steps_value
        return None

    def _index_comparable_commands(
        self,
        steps_container: list[dict[str, Any]],
        hash_entries: list[dict[str, Any]],
    ) -> list[tuple[int, dict[str, Any]]]:
        """Attach container indices to hash command entries."""
        indexed: list[tuple[int, dict[str, Any]]] = []
        for entry in hash_entries:
            step_obj = entry.get("step")
            if not isinstance(step_obj, dict):
                continue
            try:
                idx = steps_container.index(step_obj)
            except ValueError:
                continue
            indexed.append((idx, entry))

        indexed.sort(key=lambda item: item[0])
        return indexed

    def _insert_hash_comparison_step(
        self,
        *,
        steps_container: list[dict[str, Any]],
        parser_steps: list[dict[str, Any]],
        first_entry: tuple[int, dict[str, Any]],
        second_entry: tuple[int, dict[str, Any]],
        test_index: int,
        pair_index: int,
        changes_made: list[dict[str, Any]],
    ) -> bool:
        """Create and insert the hash comparison step into the test case."""
        _, first_data = first_entry
        _, second_data = second_entry

        comparison_step = self._create_comparison_step(
            steps_container=steps_container,
            source_entry=first_data,
            target_entry=second_data,
            test_index=test_index,
            pair_index=pair_index,
        )
        if comparison_step is None:
            return False

        if self._existing_comparison_step(steps_container, comparison_step):
            return False

        target_step = second_data.get("step")
        insert_position = len(steps_container)
        if isinstance(target_step, dict):
            try:
                insert_position = steps_container.index(target_step) + 1
            except ValueError:
                insert_position = len(steps_container)

        steps_container.insert(insert_position, comparison_step)
        parser_steps.insert(insert_position, comparison_step)

        changes_made.append(
            {
                "type": "step_added",
                "reason": "Added command comparison verification step",
                "field": "step",
                "original": None,
                "improved": comparison_step["description"],
                "test_case_index": test_index,
                "step_index": insert_position + 1,
            }
        )

        logger.info(
            "Inserted command comparison step for test %s at position %s",
            test_index + 1,
            insert_position + 1,
        )
        return True

    def _existing_comparison_step(
        self,
        steps_container: list[dict[str, Any]],
        candidate: dict[str, Any],
    ) -> bool:
        """Check whether an equivalent hash comparison step already exists."""
        candidate_metadata = candidate.get("metadata", {})
        candidate_sources = candidate_metadata.get("sourceSteps")
        candidate_data = candidate.get("testData")
        for step in steps_container:
            if not isinstance(step, dict):
                continue
            metadata = step.get("metadata")
            if (
                isinstance(metadata, dict)
                and metadata.get("generator") == "command_comparison"
                and metadata.get("sourceSteps") == candidate_sources
            ):
                return True
            if (
                isinstance(metadata, dict)
                and metadata.get("generator") == "command_comparison"
                and step.get("testData") == candidate_data
            ):
                return True
        return False

    def _create_comparison_step(
        self,
        *,
        steps_container: list[dict[str, Any]],
        source_entry: dict[str, Any],
        target_entry: dict[str, Any],
        test_index: int,
        pair_index: int,
    ) -> dict[str, Any] | None:
        """Build a comparison step based on matching hash commands."""
        source_command = self._sanitize_command(source_entry.get("command"))
        target_command = self._sanitize_command(target_entry.get("command"))
        if not source_command or not target_command:
            return None

        source_file = self._extract_primary_target(source_command)
        target_file = self._extract_primary_target(target_command)
        hint = self._extract_command_hint(source_command, target_command)

        description = self._format_comparison_description(source_file, target_file)

        test_data_parts = [
            f"command_1: {source_command}",
            f"command_2: {target_command}",
        ]
        if hint:
            test_data_parts.append(f"comparison_hint: {hint}")

        metadata = {
            "autoGenerated": True,
            "generator": "command_comparison",
            "sourceSteps": self._source_step_numbers(
                steps_container, source_entry.get("step"), target_entry.get("step")
            ),
            "signature": source_entry.get("signature"),
        }

        comparison_step: dict[str, Any] = {
            "description": description,
            "testData": ", ".join(test_data_parts),
            "expectedResult": "Outputs match",
            "index": self._next_step_index(steps_container),
            "id": f"auto_compare_{test_index + 1}_{pair_index + 1}",
            "metadata": metadata,
        }
        return comparison_step

    def _source_step_numbers(
        self,
        steps_container: list[dict[str, Any]],
        source_step: dict[str, Any] | None,
        target_step: dict[str, Any] | None,
    ) -> list[int | None]:
        """Return user-readable step numbers for metadata tracking."""
        numbers: list[int | None] = []
        for step in (source_step, target_step):
            if isinstance(step, dict):
                index_value = step.get("index")
                if isinstance(index_value, int):
                    numbers.append(index_value)
                    continue
                try:
                    numbers.append(steps_container.index(step) + 1)
                    continue
                except ValueError:
                    pass
            numbers.append(None)
        return numbers

    def _next_step_index(self, steps_container: list[dict[str, Any]]) -> int:
        """Determine the next step index value when 'index' keys are numeric."""
        max_index = 0
        for step in steps_container:
            if not isinstance(step, dict):
                continue
            value = step.get("index")
            if isinstance(value, int) and value > max_index:
                max_index = value
        return max_index + 1 if max_index else len(steps_container) + 1

    def _sanitize_command(self, command: Any) -> str | None:
        """Return a normalized hash command string suitable for reuse."""
        if not isinstance(command, str):
            return None
        cleaned = command.strip().rstrip("{")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned or None

    def _extract_primary_target(self, command: str) -> str:
        """Extract the primary file target from a hash command."""
        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()

        if len(tokens) <= 1:
            return ""

        for token in tokens[1:]:
            if token.startswith("-"):
                continue
            return token
        return ""

    def _extract_command_hint(self, source_command: str, target_command: str) -> str:
        """Infer a comparison hint from the command names if possible."""
        try:
            source_tokens = shlex.split(source_command)
        except ValueError:
            source_tokens = source_command.split()
        try:
            target_tokens = shlex.split(target_command)
        except ValueError:
            target_tokens = target_command.split()

        first_tokens = [
            token for token in (source_tokens[:1] + target_tokens[:1]) if token
        ]
        for token in first_tokens:
            lower = token.lower()
            if any(
                prefix in lower for prefix in ["sha", "md5", "blake", "hash", "diff"]
            ):
                return token
        return ""

    def _format_comparison_description(self, source_file: str, target_file: str) -> str:
        """Create a human-readable description for the comparison step."""
        if source_file and target_file:
            return (
                f"Verify command outputs are equal for {source_file} and {target_file}"
            )
        if source_file or target_file:
            file_name = source_file or target_file
            return f"Verify command outputs are equal for {file_name}"
        return "Verify command outputs are equal"
