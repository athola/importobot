"""Property-based tests for blueprint template learning."""

from __future__ import annotations

import string
from collections.abc import Iterator
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import DrawFn

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


safe_identifier_chars = string.ascii_letters + string.digits + "-_"
safe_message_chars = safe_identifier_chars + " "


def _safe_placeholder() -> st.SearchStrategy[str]:
    valid_start = string.ascii_letters
    body_chars = safe_identifier_chars
    head = st.text(alphabet=valid_start, min_size=1, max_size=1)
    tail = st.text(alphabet=body_chars, min_size=0, max_size=5)
    return (
        st.tuples(head, tail)
        .map(lambda parts: "".join(parts))
        .filter(lambda name: not name.startswith("__"))
    )


def _message_tokens() -> st.SearchStrategy[str]:
    simple_word = st.text(
        alphabet=safe_message_chars,
        min_size=1,
        max_size=8,
    )
    placeholder = _safe_placeholder().map(lambda name: f"${{{name}}}")
    return st.one_of(simple_word, placeholder)


@st.composite
def robot_templates(draw: DrawFn) -> tuple[str, str]:
    template_name = draw(
        st.text(
            alphabet=safe_identifier_chars.replace("-", ""), min_size=3, max_size=12
        )
    )
    command_token = draw(
        st.text(alphabet=string.ascii_lowercase, min_size=3, max_size=10)
    )
    additional_args = draw(
        st.lists(
            st.text(alphabet=safe_identifier_chars, min_size=1, max_size=6),
            min_size=0,
            max_size=3,
        )
    )
    connection = draw(st.text(alphabet=safe_identifier_chars, min_size=3, max_size=10))
    tokens = draw(st.lists(_message_tokens(), min_size=1, max_size=4))
    base_message = " ".join(tokens)
    control_prefix = draw(st.text(alphabet="\r\ufeff\t", min_size=0, max_size=1))
    control_suffix = draw(st.text(alphabet="\r\ufeff\t", min_size=0, max_size=1))
    message = f"{control_prefix}{base_message}{control_suffix}"
    newline = draw(st.sampled_from(["\n", "\r\n"]))

    content_lines = [
        "*** Test Cases ***",
        template_name,
        f"    Switch Connection    {connection}",
        f"    Write    {command_token} {' '.join(additional_args)}".rstrip(),
        f"    Log    {message}",
        "",
    ]

    content = newline.join(content_lines)
    if draw(st.booleans()):
        content = "\ufeff" + content

    return content, command_token


@settings(max_examples=60, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(template_data=robot_templates())
@example(
    template_data=(
        "\ufeff*** Test Cases ***\r\nExample\r\n    Switch Connection    Controller\r\n"
        "    Write    setconfig\r\n    Log    Value ${placeholder}\r\n",
        "setconfig",
    )
)
def test_configure_template_sources_generative(
    template_data: tuple[str, str], tmp_path: Path
) -> None:
    """configure_template_sources should sanitise and learn across varied inputs."""
    content, command_token = template_data
    template_path = tmp_path / "generated.robot"
    template_path.write_text(content, encoding="utf-8")

    registry.configure_template_sources([str(template_path)])

    template = registry.get_template("generated")
    assert template is not None

    sanitized = template.template
    assert "\r" not in sanitized
    assert "\ufeff" not in sanitized
    assert all(ch.isprintable() or ch in {"\n", "\t"} for ch in sanitized)

    pattern = registry.find_step_pattern(command_token=command_token.lower())
    assert pattern is not None
