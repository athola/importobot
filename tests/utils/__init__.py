"""Test utilities package.

This package provides reusable test utilities organized into focused modules:
- test_helpers: Core test utilities (Robot file parsing, test case creation)
- performance_utils: Performance testing utilities (adaptive thresholds, benchmarking)
"""

# Import submodules for direct access
from . import performance_utils, test_helpers

# Re-export commonly used functions for convenience
from .test_helpers import (
    create_test_case_base,
    measure_performance,
    parse_robot_file,
    run_robot_command,
    validate_test_script_structure,
)

__all__ = [
    "create_test_case_base",
    "measure_performance",
    "parse_robot_file",
    # Submodules
    "performance_utils",
    # Commonly used functions (re-exported from test_helpers)
    "run_robot_command",
    "test_helpers",
    "validate_test_script_structure",
]
