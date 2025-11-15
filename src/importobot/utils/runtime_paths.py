"""Utilities for resolving Importobot runtime storage paths."""

from __future__ import annotations

import os
from pathlib import Path


def _resolve_base_dir() -> Path:
    """Return the base directory for Importobot runtime data."""
    env_home = os.getenv("IMPORTOBOT_HOME") or os.getenv("IMPORTOBOT_STATE_DIR")
    base = Path(env_home).expanduser() if env_home else Path.home() / ".importobot"

    base.mkdir(parents=True, exist_ok=True)
    return base


def get_runtime_subdir(name: str) -> Path:
    """Return a writable subdirectory under the Importobot runtime root."""
    base = _resolve_base_dir()
    target = base / name
    target.mkdir(parents=True, exist_ok=True)
    return target
