"""Shared test data constants to avoid duplication across test files."""

# International characters test data used by multiple test modules
INTERNATIONAL_CHARACTERS_TEST_DATA = {
    "name": "Test Internacionalização (çãé) 🌍",
    "description": "Test with special characters: åäöüß and emoji 🎉✨",
    "steps": [
        {
            "step": "Enter special data: éñü 📝",
            "testData": "data with ñ and ç characters 🔤",
            "expectedResult": "Special characters handled correctly ✅",
        }
    ],
}

# Emoji-focused test data for Unicode edge cases
EMOJI_TEST_DATA = {
    "name": "🔐 Security Login Test 🚀",
    "description": "Test with various emoji types: 👤👥🔑🎯",
    "steps": [
        {
            "step": "Navigate to login page 🌐",
            "testData": "https://example.com/login 🔗",
            "expectedResult": "Login page displayed ✅",
        },
        {
            "step": "Enter credentials 🔑",
            "testData": "admin@test.com 📧",
            "expectedResult": "Credentials accepted 👍",
        },
        {
            "step": "Click submit button ➡️",
            "testData": "",
            "expectedResult": "User authenticated successfully ✨",
        },
    ],
}

# Mixed Unicode test data with emoji sequences and ZWJ
COMPLEX_UNICODE_TEST_DATA = {
    "name": "👨‍💻 Developer Workflow 🔧",
    "description": "Test complex emoji: 👨‍👩‍👧‍👦 family, 🏴‍☠️ flags, 🤝🏽 skin tones",
    "steps": [
        {
            "step": "Deploy application 🚀",
            "testData": "git push origin main 📤",
            "expectedResult": "Deployment successful 🎉",
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

# Sample Zephyr test case (commonly used in CLI and conversion tests)
SAMPLE_ZEPHYR_TEST_CASE = {
    "tests": [
        {
            "name": "Login Test Case",
            "description": "Test user login functionality",
            "steps": [
                {
                    "action": "Navigate to login page",
                    "expectedResult": "Login page is displayed",
                },
                {
                    "action": "Enter valid credentials",
                    "expectedResult": "Credentials are accepted",
                },
                {
                    "action": "Click login button",
                    "expectedResult": "User is logged in successfully",
                },
            ],
        }
    ]
}

# Enterprise login test case (commonly used in integration tests)
ENTERPRISE_LOGIN_TEST = {
    "name": "Enterprise Login Test",
    "description": "Automated login test for enterprise application",
    "steps": [
        {
            "step": "Navigate to login page",
            "testData": "https://app.enterprise.com/login",
            "expectedResult": "Login page displays",
        },
        {
            "step": "Enter username",
            "testData": "admin",
            "expectedResult": "Username field populated",
        },
        {
            "step": "Enter password",
            "testData": "password123",
            "expectedResult": "Password field populated",
        },
        {
            "step": "Click login button",
            "testData": "",
            "expectedResult": "User successfully logged in",
        },
    ],
}

# Simple web test case (for basic conversion testing)
SIMPLE_WEB_TEST = {
    "name": "Navigate to Example Website",
    "description": "Test basic web navigation",
    "steps": [
        {
            "action": "Go to https://example.com",
            "expectedResult": "Website loads successfully",
        }
    ],
}

# Database test case
SAMPLE_DATABASE_TEST = {
    "name": "Database Query Test",
    "description": "Test database connection and query",
    "steps": [
        {
            "action": "Connect to database",
            "testData": "host=localhost port=5432 dbname=test",
            "expectedResult": "Database connection established",
        },
        {
            "action": "Execute SELECT query",
            "testData": "SELECT * FROM users",
            "expectedResult": "Query returns results",
        },
    ],
}

# API test case
SAMPLE_API_TEST = {
    "name": "REST API Test",
    "description": "Test API endpoint",
    "steps": [
        {
            "action": "Send GET request to /api/users",
            "testData": "https://api.example.com/users",
            "expectedResult": "Response status code 200",
        },
        {
            "action": "Verify response contains user list",
            "testData": "",
            "expectedResult": "Response body contains users array",
        },
    ],
}
