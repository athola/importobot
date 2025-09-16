"""Unit tests for Chrome options functionality."""

from unittest.mock import patch

from importobot.core.converter import JsonToRobotConverter


class TestChromeOptions:
    """Tests for Chrome options functionality."""

    def test_chrome_options_in_browser_keyword(self):
        """Test that Chrome options are properly added to browser keywords."""
        converter = JsonToRobotConverter()

        test_data = {
            "name": "Test with Browser",
            "steps": [
                {
                    "step": "Open browser to login page",
                    "testData": "URL: https://example.com/login",
                    "expectedResult": "Login page is displayed",
                }
            ],
        }

        result = converter.convert_json_data(test_data)

        # Verify that Chrome options are included in the Open Browser keyword
        assert "Open Browser" in result
        assert "options=" in result
        assert "--no-sandbox" in result
        assert "--disable-dev-shm-usage" in result
        assert "--disable-gpu" in result
        assert "--headless" in result
        assert "--disable-web-security" in result
        assert "--allow-running-insecure-content" in result

    def test_chrome_options_with_default_url(self):
        """Test that Chrome options work with default URL."""
        converter = JsonToRobotConverter()

        test_data = {
            "name": "Test with Default URL",
            "steps": [
                {
                    "step": "Open browser to login page",
                    "testData": "Some test data without URL",
                    "expectedResult": "Login page is displayed",
                }
            ],
        }

        with patch(
            "importobot.config.TEST_LOGIN_URL", "http://localhost:8000/login.html"
        ):
            result = converter.convert_json_data(test_data)

        # Verify that default URL is used and Chrome options are included
        assert "Open Browser" in result
        assert "http://localhost:8000/login.html" in result
        assert "options=" in result
        assert "--no-sandbox" in result
        assert "--headless" in result

    def test_chrome_options_format(self):
        """Test that Chrome options are formatted correctly."""
        converter = JsonToRobotConverter()

        test_data = {
            "name": "Test Chrome Options Format",
            "steps": [
                {
                    "step": "Navigate to page",
                    "testData": "URL: https://example.com",
                    "expectedResult": "Page loads successfully",
                }
            ],
        }

        result = converter.convert_json_data(test_data)

        # Verify the format of Chrome options
        # They should be in the format:
        # options=add_argument('--option1'); add_argument('--option2')
        assert "options=" in result
        assert "add_argument('--no-sandbox')" in result
        assert "add_argument('--disable-dev-shm-usage')" in result
        assert "add_argument('--disable-gpu')" in result
        assert "add_argument('--headless')" in result
        assert "add_argument('--disable-web-security')" in result
        assert "add_argument('--allow-running-insecure-content')" in result
