"""Tests for medallion configuration helpers."""

from pathlib import Path

import pytest

from importobot.config import update_medallion_config
from importobot.medallion.storage.config import StorageConfig


def test_update_medallion_config_mutates_known_fields(tmp_path):
    """Known fields should be applied to the returned StorageConfig."""
    cfg = update_medallion_config(base_path=tmp_path, retention_days=42)

    assert isinstance(cfg, StorageConfig)
    assert cfg.base_path == Path(tmp_path)
    assert cfg.retention_days == 42


def test_update_medallion_config_rejects_invalid_instance():
    """Passing a non-StorageConfig instance should raise a TypeError."""
    with pytest.raises(TypeError):
        update_medallion_config(config=object())
