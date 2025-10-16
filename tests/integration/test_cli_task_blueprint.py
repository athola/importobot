"""Integration tests for the CLI task Robot blueprint."""

from __future__ import annotations

from pathlib import Path

from importobot.core.converter import JsonToRobotConverter
from importobot.core.templates import configure_template_sources
from importobot.utils.json_utils import load_json_file


def test_cli_task_blueprint_matches_expected() -> None:
    """Ensure CLI task JSON converts to the expected Robot output."""
    base_dir = Path(__file__).resolve().parents[2]
    example_path = base_dir / "examples" / "json" / "set_config.json"
    template_dir = base_dir / "tests" / "fixtures" / "robot_templates"
    configure_template_sources([str(template_dir)])
    json_data = load_json_file(str(example_path))

    robot_output = JsonToRobotConverter().convert_json_data(json_data)

    assert (
        "${setconfig_cli}=    Read Until Regexp    setconfig task (\\S+) completed successfully!"
        in robot_output
    )
    assert "Log    Expected: no task errors" in robot_output
    assert "${ps}=    Execute Command    ps -ely | grep mycustomname" in robot_output
    assert "Log    Expected: mycustomname found" in robot_output
