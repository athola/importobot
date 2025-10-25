"""Integration tests verifying cross-template learning for CLI suites."""

from __future__ import annotations

import os
from pathlib import Path

from importobot.core.converter import JsonToRobotConverter
from importobot.core.templates import configure_template_sources
from importobot.utils.json_utils import load_json_file


def test_hostname_inferred_from_setconfig_template(tmp_path: Path) -> None:
    """Hostname suite generated using knowledge from another template."""
    # Generate template inline to avoid tracking .robot files in git
    template_path = tmp_path / "set_config.robot"
    template_path.write_text(
        """*** Test Cases ***
Sample
    Switch Connection    Controller
    Write    setconfig --proc_name ${proc_name}
    ${setconfig_cli}=    Read Until Regexp    setconfig task completed successfully!
    Logger    step_num=1    result=${TRUE}    result_str=Task completed successfully.
    Log    Expected: no task errors

    Switch Connection    REMOTE_HOST
    ${setconfig_remote}=    Execute Command    ps -ely | grep ${proc_name}
    Log    Expected: process found
""",
        encoding="utf-8",
    )

    os.environ["IMPORTOBOT_ALLOW_EXTERNAL_TEMPLATES"] = "1"
    try:
        configure_template_sources([str(template_path)])
    finally:
        os.environ.pop("IMPORTOBOT_ALLOW_EXTERNAL_TEMPLATES", None)

    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "examples" / "json" / "hostname.json"

    json_data = load_json_file(str(json_path))
    converter = JsonToRobotConverter()
    robot_output = converter.convert_json_data(json_data)

    assert "Switch Connection    Cli" in robot_output
    assert "Switch Connection    Remote_Host" in robot_output
    assert "${hostname}=    Execute Command    hostname" in robot_output
    assert "Should Be Equal As Strings" in robot_output


def test_ip_task_infers_step_relationships_from_minimal_template(
    tmp_path: Path,
) -> None:
    """IP task JSON should produce comparisons by learning from a minimal template."""

    template_path = tmp_path / "set_config.robot"
    template_path.write_text(
        """*** Test Cases ***
Sample
    Switch Connection    Controller
    Write    setconfig --proc_name ${proc_name}
    ${setconfig_cli}=    Read Until Regexp    setconfig task completed successfully!
    Logger    step_num=1    result=${TRUE}    result_str=Task completed successfully.
    Log    Expected: no task errors

    Switch Connection    REMOTE_HOST
    ${setconfig_remote}=    Execute Command    ps -ely | grep ${proc_name}
    Log    Expected: process found
""",
        encoding="utf-8",
    )

    os.environ["IMPORTOBOT_ALLOW_EXTERNAL_TEMPLATES"] = "1"
    try:
        configure_template_sources([str(template_path)])
    finally:
        os.environ.pop("IMPORTOBOT_ALLOW_EXTERNAL_TEMPLATES", None)

    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "examples" / "json" / "ip.json"
    json_data = load_json_file(str(json_path))

    output = JsonToRobotConverter().convert_json_data(json_data)

    assert "Switch Connection    Target" in output
    assert "Switch Connection    Cli" in output
    assert "${ip}=    Execute Command    ip addr" in output
    assert "Should Be Equal As Strings    ${ip}    ${ip}" in output


def test_setconfig_template_applies_learned_keywords(tmp_path: Path) -> None:
    """Templates should apply their stored connection and keyword patterns."""
    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "examples" / "json" / "set_config.json"
    json_data = load_json_file(str(json_path))

    configure_template_sources([])
    default_output = JsonToRobotConverter().convert_json_data(json_data)

    template_path = tmp_path / "set_config.robot"
    template_content = (
        "*** Test Cases ***\nSample\n    Switch Connection    Controller\n"
        "Write    setconfig --proc_name ${proc_name}\n"
        "${setconfig_cli}=    Read Until Regexp    setconfig task (\\S+) completed "
        "successfully!\n"
        "Logger    step_num=1    result=${TRUE}    result_str=Task completed "
        "successfully.\n"
        "Log    Expected: no task errors\n\n"
        "Switch Connection    REMOTE_HOST\n"
        "${setconfig_remote}=    Execute Command    ps -ely | grep ${proc_name}\n"
        "Log    Expected: process found\n"
    )
    template_path.write_text(template_content, encoding="utf-8")

    os.environ["IMPORTOBOT_ALLOW_EXTERNAL_TEMPLATES"] = "1"
    try:
        configure_template_sources([str(template_path)])
    finally:
        os.environ.pop("IMPORTOBOT_ALLOW_EXTERNAL_TEMPLATES", None)

    robot_output = JsonToRobotConverter().convert_json_data(json_data)

    assert "Logger    step_num=1" in robot_output
    assert "Logger    step_num=1" not in default_output


def test_setconfig_template_influences_hash_file(tmp_path: Path) -> None:
    """Templates should not alter unrelated hash_file conversions."""
    data = load_json_file("examples/json/hash_file.json")

    configure_template_sources([])
    default_output = JsonToRobotConverter().convert_json_data(data)

    template_path = tmp_path / "set_config.robot"
    template_content = (
        "*** Test Cases ***\nSample\n    Switch Connection    Controller\n"
        "Write    setconfig --proc_name ${proc_name}\n"
        "${setconfig_cli}=    Read Until Regexp    setconfig task (\\S+) completed "
        "successfully!\n"
        "Logger    step_num=1    result=${TRUE}    result_str=Task completed "
        "successfully.\n"
        "Log    Expected: no task errors\n\n"
        "Switch Connection    REMOTE_HOST\n"
        "${setconfig_remote}=    Execute Command    ps -ely | grep ${proc_name}\n"
        "Log    Expected: process found\n"
    )
    template_path.write_text(template_content, encoding="utf-8")

    os.environ["IMPORTOBOT_ALLOW_EXTERNAL_TEMPLATES"] = "1"
    try:
        configure_template_sources([str(template_path)])
    finally:
        os.environ.pop("IMPORTOBOT_ALLOW_EXTERNAL_TEMPLATES", None)

    templated_output = JsonToRobotConverter().convert_json_data(data)

    assert templated_output != default_output
    assert "Switch Connection    Remote" in templated_output
    assert "Execute Command    sha256sum" in templated_output
    assert "Should Be Equal As Strings" not in default_output
