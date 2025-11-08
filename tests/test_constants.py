"""Test constants to eliminate hard-coded magic numbers across test suite.

This module provides named constants for test assertions, making tests
more readable and maintainable. All magic numbers and hard-coded values
should be defined here with clear names and documentation.

Current Status
--------------
Total constants: 55
Remaining capacity before split: 145 constants
Last updated: 2025-11-06

Organization Guidelines
-----------------------
Constants are grouped into 9 logical categories for maintainability:
1. Exit codes and CLI behavior (4 constants)
2. Security validation expectations (4 constants)
3. Distribution and statistical test values (9 constants)
4. Resource limits and performance parameters (4 constants)
5. Algorithm-specific parameters (18 constants: optimizer, annealing, genetic)
6. Test suite sizing and parser expectations (5 constants)
7. Framework-specific constants (3 constants: Robot Framework, SSH, Selenium)
8. Security test paths (3 constants)
9. Timeout values, file sizes, and cache config (9 constants)

Future Growth Strategy
----------------------
When this module exceeds 200 constants, consider splitting into:
- tests/constants/cli.py (exit codes, CLI test counts)
- tests/constants/security.py (security paths, warning counts)
- tests/constants/algorithms.py (optimizer, annealing, genetic)
- tests/constants/resources.py (limits, timeouts, file sizes, cache)
- tests/constants/frameworks.py (Robot Framework, SSH, Selenium)

For now, the single-file approach with clear section markers (=========)
provides sufficient organization without over-engineering the structure.
Section markers make it easy to navigate and prevent "grab-bag" syndrome.
"""

# =============================================================================
# EXIT CODES AND CLI BEHAVIOR
# =============================================================================

EXIT_CODE_SUCCESS = 0
EXIT_CODE_INVALID_ARGS = 2
EXIT_CODE_FILE_NOT_FOUND = 1


# =============================================================================
# SECURITY VALIDATION EXPECTATIONS
# =============================================================================
SECURITY_SSH_PASSWORD_WARNING_COUNT = 2  # SSH password + hardcoded credential
SECURITY_SUDO_COMMAND_WARNING_COUNT = 1
SECURITY_DANGEROUS_PATH_WARNING_COUNT = 1
SECURITY_MULTIPLE_ISSUES_WARNING_COUNT = 3  # Combined warnings


# =============================================================================
# DISTRIBUTION AND STATISTICAL TEST VALUES
# =============================================================================
DISTRIBUTION_SMALL_TOTAL = 60
DISTRIBUTION_LARGE_TOTAL = 1000

# Category1 expected distribution results
DISTRIBUTION_CATEGORY1_SMALL = 10  # 1/6 * 60
DISTRIBUTION_CATEGORY1_LARGE = 167  # 1/6 * 1000 (rounded)

# Category2 expected distribution results
DISTRIBUTION_CATEGORY2_SMALL = 20  # 2/6 * 60
DISTRIBUTION_CATEGORY2_LARGE = 333  # 2/6 * 1000 (rounded)

# Category3 expected distribution results
DISTRIBUTION_CATEGORY3_SMALL = 30  # 3/6 * 60
DISTRIBUTION_CATEGORY3_LARGE = 500  # 3/6 * 1000


# =============================================================================
# RESOURCE LIMITS AND PERFORMANCE PARAMETERS
# =============================================================================
RESOURCE_LIMIT_MAX_OPERATIONS = 100
RESOURCE_LIMIT_MAX_FILE_SIZE_MB = 50
RESOURCE_LIMIT_MAX_MEMORY_MB = 512
RESOURCE_LIMIT_MAX_TEST_CASES = 10000


# =============================================================================
# ALGORITHM-SPECIFIC PARAMETERS
# =============================================================================

# Optimization test parameters
OPTIMIZER_DEFAULT_LEARNING_RATE = 0.01
OPTIMIZER_DEFAULT_MOMENTUM = 0.9
OPTIMIZER_DEFAULT_MAX_ITERATIONS = 100
OPTIMIZER_TOLERANCE = 1e-6

# Annealing test parameters
ANNEALING_INITIAL_TEMP = 100.0
ANNEALING_MIN_TEMP = 0.01
ANNEALING_COOLING_RATE = 0.95
ANNEALING_MAX_ITERATIONS = 1000

# Genetic algorithm test parameters
GENETIC_POPULATION_SIZE = 50
GENETIC_GENERATIONS = 100
GENETIC_MUTATION_RATE = 0.1
GENETIC_CROSSOVER_RATE = 0.8
GENETIC_ELITISM_COUNT = 5


# =============================================================================
# TEST SUITE SIZING
# =============================================================================
SMALL_TEST_SUITE_SIZE = 5
MEDIUM_TEST_SUITE_SIZE = 50
LARGE_TEST_SUITE_SIZE = 500

# Parser test expectations
PARSER_EXPECTED_TEST_CASE_COUNT = 2
PARSER_EXPECTED_STEP_COUNT_PER_TEST = 3


# =============================================================================
# FRAMEWORK-SPECIFIC CONSTANTS
# =============================================================================

# Robot Framework
ROBOT_FRAMEWORK_ARGUMENT_SEPARATOR_LENGTH = 4  # Length of "    " (4 spaces)

# SSH Library
SSH_LIBRARY_KEYWORD_COUNT = 42  # Total number of SSH keywords in Robot Framework

# Selenium Library
SELENIUM_LIBRARY_COMMON_KEYWORD_COUNT = 10  # Common keywords to test


# =============================================================================
# SECURITY TEST PATHS
# =============================================================================

SECURITY_SENSITIVE_PATH_PASSWD = "/etc/passwd"
SECURITY_SENSITIVE_PATH_SHADOW = "/etc/shadow"
SECURITY_SENSITIVE_PATH_SUDOERS = "/etc/sudoers"


# =============================================================================
# TIMEOUT VALUES AND FILE SIZES
# =============================================================================

# Timeout values (in seconds)
TIMEOUT_SHORT = 1
TIMEOUT_MEDIUM = 5
TIMEOUT_LONG = 30

# File size limits for testing
FILE_SIZE_SMALL_BYTES = 1024  # 1 KB
FILE_SIZE_MEDIUM_BYTES = 1024 * 1024  # 1 MB
FILE_SIZE_LARGE_BYTES = 10 * 1024 * 1024  # 10 MB


# =============================================================================
# CACHE CONFIGURATION
# =============================================================================
CACHE_DEFAULT_SIZE_MB = 100
CACHE_MIN_SIZE_MB = 10
CACHE_MAX_SIZE_MB = 1000


# =============================================================================
# CLI TEST FILE COUNTS
# =============================================================================
CLI_TEST_MULTIPLE_FILES_COUNT = 2  # Number of files for multi-file CLI tests
CLI_TEST_DIRECTORY_FILES_COUNT = 3  # Number of files for directory CLI tests
CLI_TEST_BATCH_FILES_COUNT = 5  # Number of files for batch processing CLI tests
