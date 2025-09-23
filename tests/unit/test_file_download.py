"""Unit tests for file download functionality."""

from importobot.core.keyword_generator import GenericKeywordGenerator


class TestFileDownloadFunctionality:
    """Tests for file download functionality."""

    def test_curl_command_conversion(self):
        """Test conversion of curl commands to Run Process keywords."""
        generator = GenericKeywordGenerator()

        step_data = {
            "step": "Initiate file download",
            "testData": "Command: curl -o /tmp/downloaded_file.txt "
            + "https://example.com/remote.txt",
            "expectedResult": "File download initiated successfully",
        }

        result = generator.generate_step_keywords(step_data)

        # Should generate a Run Process keyword for curl command
        assert any("Run Process" in line and "curl" in line for line in result)
        assert any("curl" in line and "-o" in line for line in result)
        assert any("/tmp/downloaded_file.txt" in line for line in result)

    def test_wget_command_conversion(self):
        """Test conversion of wget commands to Run Process keywords."""
        generator = GenericKeywordGenerator()

        step_data = {
            "step": "Execute wget command",
            "testData": "Command: wget -O /tmp/file.txt https://example.com/file.txt",
            "expectedResult": "File downloaded successfully",
        }

        result = generator.generate_step_keywords(step_data)

        # Should generate a Run Process keyword for wget command
        assert any("Run Process" in line and "wget" in line for line in result)
        assert any("wget" in line and "-O" in line for line in result)
        assert any("/tmp/file.txt" in line for line in result)

    def test_generic_command_execution(self):
        """Test conversion of generic commands to Run keywords."""
        generator = GenericKeywordGenerator()

        step_data = {
            "step": "Execute command",
            "testData": "echo 'Hello World'",
            "expectedResult": "Command executed successfully",
        }

        result = generator.generate_step_keywords(step_data)

        # Should generate a Run keyword for echo command (OperatingSystem library)
        assert any("Run" in line and "echo" in line for line in result)
        assert any("Hello World" in line for line in result)

    def test_file_transfer_keyword(self):
        """Test generation of file transfer keywords."""
        generator = GenericKeywordGenerator()

        step_data = {
            "step": "Retrieve the specified file from the remote host",
            "testData": "Remote File Path: /remote/file.txt, "
            + "Local Destination Path: /local/file.txt",
            "expectedResult": "File successfully downloaded",
        }

        result = generator.generate_step_keywords(step_data)

        # Should generate appropriate file transfer keyword
        # Check what keywords are actually generated
        contains_file_keyword = any("File" in line for line in result)
        assert contains_file_keyword, f"No file keyword found in: {result}"

        # Check for file paths
        assert any("/remote/file.txt" in line for line in result)
        assert any("/local/file.txt" in line for line in result)

    def test_file_exists_verification(self):
        """Test generation of file existence verification keywords."""
        generator = GenericKeywordGenerator()

        step_data = {
            "step": "Verify the downloaded file exists",
            "testData": "Check for file existence at /tmp/downloaded_file.txt",
            "expectedResult": "The file is present",
        }

        result = generator.generate_step_keywords(step_data)

        # Should generate a File Should Exist keyword
        assert any("File Should Exist" in line for line in result)
        assert any("/tmp/downloaded_file.txt" in line for line in result)

    def test_file_removal(self):
        """Test generation of file removal keywords."""
        generator = GenericKeywordGenerator()

        step_data = {
            "step": "Clean up the downloaded file",
            "testData": "Command: rm /tmp/downloaded_file.txt",
            "expectedResult": "File is successfully removed",
        }

        result = generator.generate_step_keywords(step_data)

        # Should generate a Remove File keyword
        assert any("Remove File" in line for line in result)
        assert any("/tmp/downloaded_file.txt" in line for line in result)
