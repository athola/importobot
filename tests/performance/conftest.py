"""Mark performance tests as slow for default test runs."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.slow


def pytest_collection_modifyitems(session, config, items):
    """Ensure all performance tests carry the slow marker."""
    base_dir = Path(__file__).parent.resolve()
    for item in items:
        try:
            path = Path(item.fspath).resolve()
        except TypeError:  # pragma: no cover - non-filesystem items
            continue
        if base_dir in path.parents or path.parent == base_dir:
            item.add_marker(pytest.mark.slow)
