"""Unit tests for SSHKeywordTestGenerator."""

import pytest

from importobot.utils.test_generation.ssh_generator import SSHKeywordTestGenerator


class TestSSHLoggingGeneration:
    """Validate SSH logging scenario generation."""

    @pytest.fixture
    def ssh_generator(self) -> SSHKeywordTestGenerator:
        """Provide a reusable SSH keyword generator instance for tests."""
        return SSHKeywordTestGenerator()

    def test_enable_ssh_logging_step_is_returned(self, ssh_generator) -> None:
        """Generator should produce a concrete logging step."""
        test_case = ssh_generator.generate_ssh_keyword_test("Enable Ssh Logging")

        assert test_case["test_case"]["steps"]
        step = test_case["test_case"]["steps"][0]
        assert "Enable SSH" in step["step"]
        assert "logfile" in step["test_data"].lower()
