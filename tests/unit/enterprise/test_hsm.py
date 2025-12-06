"""Tests for the software HSM adapter."""

from __future__ import annotations

import pytest

from importobot_enterprise.hsm import HSMError, SoftwareHSM


def test_store_and_retrieve_key() -> None:
    hsm = SoftwareHSM()
    hsm.store_key("ci-token", "supersecret")

    assert hsm.retrieve_key("ci-token") == "supersecret"


def test_rotate_key_replaces_secret() -> None:
    hsm = SoftwareHSM()
    hsm.store_key("ci-token", "old")
    hsm.rotate_key("ci-token", "new")

    assert hsm.retrieve_key("ci-token") == "new"


def test_duplicate_alias_raises() -> None:
    hsm = SoftwareHSM()
    hsm.store_key("dup", "value")
    with pytest.raises(HSMError):
        hsm.store_key("dup", "other")
