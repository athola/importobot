"""Unit tests for secure file permission helpers."""

import os
import stat

from importobot.utils.file_operations import temporary_json_file


def test_temporary_file_has_restrictive_permissions() -> None:
    """Temporary files should be created with 0600 permissions."""
    data = {"test": "data"}

    with temporary_json_file(data) as path:
        mode = os.stat(path).st_mode
        assert stat.S_IMODE(mode) == 0o600
