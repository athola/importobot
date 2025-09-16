"""Unit tests for multi-line comment formatting functionality."""

from importobot.core.keywords import GenericKeywordGenerator


class TestMultiLineCommentFormatting:
    """Tests for multi-line comment formatting functionality."""

    def test_short_comment_not_split(self):
        """Test that short comments are not split."""
        generator = GenericKeywordGenerator()

        short_test_data = "Short test data"
        # pylint: disable=protected-access
        result = generator._format_test_data_comment(short_test_data)

        # Should be a single line comment
        assert len(result) == 1
        assert result[0] == f"    # Test Data: {short_test_data}"

    def test_comment_split_at_comma(self):
        """Test that comments are split at commas when possible."""
        generator = GenericKeywordGenerator()

        long_test_data = (
            "Very long test data string that exceeds the normal limit, "
            "with comma used for splitting"
        )
        # pylint: disable=protected-access
        result = generator._format_test_data_comment(long_test_data)

        # Should be split into two lines
        assert len(result) == 2
        assert result[0].startswith("    # Test Data:")
        assert result[1].startswith("    # Test Data (cont.):")
        # The split happens at the comma, so the second part should start with
        # "with a comma"
        assert result[1].endswith("with comma used for splitting")

    def test_comment_split_at_semicolon(self):
        """Test that comments are split at semicolons when commas not available."""
        generator = GenericKeywordGenerator()

        long_test_data = (
            "This is a very long test data string; with a semicolon that "
            "should be used for splitting"
        )
        # pylint: disable=protected-access
        result = generator._format_test_data_comment(long_test_data)

        # Should be split into two lines
        assert len(result) == 2
        assert result[0].startswith("    # Test Data:")
        assert result[1].startswith("    # Test Data (cont.):")
        # The split happens at the semicolon, so the second part should start
        # with "with a semicolon"
        assert result[1].endswith("with a semicolon that should be used for splitting")

    def test_comment_split_at_space(self):
        """Test that comments are split at spaces when no commas or semicolons."""
        generator = GenericKeywordGenerator()

        # Create a test data string that's long enough to trigger splitting
        long_test_data = "A" * 80 + " B" * 20  # This should be > 88 chars
        # pylint: disable=protected-access
        result = generator._format_test_data_comment(long_test_data)

        # Should be split into two lines
        assert len(result) == 2
        assert result[0].startswith("    # Test Data:")
        assert result[1].startswith("    # Test Data (cont.):")

    def test_extremely_long_comment_fallback(self):
        """Test fallback behavior for extremely long comments without natural
        split points."""
        generator = GenericKeywordGenerator()

        # Create a very long string without good split points
        long_test_data = "x" * 200  # 200 character string of x's
        # pylint: disable=protected-access
        result = generator._format_test_data_comment(long_test_data)

        # Should be split into two lines using fallback method
        assert len(result) == 2
        assert result[0].startswith("    # Test Data:")
        assert result[1].startswith("    # Test Data (cont.):")

    def test_comment_with_step_keywords(self):
        """Test that multi-line comments work correctly in step keyword generation."""
        generator = GenericKeywordGenerator()

        # Create test data that's definitely long enough to trigger splitting
        step_data = {
            "step": "Do something",
            "testData": (
                "This is a very long test data string that will definitely "
                "exceed the 88 character limit and cause splitting into "
                "multiple lines for sure"
            ),
            "expectedResult": "Something happens",
        }

        result = generator.generate_step_keywords(step_data)

        # Should contain comment lines
        comment_lines = [line for line in result if "# Test Data:" in line]
        assert len(comment_lines) >= 1
        assert any("Test Data:" in line for line in comment_lines)
