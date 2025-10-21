"""Integration tests for the CLI task Robot blueprint."""

from __future__ import annotations

from pathlib import Path

import pytest

from importobot.core.converter import JsonToRobotConverter
from importobot.core.templates import configure_template_sources
from importobot.utils.json_utils import load_json_file

BASE_DIR = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = BASE_DIR / "examples" / "json" / "set_config.json"
TEMPLATE_DIR = BASE_DIR / "tests" / "fixtures" / "robot_templates"


@pytest.fixture(autouse=True)
def reset_blueprint_sources():
    """Ensure each test starts with a clean blueprint registry."""
    configure_template_sources([])
    try:
        yield
    finally:
        configure_template_sources([])


def test_cli_task_blueprint_matches_expected() -> None:
    """Ensure CLI task JSON converts to the expected Robot output."""
    configure_template_sources([str(TEMPLATE_DIR)])
    json_data = load_json_file(str(EXAMPLE_PATH))

    robot_output = JsonToRobotConverter().convert_json_data(json_data)

    expected_fragment = (
        "${setconfig_cli}=    Read Until Regexp    setconfig task (\\S+) "
        "completed successfully!"
    )
    assert expected_fragment in robot_output
    assert "Log    Expected: no task errors" in robot_output
    assert "${ps}=    Execute Command    ps -ely | grep mycustomname" in robot_output
    assert "Log    Expected: mycustomname found" in robot_output


def test_cli_blueprint_default_rendering_without_templates() -> None:
    """Blueprint should fall back to default rendering when no templates exist."""
    configure_template_sources([])
    json_data = load_json_file(str(EXAMPLE_PATH))

    robot_output = JsonToRobotConverter().convert_json_data(json_data)

    assert "*** Settings ***" in robot_output
    assert "Library             SSHLibrary" in robot_output
    assert "# No resource imports discovered" in robot_output
    assert "Switch Connection    Controller" in robot_output
    assert "Write    setconfig --proc_name ${proc_name}" in robot_output
    assert "${setconfig_cli}=    Read Until Prompt" in robot_output
    assert "Log    Expected: no task errors" in robot_output
    assert "Switch Connection    Target" in robot_output
    assert "${ps}=    Execute Command    ps -ely | grep ${proc_name}" in robot_output
    assert "Log    Expected: mycustomname found" in robot_output


def test_cli_blueprint_uses_template_substitutions_when_available() -> None:
    """Verify learned templates influence the rendered Robot output."""
    configure_template_sources([str(TEMPLATE_DIR)])
    json_data = load_json_file(str(EXAMPLE_PATH))

    robot_output = JsonToRobotConverter().convert_json_data(json_data)

    assert "Resource            resources/Setup.resource" in robot_output
    assert (
        "Read Until Regexp    setconfig task (\\S+) completed successfully!"
        in robot_output
    )
    assert "Target Process List" in robot_output
    assert "Logger    step_num=1" in robot_output
    assert "Logger    step_num=2" in robot_output
    assert "# No resource imports discovered" not in robot_output
