"""Generative tests for API retrieval helpers."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from importobot.config import _parse_project_identifier, _split_tokens

token_chars = st.characters(
    blacklist_characters=[","],
    min_codepoint=33,
    max_codepoint=126,
)


@given(st.data())
@settings(max_examples=75)
def test_split_tokens_roundtrip(data: st.DataObject) -> None:
    """Splitting tokens should behave like comma parsing with trimming."""
    tokens = data.draw(
        st.lists(
            st.text(token_chars, min_size=1, max_size=8),
            min_size=0,
            max_size=5,
        )
    )
    if not tokens:
        raw = data.draw(st.text(alphabet=", \t", min_size=0, max_size=5))
    else:
        separators = data.draw(
            st.lists(
                st.text(alphabet=", \t", min_size=1, max_size=3),
                min_size=len(tokens) - 1,
                max_size=len(tokens) - 1,
            )
        )
        prefixes = data.draw(
            st.lists(
                st.text(alphabet=" \t", min_size=0, max_size=2),
                min_size=len(tokens),
                max_size=len(tokens),
            )
        )
        parts: list[str] = []
        for index, token in enumerate(tokens):
            parts.append(prefixes[index])
            parts.append(token)
            if index < len(separators):
                parts.append(separators[index])
        raw = "".join(parts)

    parsed = _split_tokens(raw)
    expected = [part.strip() for part in raw.split(",") if part.strip()]
    assert parsed == expected


@given(st.one_of(st.none(), st.text(min_size=0, max_size=8)))
@settings(max_examples=60)
def test_parse_project_identifier_behaviour(value: str | None) -> None:
    """Parsing project identifiers should split numeric and textual inputs."""
    name, project_id = _parse_project_identifier(value)

    if value is None or not value.strip():
        assert name is None
        assert project_id is None
        return

    stripped = value.strip()
    if stripped.isdigit():
        if stripped.isascii():
            assert name is None
            assert project_id == int(stripped)
        else:
            assert name == stripped
            assert project_id is None
    else:
        assert name == stripped
        assert project_id is None
