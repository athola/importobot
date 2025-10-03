"""Configuration for invariant tests using Hypothesis.

This module provides shared configuration and fixtures for property-based
invariant testing across the entire codebase.
"""

import pytest
from hypothesis import Verbosity, settings

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
def invariant_test_session():
    """Session-wide fixture for invariant test setup."""
    print("\n🔬 Starting system-wide invariant test session")
    yield
    print("\n✅ Invariant test session completed")


@pytest.fixture
def clean_temp_dir(tmp_path):
    """Provide a clean temporary directory for each test."""
    yield tmp_path
    # Cleanup is automatic with tmp_path
