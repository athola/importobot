"""Integration tests for the CLI task Robot blueprint."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from importobot.core.converter import JsonToRobotConverter
from importobot.core.templates import configure_template_sources
from importobot.utils.json_utils import load_json_file

BASE_DIR = Path(__file__).resolve().parents[2]
EXAMPLE_PATH = BASE_DIR / "examples" / "json" / "set_config.json"
TEMPLATE_DIR = BASE_DIR / "tests" / "fixtures" / "robot_templates"


@pytest.fixture(autouse=True)
def reset_blueprint_sources() -> Generator[None, None, None]:
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
    """Without templates the converter renders generic OS/Process keywords."""
    configure_template_sources([])
    json_data = load_json_file(str(EXAMPLE_PATH))

    robot_output = JsonToRobotConverter().convert_json_data(json_data)

    # Verify basic structure
    assert "*** Settings ***" in robot_output
    assert "Library    Process" in robot_output
    assert "Library    RequestsLibrary" in robot_output
    assert "SSHLibrary" not in robot_output
    assert "Switch Connection" not in robot_output


def test_cli_blueprint_uses_template_substitutions_when_available() -> None:
    """Verify learned patterns from templates influence the rendered output."""
    configure_template_sources([str(TEMPLATE_DIR)])
    json_data = load_json_file(str(EXAMPLE_PATH))

    robot_output = JsonToRobotConverter().convert_json_data(json_data)

    # Verify templates influenced output
    assert "Resource            resources/Setup.resource" in robot_output

    # Verify learned pattern from set_config.robot is applied for CLI command
    assert (
        "Read Until Regexp    setconfig task (\\S+) completed successfully!"
        in robot_output
    )
    assert "Logger    step_num=1" in robot_output

    # Resources were discovered from templates
    assert "# No resource imports discovered" not in robot_output

    # Both steps should use SSHLibrary
    assert "Switch Connection" in robot_output
