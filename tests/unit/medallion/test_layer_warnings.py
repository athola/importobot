"""Runtime warning tests for Silver and Gold layers."""

from __future__ import annotations

import warnings

import pytest

from importobot.medallion.gold_layer import GoldLayer
from importobot.medallion.silver_layer import SilverLayer


@pytest.mark.parametrize("layer_cls", [SilverLayer, GoldLayer])
def test_placeholder_layers_emit_warning(layer_cls: type) -> None:
    """Ensure placeholder layer implementations emit a runtime warning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        layer_cls()

    assert any(
        "placeholder implementation" in str(w.message).lower() for w in caught
    ), "Expected placeholder warning was not emitted"
