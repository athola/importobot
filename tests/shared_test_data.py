"""Shared test data constants to avoid duplication across test files."""

# International characters test data used by multiple test modules
INTERNATIONAL_CHARACTERS_TEST_DATA = {
    "name": "Test Internacionalização (çãé)",
    "description": "Test with special characters: åäöüß",
    "steps": [
        {
            "step": "Enter special data: éñü",
            "testData": "data with ñ and ç characters",
            "expectedResult": "Special characters handled correctly",
        }
    ],
}

# Library detection test cases used by multiple test modules
LIBRARY_DETECTION_TEST_CASES = [
    ("ssh user@example.com", "SSHLibrary"),
    ("execute ssh command", "SSHLibrary"),
    ("navigate browser", "SeleniumLibrary"),
    ("api request", "RequestsLibrary"),
]

# SSH security topics used by multiple test modules
SSH_SECURITY_TOPICS = [
    "key-based authentication",
    "connection timeouts",
    "host key fingerprints",
    "dedicated test environments",
    "privileges",
    "audit trails",
    "credentials",
    "secrets",
]
