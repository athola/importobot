"""Invariant tests for API retrieval configuration resolution."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from importobot.config import resolve_api_ingest_config
from importobot.exceptions import ConfigurationError
from importobot.medallion.interfaces.enums import SupportedFormat

token_strategy = st.text(
    alphabet=st.characters(
        blacklist_characters=[",", " ", "\t"],
        min_codepoint=33,
        max_codepoint=126,
    ),
    min_size=1,
    max_size=12,
)


# pylint: disable=too-many-positional-arguments
@given(
    cli_tokens=st.lists(token_strategy, min_size=0, max_size=3),
    env_tokens=st.lists(token_strategy, min_size=0, max_size=3),
    use_cli_tokens=st.booleans(),
    cli_project=st.one_of(st.none(), st.text(min_size=1, max_size=12)),
)
@settings(max_examples=60, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_token_resolution_precedence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    cli_tokens: list[str],
    env_tokens: list[str],
    use_cli_tokens: bool,
    cli_project: str | None,
) -> None:
    """CLI tokens should override environment tokens while preserving immutability."""
    prefix = "IMPORTOBOT_ZEPHYR"
    env_url = "https://env.example/api"
    monkeypatch.setenv(f"{prefix}_API_URL", env_url)
    monkeypatch.setenv(f"{prefix}_PROJECT", "ENVPROJECT")

    if env_tokens:
        monkeypatch.setenv(f"{prefix}_TOKENS", ",".join(env_tokens))
    else:
        monkeypatch.delenv(f"{prefix}_TOKENS", raising=False)

    args = Namespace(
        fetch_format=SupportedFormat.ZEPHYR,
        api_url=None,
        api_tokens=cli_tokens if use_cli_tokens else None,
        api_user=None,
        project=cli_project,
        input_dir=str(tmp_path),
        max_concurrency=None,
    )

    expected_tokens = cli_tokens if use_cli_tokens and cli_tokens else env_tokens

    if not expected_tokens:
        with pytest.raises(ConfigurationError):
            resolve_api_ingest_config(args)
        return

    original_cli = list(cli_tokens)
    config = resolve_api_ingest_config(args)

    assert config.tokens == expected_tokens
    if use_cli_tokens and cli_tokens:
        assert cli_tokens == original_cli

    assert config.api_url == env_url
    if cli_project and cli_project.strip():
        stripped = cli_project.strip()
        if stripped.isdigit():
            assert config.project_name is None
            assert config.project_id == int(stripped)
        else:
            assert config.project_name == stripped
    else:
        assert config.project_name == "ENVPROJECT"
    assert config.output_dir == Path(tmp_path)
