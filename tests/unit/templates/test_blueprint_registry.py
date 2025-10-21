"""Unit tests for blueprint registry helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from importobot.core.templates.blueprints import registry


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

    pattern = registry.find_step_pattern("cli", "setconfig")
    assert pattern is not None
    assert pattern.command_token == "setconfig"
    assert any("Read Until Regexp" in line for line in pattern.lines)


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
