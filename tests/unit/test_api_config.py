"""Tests for API ingest configuration resolution."""

from argparse import Namespace

import pytest

from importobot import exceptions
from importobot.config import APIIngestConfig, resolve_api_ingest_config
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
