"""Tests for API ingest configuration resolution."""

from argparse import Namespace
from typing import cast

import pytest

from importobot import exceptions
from importobot.config import (
    MAX_PROJECT_ID,
    APIIngestConfig,
    _parse_project_identifier,
    _ProjectReferenceArgs,
    _resolve_project_reference,
    resolve_api_ingest_config,
)
from importobot.medallion.interfaces.enums import SupportedFormat


def make_args(**overrides: object) -> Namespace:
    """Create a Namespace with sensible defaults for API ingest tests."""
    defaults: dict[str, object] = {
        "fetch_format": SupportedFormat.TESTRAIL,
        "api_url": None,
        "api_tokens": None,
        "api_user": None,
        "project": None,
        "input_dir": None,
        "max_concurrency": None,
        "insecure": False,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


def test_cli_overrides_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI arguments should take precedence over environment variables."""
    monkeypatch.setenv("IMPORTOBOT_TESTRAIL_API_URL", "https://env.example/api")
    monkeypatch.setenv("IMPORTOBOT_TESTRAIL_TOKENS", "env-token")
    args = make_args(
        api_url="https://cli.example/api",
        api_tokens=["cli-token"],
        api_user="cli-user",
        project="CLI",
        input_dir="cli-downloads",
    )

    config = resolve_api_ingest_config(args)

    assert isinstance(config, APIIngestConfig)
    assert config.api_url == "https://cli.example/api"
    assert config.tokens == ["cli-token"]
    assert config.user == "cli-user"
    assert config.project_name == "CLI"
    assert config.project_id is None
    assert str(config.output_dir).endswith("cli-downloads")
    assert config.insecure is False


def test_environment_used_when_cli_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables should be used when CLI arguments are absent."""
    monkeypatch.setenv("IMPORTOBOT_ZEPHYR_API_URL", "https://jira.example/rest")
    monkeypatch.setenv("IMPORTOBOT_ZEPHYR_TOKENS", "jira-token,zephyr-token")
    monkeypatch.setenv("IMPORTOBOT_ZEPHYR_API_USER", "jira-user")
    monkeypatch.setenv("IMPORTOBOT_ZEPHYR_PROJECT", "ZEPHYR")
    monkeypatch.setenv("IMPORTOBOT_API_MAX_CONCURRENCY", "5")
    args = make_args(fetch_format=SupportedFormat.ZEPHYR)

    config = resolve_api_ingest_config(args)

    assert config.api_url == "https://jira.example/rest"
    assert config.tokens == ["jira-token", "zephyr-token"]
    assert config.user == "jira-user"
    assert config.project_name == "ZEPHYR"
    assert config.project_id is None
    assert config.max_concurrency == 5
    assert config.insecure is False


def test_missing_required_values_raise_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing API url should raise configuration error with masked tokens."""
    monkeypatch.delenv("IMPORTOBOT_TESTLINK_API_URL", raising=False)
    args = make_args(fetch_format=SupportedFormat.TESTLINK, api_tokens=["secret-token"])

    with pytest.raises(exceptions.ConfigurationError) as exc_info:
        resolve_api_ingest_config(args)

    message = str(exc_info.value)
    assert "API URL" in message
    assert "secret-token" not in message
    assert "***" in message


def test_project_id_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    # pylint: disable=unused-argument
    """Numeric project identifiers should map to project_id."""
    args = make_args(
        api_url="https://testrail.example/api",
        api_tokens=["token"],
        api_user="cli-user",
        project="12345",
    )

    config = resolve_api_ingest_config(args)

    assert config.project_id == 12345
    assert config.project_name is None
    assert config.insecure is False


def test_cli_insecure_flag_sets_configuration() -> None:
    """The --insecure flag should disable TLS verification in the config."""
    args = make_args(
        api_url="https://testrail.example/api",
        api_tokens=["token"],
        api_user="cli-user",
        insecure=True,
    )

    config = resolve_api_ingest_config(args)

    assert config.insecure is True


def test_environment_insecure_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment toggle should disable TLS verification when set."""
    monkeypatch.setenv("IMPORTOBOT_TESTRAIL_API_URL", "https://env.example/api")
    monkeypatch.setenv("IMPORTOBOT_TESTRAIL_TOKENS", "env-token")
    monkeypatch.setenv("IMPORTOBOT_TESTRAIL_API_USER", "env-user")
    monkeypatch.setenv("IMPORTOBOT_TESTRAIL_INSECURE", "true")

    args = make_args()

    config = resolve_api_ingest_config(args)

    assert config.insecure is True


def test_parse_project_identifier_trims_ascii_name() -> None:
    """Explicit regression: ASCII name survives stripping."""
    name, project_id = _parse_project_identifier("  PRJ-42  ")

    assert name == "PRJ-42"
    assert project_id is None


def test_parse_project_identifier_handles_unicode_digits(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Explicit regression: Non-ASCII numerals treated as name."""
    unicode_digits = "\uff11\uff12\uff13\uff14\uff15"

    name, project_id = _parse_project_identifier(unicode_digits)

    assert name == unicode_digits
    assert project_id is None
    assert "treated as project name (not numeric ID)" in caplog.text


def test_parse_project_identifier_accepts_upper_bound() -> None:
    """Max supported numeric identifier should remain numeric."""
    name, project_id = _parse_project_identifier(str(MAX_PROJECT_ID))

    assert name is None
    assert project_id == MAX_PROJECT_ID


def test_parse_project_identifier_rejects_out_of_range_numeric() -> None:
    """Identifiers beyond the supported range should raise a configuration error."""
    overflow_value = str(MAX_PROJECT_ID + 1)

    with pytest.raises(exceptions.ConfigurationError) as exc_info:
        _parse_project_identifier(overflow_value)

    assert str(MAX_PROJECT_ID + 1) in str(exc_info.value)


def test_cli_project_identifier_invalid_raises_configuration_error() -> None:
    """CLI project argument should be validated before falling back to env."""
    args = make_args(
        api_url="https://testrail.example/api",
        api_tokens=["token"],
        api_user="cli-user",
        project="   ",
    )

    with pytest.raises(exceptions.ConfigurationError) as exc_info:
        resolve_api_ingest_config(args)

    assert "Invalid CLI project identifier" in str(exc_info.value)


def test_parse_project_identifier_handles_empty_string() -> None:
    """Empty string should return None for both name and ID."""
    name, project_id = _parse_project_identifier("")

    assert name is None
    assert project_id is None


def test_parse_project_identifier_handles_whitespace_only() -> None:
    """Whitespace-only string should return None for both name and ID."""
    name, project_id = _parse_project_identifier("   \t\n  ")

    assert name is None
    assert project_id is None


def test_parse_project_identifier_handles_mixed_unicode() -> None:
    """Mixed ASCII and non-ASCII should be treated as project name."""
    mixed = "Project-\uff11\uff12\uff13"

    name, project_id = _parse_project_identifier(mixed)

    assert name == mixed
    assert project_id is None


def test_parse_project_identifier_handles_zero() -> None:
    """Zero should be accepted as a valid project ID."""
    name, project_id = _parse_project_identifier("0")

    assert name is None
    assert project_id == 0


class TestProjectReferenceArgsProtocol:
    """Test the _ProjectReferenceArgs Protocol for typing improvements."""

    def test_resolve_project_reference_accepts_namespace_args(self) -> None:
        """Test that _resolve_project_reference accepts Namespace arguments."""
        # Create a Namespace with project attribute (compatible with Protocol)
        args = make_args(project="test_project")

        def mock_fetch_env(key: str) -> str | None:
            return None

        name, project_id = _resolve_project_reference(
            args=args,  # pyright: ignore[reportArgumentType]
            fetch_env=mock_fetch_env,
            prefix="TEST_",
            fetch_format=SupportedFormat.TESTRAIL,
        )

        assert name == "test_project"
        assert project_id is None

    def test_resolve_project_reference_accepts_custom_object(self) -> None:
        """Test _resolve_project_reference accepts custom objects."""

        class CustomArgs:
            def __init__(self, project: str | None):
                self.project = project

        # Create a custom object with project attribute (compatible with Protocol)
        args = CustomArgs(project="custom_project")

        def mock_fetch_env(key: str) -> str | None:
            return None

        name, project_id = _resolve_project_reference(
            args=args,
            fetch_env=mock_fetch_env,
            prefix="CUSTOM_",
            fetch_format=SupportedFormat.ZEPHYR,
        )

        assert name == "custom_project"
        assert project_id is None

    def test_resolve_project_reference_handles_missing_project_attribute(self) -> None:
        """Test that function gracefully handles objects without project attribute."""

        class IncompatibleArgs:
            def __init__(self, other_attr: str):
                self.other_attr = other_attr

        args = IncompatibleArgs(other_attr="no_project")

        def mock_fetch_env(key: str) -> str | None:
            return None

        # Function should handle missing attribute gracefully with getattr
        name, project_id = _resolve_project_reference(
            args=args,  # type: ignore
            fetch_env=mock_fetch_env,
            prefix="TEST_",
            fetch_format=SupportedFormat.TESTRAIL,
        )

        # Should return None when project attribute is missing
        assert name is None
        assert project_id is None

    def test_resolve_project_reference_handles_none_project(self) -> None:
        """Test that _resolve_project_reference handles None project values."""
        args = make_args(project=None)

        def mock_fetch_env(key: str) -> str | None:
            return None

        name, project_id = _resolve_project_reference(
            args=args,  # pyright: ignore[reportArgumentType]
            fetch_env=mock_fetch_env,
            prefix="TEST_",
            fetch_format=SupportedFormat.TESTRAIL,
        )

        assert name is None
        assert project_id is None

    def test_resolve_project_reference_handles_numeric_string(self) -> None:
        """Test that _resolve_project_reference handles numeric string values."""
        # Test with numeric string (should parse as project ID)
        args = make_args(project="123")

        def mock_fetch_env(key: str) -> str | None:
            return None

        name, project_id = _resolve_project_reference(
            args=args,  # pyright: ignore[reportArgumentType]
            fetch_env=mock_fetch_env,
            prefix="IMPORTOBOT_TESTRAIL",
            fetch_format=SupportedFormat.TESTRAIL,
        )

        # Numeric string should be parsed as project ID
        assert name is None
        assert project_id == 123

    def test_resolve_project_reference_environment_secondary(self) -> None:
        """Test _resolve_project_reference uses env as secondary source."""
        # Test with invalid CLI project (empty string)
        args = make_args(project="")

        def mock_fetch_env(key: str) -> str | None:
            if key == "IMPORTOBOT_TESTRAIL_PROJECT":
                return "env_project"
            return None

        name, project_id = _resolve_project_reference(
            args=args,  # pyright: ignore[reportArgumentType]
            fetch_env=mock_fetch_env,
            prefix="IMPORTOBOT_TESTRAIL",
            fetch_format=SupportedFormat.TESTRAIL,
        )

        # Empty string should use the environment variable as a secondary source
        assert name == "env_project"
        assert project_id is None

    def test_protocol_type_safety_example(self) -> None:
        """Test that demonstrates Protocol type safety through runtime behavior."""

        # This demonstrates that any object with a `project` attribute works
        class WorkingArgs:
            def __init__(self, project: str | None):
                self.project = project

        def mock_fetch_env(key: str) -> str | None:
            return None

        # Valid usage - object has required project attribute
        valid_args: _ProjectReferenceArgs = WorkingArgs(project="valid")
        result = _resolve_project_reference(
            args=valid_args,
            fetch_env=mock_fetch_env,
            prefix="TEST_",
            fetch_format=SupportedFormat.TESTRAIL,
        )
        assert result == ("valid", None)

        # This would be caught by static type checkers:
        # invalid_args: _ProjectReferenceArgs = object()
        # Error: object doesn't implement protocol

        # But at runtime, function uses getattr gracefully
        class BrokenArgs:
            def __init__(self, wrong_attr: str):
                self.wrong_attr = wrong_attr

        broken_args = BrokenArgs(wrong_attr="test")

        # Function handles missing attributes gracefully at runtime
        # Using cast() to bypass type checkers - the test verifies graceful handling
        result = _resolve_project_reference(
            args=cast(_ProjectReferenceArgs, broken_args),
            fetch_env=mock_fetch_env,
            prefix="TEST_",
            fetch_format=SupportedFormat.TESTRAIL,
        )
        # Returns None for both when project attribute is missing
        assert result == (None, None)
