"""
Tests for the interactive demo script helper functions.

This module tests the refactored helper functions from scripts/interactive_demo.py
to ensure proper functionality and TDD compliance.
"""

# ruff: noqa: I001
# pylint: disable=C0411

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from importobot_scripts.demo_config import DemoConfig
from importobot_scripts.demo_validation import safe_remove_file
from importobot_scripts.demo_visualization import ChartFactory, VisualizationTheme
from importobot_scripts.interactive_demo import (
    _display_business_challenge,
    _display_business_impact,
)

from importobot.core.keyword_generator import GenericKeywordGenerator


class TestBusinessCaseHelpers:
    """Test business case helper functions."""

    @patch("builtins.print")
    def test_display_business_challenge(self, mock_print):
        """Test business challenge display function."""
        metrics = SimpleNamespace(
            test_cases=500, manual_time_per_test_days=1.5, daily_cost_usd=300
        )

        _display_business_challenge(metrics)

        # Verify print was called
        mock_print.assert_called()

        # Get the printed content
        printed_content = mock_print.call_args[0][0]

        # Verify key information is included
        assert "500+" in printed_content
        assert "1.5 days" in printed_content
        assert "$300" in printed_content
        assert "THE CHALLENGE:" in printed_content

    @patch("builtins.print")
    def test_display_business_impact(self, mock_print):
        """Test business impact display function."""
        business_metrics = {
            "speed_improvement": 50.0,
            "time_reduction_percent": 98.0,
            "cost_savings_usd": 125000,
            "roi_multiplier": 25.0,
            "manual_time_days": 100,
            "importobot_time_days": 2,
        }

        _display_business_impact(business_metrics)

        # Verify print was called
        mock_print.assert_called()

        # Get the printed content
        printed_content = mock_print.call_args[0][0]

        # Verify key information is included
        assert "50x faster" in printed_content
        assert "98.0% time reduction" in printed_content
        assert "125.0K" in printed_content  # format_large_number includes decimal
        assert "25x ROI" in printed_content
        assert "BUSINESS IMPACT:" in printed_content

    @patch("builtins.print")
    def test_display_business_impact_infinite_values(self, mock_print):
        """Test business impact display with infinite values."""
        business_metrics = {
            "speed_improvement": float("inf"),
            "time_reduction_percent": 99.9,
            "cost_savings_usd": 50000,
            "roi_multiplier": float("inf"),
            "manual_time_days": 1000,
            "importobot_time_days": 1,
        }

        _display_business_impact(business_metrics)

        # Get the printed content
        printed_content = mock_print.call_args[0][0]

        # Verify infinite values are handled properly
        assert "Dramatically faster" in printed_content
        assert "Infinite ROI" in printed_content


class TestUtilityHelpers:
    """Test utility helper functions."""

    def test_format_large_number(self):
        """Test large number formatting."""
        # Create a ChartFactory instance to access _format_large_number

        config = DemoConfig()
        theme = VisualizationTheme(config)
        chart_factory = ChartFactory(theme)

        # Test billions
        assert chart_factory.format_large_number(1500000000) == "1.5B"
        assert chart_factory.format_large_number(2000000000) == "2.0B"

        # Test millions
        assert chart_factory.format_large_number(1500000) == "1.5M"
        assert chart_factory.format_large_number(2000000) == "2.0M"

        # Test thousands
        assert chart_factory.format_large_number(1500) == "1.5K"
        assert chart_factory.format_large_number(2000) == "2.0K"

        # Test smaller numbers
        assert chart_factory.format_large_number(999) == "999"
        assert chart_factory.format_large_number(100) == "100"
        assert chart_factory.format_large_number(0) == "0"

    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.exists")
    def test_safe_remove_file_success(self, mock_exists, mock_unlink):
        """Test successful file removal."""
        mock_exists.return_value = True

        safe_remove_file("/tmp/test_file.txt")

        mock_exists.assert_called_once_with()
        mock_unlink.assert_called_once_with()

    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.exists")
    def test_safe_remove_file_not_exists(self, mock_exists, mock_unlink):
        """Test file removal when file doesn't exist."""
        mock_exists.return_value = False

        safe_remove_file("/tmp/test_file.txt")

        mock_exists.assert_called_once_with()
        mock_unlink.assert_not_called()

    @patch("pathlib.Path.exists")
    def test_safe_remove_file_empty_path(self, mock_exists):
        """Test file removal with empty path."""
        safe_remove_file("")

        mock_exists.assert_not_called()

    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.exists")
    def test_safe_remove_file_permission_error(self, mock_exists, mock_unlink):
        """Test file removal with permission error."""
        mock_exists.return_value = True
        mock_unlink.side_effect = PermissionError("Permission denied")

        # Should not raise exception
        safe_remove_file("/tmp/test_file.txt")

        mock_exists.assert_called_once_with()
        mock_unlink.assert_called_once_with()


class TestNewHelperFunctions:
    """Test the new helper functions we created during refactoring."""

    def test_command_keyword_decision_logic(self):
        """Test that our refactored command keyword logic works correctly."""
        # This is an integration test to verify our intent recognition improvements
        try:
            generator = GenericKeywordGenerator()

            # Test simple commands use OperatingSystem.Run
            result = generator.operating_system_generator.generate_command_keyword(
                "echo hello"
            )
            assert "Run    echo hello" == result

            result = generator.operating_system_generator.generate_command_keyword(
                "ls -la"
            )
            assert "Run    ls -la" == result

            result = generator.operating_system_generator.generate_command_keyword(
                "pwd"
            )
            assert "Run    pwd" == result

            # Test complex commands use Process.Run Process
            result = generator.operating_system_generator.generate_command_keyword(
                "wget http://example.com"
            )
            assert "Run Process    wget    http://example.com" == result

            result = generator.operating_system_generator.generate_command_keyword(
                "python script.py"
            )
            assert "Run Process    python script.py    shell=True" == result
        except ImportError:
            # Skip this test if importobot is not available
            pytest.skip("importobot package not available")


if __name__ == "__main__":
    pytest.main([__file__])
