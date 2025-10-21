"""Integration tests verifying cross-template learning for CLI suites."""

from __future__ import annotations

from pathlib import Path

from importobot.core.converter import JsonToRobotConverter
from importobot.core.templates import configure_template_sources
from importobot.utils.json_utils import load_json_file


def test_hostname_inferred_from_setconfig_template(tmp_path: Path) -> None:
    """Hostname suite should be generated using knowledge learned from another template."""
    # Generate template inline to avoid tracking .robot files in git
    template_path = tmp_path / "set_config.robot"
    template_path.write_text(
        """*** Test Cases ***
Sample
    Switch Connection    Controller
    Write    setconfig --proc_name ${proc_name}
    ${setconfig_cli}=    Read Until Regexp    setconfig task (\\S+) completed successfully!
    Logger    step_num=1    result=${TRUE}    result_str=Task completed successfully.
    Log    Expected: no task errors

    Switch Connection    REMOTE_HOST
    ${setconfig_remote}=    Execute Command    ps -ely | grep ${proc_name}
    Log    Expected: process found
""",
        encoding="utf-8",
    )

    configure_template_sources([str(template_path)])

    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "examples" / "json" / "hostname.json"

    json_data = load_json_file(str(json_path))
    converter = JsonToRobotConverter()
    robot_output = converter.convert_json_data(json_data)

    assert "Switch Connection    REMOTE_HOST" in robot_output
    assert "Log    Expected: Hostname of the target shown" in robot_output
    assert "Read Until Regexp    hostname task" in robot_output
    assert "Should Contain    ${hostname_cli}    ${hostname}" in robot_output
    assert (
        "Should Be Equal As Strings    ${hostname_cli}    ${hostname}" in robot_output
    )


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
    ${setconfig_cli}=    Read Until Regexp    setconfig task (\\S+) completed successfully!
    Logger    step_num=1    result=${TRUE}    result_str=Task completed successfully.
    Log    Expected: no task errors

    Switch Connection    REMOTE_HOST
    ${setconfig_remote}=    Execute Command    ps -ely | grep ${proc_name}
    Log    Expected: process found
""",
        encoding="utf-8",
    )

    configure_template_sources([str(template_path)])

    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "examples" / "json" / "ip.json"
    json_data = load_json_file(str(json_path))

    output = JsonToRobotConverter().convert_json_data(json_data)

    assert "Switch Connection    Target" in output
    assert (
        "${ip_cli}=    Read Until Regexp    ip task (\\S+) completed successfully!"
        in output
    )
    assert "${ip}=    Execute Command    ip addr" in output
    assert "Should Be Equal As Strings    ${ip}    ${ip_cli}" in output
    assert (
        "Should Contain    ${ip}    all interfaces and their type, mac address, ipv4/6 addresses"
        in output
    )
