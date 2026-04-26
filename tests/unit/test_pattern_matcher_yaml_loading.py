"""Tests for YAML-based pattern loading in PatternMatcher."""

import re
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
import yaml

from importobot.core.pattern_matcher import IntentType, PatternMatcher

EXPECTED_PATTERN_COUNT = 93
YAML_CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "importobot"
    / "core"
    / "pattern_matcher.py"
)
YAML_FILE_PATH = Path(__file__).parent.parent.parent / "config" / "intent_patterns.yaml"


class TestYamlFileExists:
    """Verify the YAML configuration file exists and is loadable."""

    def test_yaml_file_exists(self) -> None:
        """config/intent_patterns.yaml must exist on disk."""
        assert YAML_FILE_PATH.exists(), f"Expected YAML config at {YAML_FILE_PATH}"

    def test_yaml_file_loads_without_error(self) -> None:
        """Loading the YAML file must not raise any exception."""
        with open(YAML_FILE_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert config is not None

    def test_yaml_file_has_patterns_key(self) -> None:
        """Top-level 'patterns' key must be present in the YAML."""
        with open(YAML_FILE_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert "patterns" in config, "YAML must have a top-level 'patterns' key"
        assert isinstance(config["patterns"], list)


class TestPatternCount:
    """Verify the expected number of patterns is present in the YAML."""

    def test_pattern_count_is_93(self) -> None:
        """YAML must contain exactly 93 pattern entries."""
        with open(YAML_FILE_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        entries = config.get("patterns", [])
        assert len(entries) == EXPECTED_PATTERN_COUNT, (
            f"Expected {EXPECTED_PATTERN_COUNT} patterns, got {len(entries)}"
        )

    def test_pattern_matcher_loads_all_patterns(self) -> None:
        """PatternMatcher must hold the same count of patterns as the YAML."""
        matcher = PatternMatcher()
        assert len(matcher.patterns) == EXPECTED_PATTERN_COUNT, (
            f"PatternMatcher loaded {len(matcher.patterns)} patterns, "
            f"expected {EXPECTED_PATTERN_COUNT}"
        )


class TestRequiredFields:
    """Verify every pattern entry contains the required fields."""

    @pytest.fixture(scope="class")
    def yaml_entries(self) -> list[dict[str, Any]]:
        with open(YAML_FILE_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return cast(list[dict[str, Any]], config.get("patterns", []))

    def test_every_entry_has_intent_field(
        self, yaml_entries: list[dict[str, Any]]
    ) -> None:
        """Each entry must have an 'intent' field."""
        missing = [i for i, entry in enumerate(yaml_entries) if "intent" not in entry]
        assert not missing, f"Entries at indices {missing} are missing 'intent'"

    def test_every_entry_has_pattern_field(
        self, yaml_entries: list[dict[str, Any]]
    ) -> None:
        """Each entry must have a 'pattern' field."""
        missing = [i for i, entry in enumerate(yaml_entries) if "pattern" not in entry]
        assert not missing, f"Entries at indices {missing} are missing 'pattern'"

    def test_every_entry_has_priority_field(
        self, yaml_entries: list[dict[str, Any]]
    ) -> None:
        """Each entry must have a 'priority' field."""
        missing = [i for i, entry in enumerate(yaml_entries) if "priority" not in entry]
        assert not missing, f"Entries at indices {missing} are missing 'priority'"

    def test_intent_fields_are_strings(
        self, yaml_entries: list[dict[str, Any]]
    ) -> None:
        """All 'intent' values must be non-empty strings."""
        bad = [
            i
            for i, entry in enumerate(yaml_entries)
            if not isinstance(entry.get("intent"), str) or not entry["intent"].strip()
        ]
        assert not bad, f"Entries at indices {bad} have invalid 'intent' values"

    def test_pattern_fields_are_strings(
        self, yaml_entries: list[dict[str, Any]]
    ) -> None:
        """All 'pattern' values must be non-empty strings."""
        bad = [
            i
            for i, entry in enumerate(yaml_entries)
            if not isinstance(entry.get("pattern"), str) or not entry["pattern"].strip()
        ]
        assert not bad, f"Entries at indices {bad} have invalid 'pattern' values"

    def test_priority_fields_are_integers(
        self, yaml_entries: list[dict[str, Any]]
    ) -> None:
        """All 'priority' values must be integers."""
        bad = [
            i
            for i, entry in enumerate(yaml_entries)
            if not isinstance(entry.get("priority"), int)
        ]
        assert not bad, f"Entries at indices {bad} have non-integer 'priority' values"


class TestPatternIntegrity:
    """Verify every pattern in the YAML compiles to a valid regex."""

    @pytest.fixture(scope="class")
    def yaml_entries(self) -> list[dict[str, Any]]:
        with open(YAML_FILE_PATH, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return cast(list[dict[str, Any]], config.get("patterns", []))

    def test_all_patterns_compile_to_valid_regex(
        self, yaml_entries: list[dict[str, Any]]
    ) -> None:
        """Every 'pattern' string must compile without error using re.IGNORECASE."""
        invalid = []
        for i, entry in enumerate(yaml_entries):
            pattern_str = entry.get("pattern", "")
            try:
                re.compile(pattern_str, re.IGNORECASE)
            except re.error as exc:
                invalid.append((i, pattern_str, str(exc)))

        assert not invalid, "Invalid regex patterns found:\n" + "\n".join(
            f"  [{i}] {p!r}: {e}" for i, p, e in invalid
        )

    def test_all_intent_names_map_to_valid_enum_values(
        self, yaml_entries: list[dict[str, Any]]
    ) -> None:
        """Every 'intent' value must correspond to an IntentType enum member."""
        unknown = []
        valid_names = {member.name for member in IntentType}
        for i, entry in enumerate(yaml_entries):
            intent_name = entry.get("intent", "")
            if intent_name not in valid_names:
                unknown.append((i, intent_name))

        assert not unknown, "Unknown IntentType names found in YAML:\n" + "\n".join(
            f"  [{i}] {name!r}" for i, name in unknown
        )


class TestFallbackBehavior:
    """Verify error behavior when the YAML file is missing."""

    def test_missing_yaml_raises_file_not_found(self, tmp_path: Path) -> None:
        """_load_patterns_from_yaml must raise FileNotFoundError."""
        missing = tmp_path / "nonexistent" / "intent_patterns.yaml"

        def patched(self):  # type: ignore[no-untyped-def]
            with open(missing, encoding="utf-8") as f:
                yaml.safe_load(f)
            return []

        with (
            patch.object(PatternMatcher, "_load_patterns_from_yaml", patched),
            pytest.raises(FileNotFoundError),
        ):
            PatternMatcher()

    def test_missing_yaml_error_message_is_informative(self, tmp_path: Path) -> None:
        """FileNotFoundError for a missing YAML should include the path."""
        nonexistent = tmp_path / "gone.yaml"

        def patched(self):  # type: ignore[no-untyped-def]
            with open(nonexistent, encoding="utf-8") as f:
                yaml.safe_load(f)
            return []

        with (
            patch.object(PatternMatcher, "_load_patterns_from_yaml", patched),
            pytest.raises(FileNotFoundError) as exc_info,
        ):
            PatternMatcher()
        assert str(nonexistent) in str(exc_info.value)


class TestRoundTripConsistency:
    """Patterns from YAML produce expected matching behavior."""

    @pytest.fixture(scope="class")
    def matcher(self) -> PatternMatcher:
        return PatternMatcher()

    # SSH intents
    @pytest.mark.parametrize(
        ("text", "expected_intent"),
        [
            ("open ssh connection to server", IntentType.SSH_CONNECT),
            ("establish remote connection", IntentType.SSH_CONNECT),
            ("connect to staging", IntentType.SSH_CONNECT),
            ("connect to production", IntentType.SSH_CONNECT),
            ("close ssh connection", IntentType.SSH_DISCONNECT),
            ("disconnect from remote", IntentType.SSH_DISCONNECT),
            ("upload file to remote", IntentType.SSH_FILE_UPLOAD),
            ("download file from server", IntentType.SSH_FILE_DOWNLOAD),
            ("create directory on server", IntentType.SSH_DIRECTORY_CREATE),
            ("list directory contents", IntentType.SSH_DIRECTORY_LIST),
            ("login ssh with key", IntentType.SSH_LOGIN),
            ("enable logging on connection", IntentType.SSH_ENABLE_LOGGING),
            ("switch connection to backup", IntentType.SSH_SWITCH_CONNECTION),
            ("read until prompt appears", IntentType.SSH_READ_UNTIL),
        ],
    )
    def test_ssh_intent_detection(
        self, matcher: PatternMatcher, text: str, expected_intent: IntentType
    ) -> None:
        """SSH-related texts must resolve to the correct SSH intent."""
        assert matcher.detect_intent(text) == expected_intent, (
            f"{text!r} should map to {expected_intent}, "
            f"got {matcher.detect_intent(text)}"
        )

    # File operation intents
    @pytest.mark.parametrize(
        ("text", "expected_intent"),
        [
            ("verify file exists on disk", IntentType.FILE_EXISTS),
            ("check file exists", IntentType.FILE_EXISTS),
            ("remove file from directory", IntentType.FILE_REMOVE),
            ("delete file after test", IntentType.FILE_REMOVE),
            ("get file from server", IntentType.FILE_TRANSFER),
            ("create a new file here", IntentType.FILE_CREATION),
        ],
    )
    def test_file_operation_intent_detection(
        self, matcher: PatternMatcher, text: str, expected_intent: IntentType
    ) -> None:
        """File operation texts must resolve to the correct file intent."""
        assert matcher.detect_intent(text) == expected_intent, (
            f"{text!r} should map to {expected_intent}, "
            f"got {matcher.detect_intent(text)}"
        )

    # Database intents
    @pytest.mark.parametrize(
        ("text", "expected_intent"),
        [
            ("connect to database", IntentType.DATABASE_CONNECT),
            ("establish db connection", IntentType.DATABASE_CONNECT),
            ("execute sql query", IntentType.DATABASE_EXECUTE),
            ("run query against db", IntentType.DATABASE_EXECUTE),
            ("disconnect from database", IntentType.DATABASE_DISCONNECT),
            ("insert new record into table", IntentType.DATABASE_MODIFY),
            ("update record in table", IntentType.DATABASE_MODIFY),
        ],
    )
    def test_database_intent_detection(
        self, matcher: PatternMatcher, text: str, expected_intent: IntentType
    ) -> None:
        """Database texts must resolve to the correct database intent."""
        assert matcher.detect_intent(text) == expected_intent, (
            f"{text!r} should map to {expected_intent}, "
            f"got {matcher.detect_intent(text)}"
        )

    # Command execution intents
    @pytest.mark.parametrize(
        ("text", "expected_intent"),
        [
            ("execute curl command", IntentType.COMMAND_EXECUTION),
            ("run wget download", IntentType.COMMAND_EXECUTION),
            ("echo hello world", IntentType.COMMAND_EXECUTION),
        ],
    )
    def test_command_execution_intent_detection(
        self, matcher: PatternMatcher, text: str, expected_intent: IntentType
    ) -> None:
        """Command texts must resolve to COMMAND_EXECUTION."""
        assert matcher.detect_intent(text) == expected_intent, (
            f"{text!r} should map to {expected_intent}, "
            f"got {matcher.detect_intent(text)}"
        )

    def test_patterns_sorted_descending_by_priority(
        self, matcher: PatternMatcher
    ) -> None:
        """Patterns list must be sorted highest priority first after YAML load."""
        priorities = [p.priority for p in matcher.patterns]
        assert priorities == sorted(priorities, reverse=True)

    def test_no_duplicate_intent_type_on_repeated_instantiation(self) -> None:
        """Two independently created PatternMatcher instances must agree on intents."""
        matcher_a = PatternMatcher()
        matcher_b = PatternMatcher()

        test_cases = [
            "open ssh connection",
            "connect to database",
            "verify file exists",
            "execute curl command",
            "make get request to api",
        ]
        for text in test_cases:
            assert matcher_a.detect_intent(text) == matcher_b.detect_intent(text), (
                f"Inconsistent intent for {text!r} between two PatternMatcher instances"
            )
