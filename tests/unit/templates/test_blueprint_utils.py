"""Unit tests for blueprint utility helpers."""

from importobot.core.templates.blueprints import utils


def test_extract_test_cases_from_dict() -> None:
    data = {
        "tests": [
            {"name": "first"},
            {"name": "second"},
        ]
    }
    cases = utils.extract_test_cases(data)
    assert [case["name"] for case in cases] == ["first", "second"]


def test_iter_step_text_collects_fields() -> None:
    step = {
        "description": "desc",
        "action": "act",
        "expectedResult": "result",
    }
    collected = list(utils.iter_step_text(step))
    assert collected == ["desc", "act", "result"]


def test_format_test_name_prefers_key() -> None:
    test_case = {"key": "TC-1", "name": "unused"}
    formatted = utils.format_test_name(test_case)
    assert "tc 1" in formatted.lower()


def test_resolve_cli_command_prefers_name_if_available() -> None:
    test_case = {"name": "default"}
    context = {"command": "touch"}
    assert utils.resolve_cli_command(test_case, context) == "default"
