"""Configuration for invariant tests using Hypothesis.

This module provides shared configuration and fixtures for property-based
invariant testing across the entire codebase.
"""

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from hypothesis import Verbosity, settings

pytestmark = pytest.mark.slow


def pytest_collection_modifyitems(session: Any, config: Any, items: Any) -> None:
    """Mark invariant tests as slow to keep Hypothesis runs consistent."""
    base_dir = Path(__file__).parent.resolve()
    for item in items:
        try:
            path = Path(item.fspath).resolve()
        except TypeError:  # pragma: no cover
            continue
        if base_dir in path.parents or path.parent == base_dir:
            item.add_marker(pytest.mark.slow)


# Configure Hypothesis settings for invariant tests
settings.register_profile(
    "ci",
    max_examples=20,
    verbosity=Verbosity.normal,
    deadline=5000,  # 5 seconds per test
    suppress_health_check=[],
)

settings.register_profile(
    "dev",
    max_examples=100,
    verbosity=Verbosity.verbose,
    deadline=10000,  # 10 seconds per test
    suppress_health_check=[],
)

settings.register_profile(
    "thorough",
    max_examples=500,
    verbosity=Verbosity.verbose,
    deadline=30000,  # 30 seconds per test
    suppress_health_check=[],
)

# Use CI profile by default
settings.load_profile("ci")


@pytest.fixture(scope="session")
def invariant_test_session() -> Generator[None, None, None]:
    """Session-wide fixture for invariant test setup."""
    print("\n🔬 Starting system-wide invariant test session")
    yield
    print("\n Invariant test session completed")


@pytest.fixture
def clean_temp_dir(tmp_path: Path) -> Path:
    """Provide a clean temporary directory for each test."""
    return tmp_path
    # Cleanup is automatic with tmp_path
