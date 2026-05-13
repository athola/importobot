"""Packaged data resources for importobot.

This package only contains data files (YAML, JSON) that are read at
runtime via ``importlib.resources``. It is intentionally empty of
executable code so the data subdirectory ships inside the installed
wheel without dragging additional logic.
"""
