"""Pytest entrypoint for mutation testing.

Ensures the project source directory is on ``sys.path`` before delegating to
pytest. Mutmut executes tests from a temporary working tree (`mutants/`), so
relative imports would otherwise fail without this shim.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest


def _sync_tree(source_root: Path, destination_root: Path) -> None:
    if not source_root.exists():
        return

    for source_path in source_root.rglob("*"):
        relative_path = source_path.relative_to(source_root)
        destination_path = destination_root / relative_path

        if destination_path.exists():
            continue

        if source_path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
        else:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)


def main(argv: list[str] | None = None) -> int:
    # File moved from scripts/ to scripts/src/importobot_scripts/ (+2 levels)
    project_root = Path(__file__).resolve().parents[5]
    mutated_src = project_root / "src"
    original_src = project_root.parent / "src"
    if not original_src.exists():
        original_src = project_root / "src"
    _sync_tree(original_src, mutated_src)

    original_tests = project_root.parent / "tests"
    if not original_tests.exists():
        original_tests = project_root / "tests"
    _sync_tree(original_tests, project_root / "tests")

    sys.path.insert(0, str(mutated_src))
    sys.path.insert(0, str(project_root))
    if original_src.exists():
        sys.path.append(str(original_src))

    args = argv if argv is not None else sys.argv[1:]
    if not args:
        args = ["-q"]
    return pytest.main(list(args))


if __name__ == "__main__":
    raise SystemExit(main())
