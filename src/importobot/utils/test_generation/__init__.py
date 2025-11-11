"""Test generation package for Robot Framework test suites."""

from .generators import TestSuiteGenerator
from .ssh_authentication_tests import SSHAuthenticationTestGenerator
from .ssh_command_tests import SSHCommandTestGenerator
from .ssh_connection_tests import SSHConnectionTestGenerator
from .ssh_directory_tests import SSHDirectoryTestGenerator
from .ssh_file_tests import SSHFileTestGenerator
from .ssh_interactive_tests import SSHInteractiveTestGenerator
from .ssh_logging_tests import SSHLoggingTestGenerator
from .ssh_test_data import SSHTestDataGenerator
from .templates import TemplateManager

__all__ = [
    "SSHAuthenticationTestGenerator",
    "SSHCommandTestGenerator",
    "SSHConnectionTestGenerator",
    "SSHDirectoryTestGenerator",
    "SSHFileTestGenerator",
    "SSHInteractiveTestGenerator",
    "SSHLoggingTestGenerator",
    "SSHTestDataGenerator",
    "TemplateManager",
    "TestSuiteGenerator",
]
