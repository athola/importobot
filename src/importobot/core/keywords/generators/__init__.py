"""Keyword generators for different domains.

This module provides domain-specific keyword generators that have been extracted
from the monolithic keywords.py file for better maintainability and modularity.
"""

from .api_keywords import APIKeywordGenerator
from .builtin_keywords import BuiltInKeywordGenerator
from .database_keywords import DatabaseKeywordGenerator
from .file_keywords import FileKeywordGenerator
from .operating_system_keywords import OperatingSystemKeywordGenerator
from .ssh_keywords import SSHKeywordGenerator
from .web_keywords import WebKeywordGenerator

__all__ = [
    "APIKeywordGenerator",
    "BuiltInKeywordGenerator",
    "DatabaseKeywordGenerator",
    "FileKeywordGenerator",
    "OperatingSystemKeywordGenerator",
    "SSHKeywordGenerator",
    "WebKeywordGenerator",
]
