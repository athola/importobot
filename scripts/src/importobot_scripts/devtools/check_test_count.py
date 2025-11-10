#!/usr/bin/env python3
"""Verify pytest collection count meets baseline requirements.

This script ensures the test suite maintains a minimum number of tests,
helping catch issues where tests might be accidentally skipped or not
collected properly. This is critical for ensuring coverage accuracy.
"""

import re
import subprocess
import sys

# Minimum expected test count (set conservatively to allow some variation)
MIN_TEST_COUNT = 2000

# Expected approximate test count for informational purposes
EXPECTED_TEST_COUNT = 2105


def get_test_count() -> int:
    """Run pytest collection and extract the test count.

    Returns:
        int: Number of tests collected

    Raises:
        RuntimeError: If pytest collection fails or output cannot be parsed
    """
    # Run pytest with collection only
    result = subprocess.run(
        ["pytest", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"pytest collection failed with exit code {result.returncode}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    # Parse the output to find the test count.
    # Format resembles: "===== N tests collected in X.XXs =====".
    output = result.stdout + result.stderr
    match = re.search(r"(\d+) tests? collected", output)

    if not match:
        raise RuntimeError(
            f"Could not parse test count from pytest output.\nOutput: {output}"
        )

    return int(match.group(1))


def main() -> int:
    """Verify test count meets baseline requirements.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        test_count = get_test_count()

        print(f"✓ Collected {test_count} tests")

        if test_count < MIN_TEST_COUNT:
            print(
                "✗ ERROR: Test count ("
                f"{test_count}) is below minimum baseline ({MIN_TEST_COUNT})",
                file=sys.stderr,
            )
            print(
                "  This suggests tests are being skipped or not collected properly.",
                file=sys.stderr,
            )
            print(
                f"  Expected approximately {EXPECTED_TEST_COUNT} tests.",
                file=sys.stderr,
            )
            return 1

        if test_count < EXPECTED_TEST_COUNT * 0.95:
            print(
                "⚠ WARNING: Test count ("
                f"{test_count}) is below expected count ({EXPECTED_TEST_COUNT})"
            )
            print("  This may indicate some tests are not being collected.")
            # Don't fail on warning, just alert

        print(f"✓ Test count verification passed (baseline: {MIN_TEST_COUNT})")
        return 0

    except Exception as e:
        print(f"✗ ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
