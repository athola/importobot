"""File conversion functionality."""

import json
from typing import Any, Dict

from importobot.core.parser import parse_json


def load_json(file_path: str) -> Dict[str, Any]:
    """Loads test data from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Could not find input file {file_path}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse JSON from {file_path}") from e


def save_robot_file(content: str, file_path: str) -> None:
    """Saves content to a Robot Framework file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        raise IOError(f"Could not write to file {file_path}: {str(e)}") from e


def convert_to_robot(input_file: str, output_file: str) -> None:
    """Converts a JSON file to a Robot Framework file."""
    json_data = load_json(input_file)
    robot_content = parse_json(json_data)
    save_robot_file(robot_content, output_file)
