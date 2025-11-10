"""Tests for configuration default resolution helpers."""

from pathlib import Path

import pytest

from importobot import config


def test_resolve_output_dir_uses_current_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IMPORTOBOT_API_INPUT_DIR", raising=False)
    result = config._resolve_output_dir(None)
    assert result == Path.cwd()


def test_resolve_output_dir_prefers_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("IMPORTOBOT_API_INPUT_DIR", str(tmp_path))
    result = config._resolve_output_dir(None)
    assert result == tmp_path.resolve()


def test_resolve_max_concurrency_from_cli() -> None:
    assert config._resolve_max_concurrency(5) == 5


def test_resolve_max_concurrency_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IMPORTOBOT_API_MAX_CONCURRENCY", raising=False)
    monkeypatch.setenv("IMPORTOBOT_API_MAX_CONCURRENCY", "8")
    assert config._resolve_max_concurrency(None) == 8


def test_resolve_max_concurrency_invalid_env(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("IMPORTOBOT_API_MAX_CONCURRENCY", "not-int")
    assert config._resolve_max_concurrency(None) is None
    assert any(
        "IMPORTOBOT_API_MAX_CONCURRENCY" in record.message for record in caplog.records
    )
