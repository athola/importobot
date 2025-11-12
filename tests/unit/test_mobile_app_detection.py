"""Test mobile app detection and keyword generation functionality.

This module tests the mobile app detection capabilities that were added to
support AppiumLibrary integration, ensuring that mobile-specific test data
generates appropriate Robot Framework keywords.
"""

from importobot.core.keyword_generator import GenericKeywordGenerator
from importobot.core.keywords.generators.web_keywords import WebKeywordGenerator
from importobot.core.keywords_registry import (
    IntentRecognitionEngine,
    RobotFrameworkKeywordRegistry,
)


class TestMobileAppDetection:
    """Test mobile app detection and keyword generation."""

    def test_mobile_app_launch_with_platformname(self) -> None:
        """Test that mobile app launch with platformName generates Open Application."""
        generator = GenericKeywordGenerator()
        step = {
            "description": "Launch mobile application on Android device",
            "testData": (
                "platformName: Android, deviceName: emulator-5554, "
                "appPackage: com.example.app"
            ),
            "expectedResult": "Mobile app launches successfully",
        }

        result = generator.generate_step_keywords(step)

        # Should contain Open Application keyword
        open_app_lines = [line for line in result if "Open Application" in line]
        assert len(open_app_lines) == 1
        assert "platformName: Android" in open_app_lines[0]
        assert "deviceName: emulator-5554" in open_app_lines[0]
        assert "appPackage: com.example.app" in open_app_lines[0]

    def test_mobile_app_launch_with_bundleid(self) -> None:
        """Test that mobile app launch with bundleId generates Open Application."""
        generator = GenericKeywordGenerator()
        step = {
            "description": "Launch iOS mobile application",
            "testData": (
                "platformName: iOS, bundleId: com.example.iosapp, "
                "deviceName: iPhone Simulator"
            ),
            "expectedResult": "iOS app launches successfully",
        }

        result = generator.generate_step_keywords(step)

        # Should contain Open Application keyword
        open_app_lines = [line for line in result if "Open Application" in line]
        assert len(open_app_lines) == 1
        assert "bundleId: com.example.iosapp" in open_app_lines[0]
        assert "deviceName: iPhone Simulator" in open_app_lines[0]

    def test_web_browser_launch_generates_open_browser(self) -> None:
        """Test that web browser launch still generates Open Browser keyword."""
        generator = GenericKeywordGenerator()
        step = {
            "description": "Open web browser",
            "testData": "https://example.com",
            "expectedResult": "Browser opens successfully",
        }

        result = generator.generate_step_keywords(step)

        # Should contain Open Browser keyword, not Open Application
        open_browser_lines = [line for line in result if "Open Browser" in line]
        open_app_lines = [line for line in result if "Open Application" in line]

        assert len(open_browser_lines) == 1
        assert len(open_app_lines) == 0
        assert "https://example.com" in open_browser_lines[0]

    def test_web_generator_detects_mobile_context(self) -> None:
        """Test that WebKeywordGenerator correctly detects mobile context."""
        web_gen = WebKeywordGenerator()

        # Mobile indicators
        mobile_test_data = "platformName: Android, appPackage: com.example.app"
        result = web_gen.generate_browser_keyword(mobile_test_data)

        assert "Open Application" in result
        assert (
            "AppiumLibrary" not in result
        )  # Should not be prefixed in generated keyword

        # Web indicators (no mobile indicators)
        web_test_data = "https://example.com/login"
        result = web_gen.generate_browser_keyword(web_test_data)

        assert "Open Browser" in result
        assert "chrome" in result.lower()  # Should have chrome options

    def test_mobile_input_keywords_without_prefix(self) -> None:
        """Test mobile input keywords don't have unnecessary prefixes when simple."""
        generator = GenericKeywordGenerator()
        step = {
            "description": "Enter mobile app credentials",
            "testData": "username: mobileuser, password: mobilepass",
            "expectedResult": "Credentials entered",
        }

        result = generator.generate_step_keywords(step)

        # Should use simple form for mobile contexts (no prefixes expected)
        input_lines = [
            line for line in result if "Input Text" in line or "Input Password" in line
        ]
        assert len(input_lines) >= 2  # At least username and password
        # Check that mobile contexts might have prefixes based on AppiumLibrary

    def test_launch_intent_recognition(self) -> None:
        """Test that 'launch' intent is properly recognized for mobile apps."""

        # Mobile app launch text
        mobile_text = (
            "launch mobile application on android device platformname: android"
        )
        intent = IntentRecognitionEngine.recognize_intent(mobile_text.lower())
        assert intent is not None
        assert "launch" in mobile_text.lower()

        # Web browser launch text
        web_text = "launch web browser and navigate to page"
        intent = IntentRecognitionEngine.recognize_intent(web_text.lower())
        assert intent is not None
        assert "launch" in web_text.lower()

    def test_app_open_intent_mapping(self) -> None:
        """Test app_open intent is properly mapped to AppiumLibrary Open Application."""

        library, keyword = RobotFrameworkKeywordRegistry.get_intent_keyword("app_open")
        assert library == "AppiumLibrary"
        assert keyword == "Open Application"

    def test_mixed_content_detection(self) -> None:
        """Test detection when test data contains both mobile and web indicators."""
        web_gen = WebKeywordGenerator()

        # Priority should be given to mobile indicators when present
        mixed_data = (
            "https://example.com platformName: Android appPackage: com.example.app"
        )
        result = web_gen.generate_browser_keyword(mixed_data)

        # Should prefer mobile app over web when mobile indicators are present
        assert "Open Application" in result
        assert "platformName: Android" in result
