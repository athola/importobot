"""Unit tests for blueprint registry helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from importobot.core.templates.blueprints import registry


@pytest.fixture(autouse=True)
def _restrict_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def reset_registry_state() -> Iterator[None]:
    registry.TEMPLATE_REGISTRY.clear()
    registry.KNOWLEDGE_BASE.clear()
    registry.KEYWORD_LIBRARY.clear()
    registry.RESOURCE_IMPORTS.clear()
    registry.TEMPLATE_STATE["base_dir"] = None
    yield
    registry.TEMPLATE_REGISTRY.clear()
    registry.KNOWLEDGE_BASE.clear()
    registry.KEYWORD_LIBRARY.clear()
    registry.RESOURCE_IMPORTS.clear()
    registry.TEMPLATE_STATE["base_dir"] = None


def test_derive_template_keys_generates_variants() -> None:
    keys = registry.template_name_candidates("My Template")
    assert "My Template" in keys
    assert "my template" in keys
    assert "my_template" in keys
    assert "mytemplate" in keys


def test_configure_template_sources_registers_template(tmp_path: Path) -> None:
    template_file = tmp_path / "example.robot"
    template_file.write_text(
        "*** Test Cases ***\nSample\n    Log    Hello\n", encoding="utf-8"
    )

    registry.configure_template_sources([str(template_file)])

    template = registry.get_template("example")
    assert template is not None
    assert "Sample" in template.template


def test_configure_template_sources_learns_patterns(tmp_path: Path) -> None:
    content = """*** Test Cases ***
Sample
    Switch Connection    Controller
    Write    setconfig --proc_name foo
    ${result}=    Read Until Regexp    setconfig task completed
"""
    template_file = tmp_path / "setconfig.robot"
    template_file.write_text(content, encoding="utf-8")

    registry.configure_template_sources([str(template_file)])

    # Find by library+keyword
    pattern = registry.find_step_pattern(
        library="SSHLibrary", keyword="Write", command_token="setconfig"
    )
    assert pattern is not None
    assert pattern.library == "SSHLibrary"
    assert pattern.keyword == "Write"
    assert pattern.command_token == "setconfig"
    assert any("Read Until Regexp" in line for line in pattern.lines)

    # Can also find by command token alone
    pattern_by_token = registry.find_step_pattern(command_token="setconfig")
    assert pattern_by_token is not None
    assert pattern_by_token.command_token == "setconfig"


def test_configure_template_sources_skips_invalid_helpers(tmp_path: Path) -> None:
    bad_py = tmp_path / "broken.py"
    bad_py.write_text("def oops(:\n", encoding="utf-8")

    registry.configure_template_sources([str(bad_py)])

    assert len(registry.TEMPLATE_REGISTRY._templates) == 0


def test_configure_template_sources_rejects_large_files(tmp_path: Path) -> None:
    large_robot = tmp_path / "huge.robot"
    large_robot.write_text("*" * (2 * 1024 * 1024 + 10), encoding="utf-8")

    registry.configure_template_sources([str(large_robot)])

    assert len(registry.TEMPLATE_REGISTRY._templates) == 0


@pytest.mark.skipif(
    not hasattr(os, "symlink") or os.name == "nt", reason="Symlinks unavailable"
)
def test_configure_template_sources_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "source.robot"
    target.write_text("*** Test Cases ***\nCase\n    Log    Ok\n", encoding="utf-8")
    link = tmp_path / "link.robot"
    os.symlink(target, link)

    registry.configure_template_sources([str(link)])

    assert registry.get_template("link") is None


def test_configure_template_sources_rejects_binary_file(tmp_path: Path) -> None:
    binary_file = tmp_path / "binary.robot"
    binary_file.write_bytes(b"\x00\x01\x02non-text")

    registry.configure_template_sources([str(binary_file)])

    assert registry.get_template("binary") is None


def test_configure_template_sources_fails_on_security_scan(tmp_path: Path) -> None:
    insecure_template = tmp_path / "secrets.robot"
    insecure_template.write_text(
        "*** Test Cases ***\nCase\n    Log    password: hunter2\n", encoding="utf-8"
    )

    with pytest.raises(registry.TemplateSecurityViolation) as excinfo:
        registry.configure_template_sources([str(insecure_template)])

    assert "password" in str(excinfo.value).lower()
    assert registry.get_template("secrets") is None


def test_configure_template_sources_rejects_outside_cwd(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.robot"
    content = "*** Test Cases ***\nCase\n    Log    Outside\n"
    outside.write_text(content, encoding="utf-8")

    registry.configure_template_sources([str(outside)])

    assert registry.get_template("outside") is None


def test_configure_template_sources_rejects_parent_directory_reference(
    tmp_path: Path,
) -> None:
    """Explicit '..' path entries should be treated as traversal and skipped."""
    escape_target = tmp_path.parent / "escape.robot"
    escape_target.write_text(
        "*** Test Cases ***\nCase\n    Log    Escaped\n", encoding="utf-8"
    )

    registry.configure_template_sources([str(Path("..") / "escape.robot")])

    assert registry.get_template("escape") is None


def test_configure_template_sources_handles_unreadable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Unreadable files should trigger a warning and be skipped."""
    template_file = tmp_path / "unreadable.robot"
    template_file.write_text(
        "*** Test Cases ***\nCase\n    Log    Unreadable\n", encoding="utf-8"
    )

    original_read = Path.read_text

    def fake_read(
        self: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        if self == template_file:
            raise OSError("Permission denied")
        return original_read(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", fake_read)

    with caplog.at_level("WARNING"):
        registry.configure_template_sources([str(template_file)])

    assert registry.get_template("unreadable") is None
    assert any(
        "Failed to read template" in message or "Security scan failed" in message
        for message in caplog.messages
    )


def test_configure_template_sources_rejects_inline_python(tmp_path: Path) -> None:
    template_file = tmp_path / "unsafe.robot"
    template_file.write_text(
        "*** Test Cases ***\nCase\n    Log    ${{1+1}}\n", encoding="utf-8"
    )

    registry.configure_template_sources([str(template_file)])

    assert registry.get_template("unsafe") is None


def test_configure_template_sources_rejects_private_placeholder(tmp_path: Path) -> None:
    template_file = tmp_path / "private.robot"
    template_file.write_text(
        "*** Test Cases ***\nCase\n    Log    $__secret\n", encoding="utf-8"
    )

    registry.configure_template_sources([str(template_file)])

    assert registry.get_template("private") is None


def test_resource_with_evaluate_is_rejected(tmp_path: Path) -> None:
    resource = tmp_path / "helper.resource"
    resource.write_text(
        "*** Keywords ***\nEvaluate Helper\n    Evaluate    1+1\n", encoding="utf-8"
    )

    registry.configure_template_sources([str(resource)])

    assert registry.RESOURCE_IMPORTS == []


def test_sandboxed_template_render_safe_truncates_and_sanitises() -> None:
    template = registry.SandboxedTemplate("Value: $name")
    long_value = "a" * (registry.MAX_TEMPLATE_VALUE_LENGTH + 10)
    rendered = template.render_safe({"name": long_value + "\x00\x07"})
    assert rendered.startswith("Value: ")
    payload = rendered.split("Value: ", 1)[1]
    assert len(payload) == registry.MAX_TEMPLATE_VALUE_LENGTH
    assert "\x00" not in payload
    assert "\x07" not in payload
