"""Tests for SSH keyword JSON data coverage and validation."""

import json
from pathlib import Path

import pytest

from importobot.core.keyword_loader import KeywordLibraryLoader
from tests.shared_ssh_test_data import (
    ALL_SSH_KEYWORDS,
    SSH_COMMAND_KEYWORDS,
    SSH_CONNECTION_KEYWORDS,
    SSH_DIRECTORY_KEYWORDS,
    SSH_FILE_KEYWORDS,
    get_basic_ssh_connection_keywords,
)


@pytest.fixture
def ssh_keywords_data():
    """Load SSH keywords JSON data."""
    # Use direct path to ssh.json
    ssh_json_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "importobot"
        / "data"
        / "keywords"
        / "ssh.json"
    )
    with open(ssh_json_path, encoding="utf-8") as f:
        return json.load(f)


class TestSSHKeywordsStructure:
    """Tests for SSH keywords JSON basic structure and metadata."""

    def test_ssh_json_structure(self, ssh_keywords_data):
        """Test that SSH JSON has correct top-level structure."""
        assert "library_name" in ssh_keywords_data
        assert "description" in ssh_keywords_data
        assert "keywords" in ssh_keywords_data
        assert ssh_keywords_data["library_name"] == "SSHLibrary"
        assert isinstance(ssh_keywords_data["keywords"], dict)

    def test_ssh_library_description(self, ssh_keywords_data):
        """Test that SSH library has appropriate description."""
        assert (
            ssh_keywords_data["description"]
            == "SSH operations and remote command execution"
        )

    def test_ssh_keyword_count(self, ssh_keywords_data):
        """Test that SSH keywords JSON contains comprehensive keyword coverage."""
        keywords = ssh_keywords_data["keywords"]
        assert (
            len(keywords) >= 40
        )  # Should have at least 40 keywords from comprehensive coverage

    def test_keyword_descriptions_non_empty(self, ssh_keywords_data):
        """Test that all keywords have non-empty descriptions."""
        keywords = ssh_keywords_data["keywords"]

        for keyword_name, keyword_data in keywords.items():
            assert "description" in keyword_data
            assert keyword_data["description"], (
                f"Empty description for keyword: {keyword_name}"
            )
            assert len(keyword_data["description"]) > 10, (
                f"Description too short for keyword: {keyword_name}"
            )

    def test_keyword_args_structure(self, ssh_keywords_data):
        """Test that keyword arguments follow consistent structure."""
        keywords = ssh_keywords_data["keywords"]

        for keyword_name, keyword_data in keywords.items():
            assert "args" in keyword_data
            assert isinstance(keyword_data["args"], list), (
                f"Args should be a list for keyword: {keyword_name}"
            )

    def test_all_keywords_have_valid_json_structure(self, ssh_keywords_data):
        """Test that all keywords have valid JSON structure without syntax errors."""
        keywords = ssh_keywords_data["keywords"]

        for keyword_name, keyword_data in keywords.items():
            # Test that keyword data can be serialized back to JSON
            try:
                json.dumps(keyword_data)
            except (TypeError, ValueError) as e:
                pytest.fail(f"Keyword {keyword_name} has invalid JSON structure: {e}")


class TestSSHKeywordsCoverage:
    """Tests for SSH keyword coverage and presence."""

    def test_connection_management_keywords(self, ssh_keywords_data):
        """Test that all connection management keywords are present."""
        keywords = ssh_keywords_data["keywords"]

        connection_keywords = SSH_CONNECTION_KEYWORDS

        for keyword in connection_keywords:
            assert keyword in keywords, f"Missing connection keyword: {keyword}"
            assert "description" in keywords[keyword]
            assert "args" in keywords[keyword]

    def test_authentication_keywords(self, ssh_keywords_data):
        """Test that all authentication keywords are present."""
        keywords = ssh_keywords_data["keywords"]

        auth_keywords = ["Login", "Login With Public Key"]

        for keyword in auth_keywords:
            assert keyword in keywords, f"Missing authentication keyword: {keyword}"
            assert "description" in keywords[keyword]
            assert "args" in keywords[keyword]

    def test_command_execution_keywords(self, ssh_keywords_data):
        """Test that all command execution keywords are present."""
        keywords = ssh_keywords_data["keywords"]

        command_keywords = ["Execute Command", "Start Command", "Read Command Output"]

        for keyword in command_keywords:
            assert keyword in keywords, f"Missing command execution keyword: {keyword}"
            assert "description" in keywords[keyword]
            assert "args" in keywords[keyword]

    def test_file_operation_keywords(self, ssh_keywords_data):
        """Test that all file operation keywords are present."""
        keywords = ssh_keywords_data["keywords"]

        file_keywords = SSH_FILE_KEYWORDS

        for keyword in file_keywords:
            assert keyword in keywords, f"Missing file operation keyword: {keyword}"
            assert "description" in keywords[keyword]
            assert "args" in keywords[keyword]

    def test_directory_operation_keywords(self, ssh_keywords_data):
        """Test that all directory operation keywords are present."""
        keywords = ssh_keywords_data["keywords"]

        directory_keywords = SSH_DIRECTORY_KEYWORDS

        for keyword in directory_keywords:
            assert keyword in keywords, (
                f"Missing directory operation keyword: {keyword}"
            )
            assert "description" in keywords[keyword]
            assert "args" in keywords[keyword]

    def test_file_verification_keywords(self, ssh_keywords_data):
        """Test that all file/directory verification keywords are present."""
        keywords = ssh_keywords_data["keywords"]

        verification_keywords = [
            "File Should Exist",
            "File Should Not Exist",
            "Directory Should Exist",
            "Directory Should Not Exist",
        ]

        for keyword in verification_keywords:
            assert keyword in keywords, f"Missing verification keyword: {keyword}"
            assert "description" in keywords[keyword]
            assert "args" in keywords[keyword]

    def test_interactive_shell_keywords(self, ssh_keywords_data):
        """Test that all interactive shell keywords are present."""
        keywords = ssh_keywords_data["keywords"]

        shell_keywords = SSH_COMMAND_KEYWORDS

        for keyword in shell_keywords:
            assert keyword in keywords, f"Missing shell keyword: {keyword}"
            assert "description" in keywords[keyword]
            assert "args" in keywords[keyword]

    def test_configuration_keywords(self, ssh_keywords_data):
        """Test that configuration keywords are present."""
        keywords = ssh_keywords_data["keywords"]

        config_keywords = ["Set Default Configuration", "Set Client Configuration"]

        for keyword in config_keywords:
            assert keyword in keywords, f"Missing configuration keyword: {keyword}"
            assert "description" in keywords[keyword]
            assert "args" in keywords[keyword]

    def test_logging_keywords(self, ssh_keywords_data):
        """Test that logging keywords are present."""
        keywords = ssh_keywords_data["keywords"]

        logging_keywords = ["Enable Ssh Logging", "Disable Ssh Logging"]

        for keyword in logging_keywords:
            assert keyword in keywords, f"Missing logging keyword: {keyword}"
            assert "description" in keywords[keyword]
            assert "args" in keywords[keyword]

    def test_comprehensive_coverage_vs_documentation(self, ssh_keywords_data):
        """Test that we have good coverage of documented SSHLibrary keywords."""
        keywords = ssh_keywords_data["keywords"]

        # Based on the comprehensive SSHLibrary documentation review
        documented_keywords = ALL_SSH_KEYWORDS

        # Check that we have coverage for all documented keywords
        missing_keywords = []
        for doc_keyword in documented_keywords:
            if doc_keyword not in keywords:
                missing_keywords.append(doc_keyword)

        assert not missing_keywords, f"Missing documented keywords: {missing_keywords}"

        # We should have at least 90% coverage of documented keywords
        coverage_ratio = len([k for k in documented_keywords if k in keywords]) / len(
            documented_keywords
        )
        assert coverage_ratio >= 0.9, (
            f"Coverage ratio {coverage_ratio:.2%} is below 90%"
        )


class TestSSHKeywordsValidation:
    """Tests for SSH keyword validation and argument specification."""

    def test_open_connection_comprehensive_args(self, ssh_keywords_data):
        """Test that Open Connection keyword has comprehensive argument list."""
        keywords = ssh_keywords_data["keywords"]
        open_connection = keywords["Open Connection"]

        expected_args = [
            "host",
            "port=22",
            "alias=None",
            "timeout=3s",
            "newline=LF",
            "prompt=None",
            "term_type=vt100",
            "width=80",
            "height=24",
            "path_separator=/",
            "encoding=UTF-8",
        ]

        assert open_connection["args"] == expected_args

    def test_execute_command_comprehensive_args(self, ssh_keywords_data):
        """Test that Execute Command keyword has comprehensive argument list."""
        keywords = ssh_keywords_data["keywords"]
        execute_command = keywords["Execute Command"]

        expected_args = [
            "command",
            "return_stdout=True",
            "return_stderr=False",
            "return_rc=False",
            "sudo=False",
            "sudo_password=None",
        ]

        assert execute_command["args"] == expected_args

    def test_keyword_loader_can_load_ssh_keywords(self):
        """Test that KeywordLibraryLoader can successfully load SSH keywords."""
        loader = KeywordLibraryLoader()
        ssh_keywords = loader.load_library("ssh")

        assert ssh_keywords is not None
        assert "keywords" in ssh_keywords
        assert len(ssh_keywords["keywords"]) >= 40


class TestSSHKeywordsSecurity:
    """Tests for SSH keyword security warnings and notes."""

    def test_security_warnings_present(self, ssh_keywords_data):
        """Test that security warnings are present for appropriate keywords."""
        keywords = ssh_keywords_data["keywords"]

        # Keywords that should have security warnings
        security_warning_keywords = get_basic_ssh_connection_keywords()

        for keyword in security_warning_keywords:
            assert keyword in keywords
            assert "security_warning" in keywords[keyword], (
                f"Missing security warning for: {keyword}"
            )
            assert keywords[keyword]["security_warning"].startswith("⚠️"), (
                f"Security warning should start with warning emoji for: {keyword}"
            )

    def test_security_notes_present(self, ssh_keywords_data):
        """Test that security notes are present for secure keywords."""
        keywords = ssh_keywords_data["keywords"]

        # Keywords that should have security notes
        security_note_keywords = ["Login With Public Key"]

        for keyword in security_note_keywords:
            assert keyword in keywords
            assert "security_note" in keywords[keyword], (
                f"Missing security note for: {keyword}"
            )
            assert keywords[keyword]["security_note"].startswith("✅"), (
                f"Security note should start with check emoji for: {keyword}"
            )
