"""Smoke tests for the documented public API surface."""

from __future__ import annotations

import json

import pytest

import importobot
from importobot import services
from importobot.services import security_gateway


def _minimal_payload() -> dict[str, object]:
    return {
        "testCase": {
            "name": "Sample Test",
            "description": "Simple scenario",
            "steps": [],
        }
    }


def test_convert_dict_payload() -> None:
    output = importobot.convert(_minimal_payload())
    assert "*** Test Cases ***" in output
    assert "Sample Test" in output


def test_convert_file(tmp_path) -> None:
    input_file = tmp_path / "input.json"
    output_file = tmp_path / "output.robot"
    input_file.write_text(json.dumps(_minimal_payload()), encoding="utf-8")

    result = importobot.convert_file(str(input_file), str(output_file))

    assert output_file.exists()
    assert result["success"] is True


def test_convert_directory(tmp_path) -> None:
    input_dir = tmp_path / "incoming"
    output_dir = tmp_path / "generated"
    input_dir.mkdir()
    (input_dir / "case.json").write_text(
        json.dumps(_minimal_payload()), encoding="utf-8"
    )

    result = importobot.convert_directory(str(input_dir), str(output_dir))

    assert result["success"] is True
    assert any(output_dir.iterdir())


def test_api_modules_exposed() -> None:
    assert hasattr(importobot.api, "converters")
    assert hasattr(importobot.api, "validation")
    assert importobot.config is not None
    assert importobot.exceptions.ImportobotError.__name__ == "ImportobotError"


def test_internal_services_guard() -> None:
    with pytest.raises(ModuleNotFoundError):
        _ = services.PerformanceCache

    assert hasattr(security_gateway, "SecurityGateway")
