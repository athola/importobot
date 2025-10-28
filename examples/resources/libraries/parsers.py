"""Utilities for parsing CLI command outputs."""

import ast
import re


def parse_table_json(output):
    """Parse json string output into a list of lists.

    Args:
        output (str): The raw string output of a CLI command
            that would return a table (in debug mode it is a list of lists)

    Returns:
        List[List[Any]]:
            List of lists if correctly parsed, empty list otherwise.

    """
    parsed_lists = re.search(r".*(\[\[.*]]).*", output)
    if not parsed_lists:
        return []
    parsed_lists_str = parsed_lists.group(1)
    list_of_lists = ast.literal_eval(parsed_lists_str)
    return list_of_lists
