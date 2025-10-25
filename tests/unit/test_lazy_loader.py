"""Tests for LazyDataLoader utility following TDD principles."""

import json
from unittest.mock import patch

import pytest

from importobot.utils.lazy_loader import LazyDataLoader


class TestLazyDataLoader:
    """Test LazyDataLoader class following TDD methodology."""

    def test_load_templates_with_existing_file(self, tmp_path):
        """Test loading templates from existing JSON file."""
        LazyDataLoader.load_templates.cache_clear()
        # Arrange
        template_data = {
            "web_automation": {
                "user_authentication": {
                    "description": "Test authentication workflow",
                    "complexity": "high",
                    "steps_count": [6, 12],
                    "templates": ["Step 1", "Step 2"],
                }
            }
        }

        # Create temporary template directory and file
        template_dir = tmp_path / "data" / "templates"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "test_templates.json"
        template_file.write_text(json.dumps(template_data))

        # Mock the path resolution - need to mock the __file__ path construction
        mock_file_path = tmp_path / "utils" / "lazy_loader.py"
        with patch("importobot.utils.lazy_loader.__file__", str(mock_file_path)):
            # Act
            result = LazyDataLoader.load_templates("test_templates")

            # Assert
            assert "web_automation" in result
            assert result["web_automation"] == template_data["web_automation"]
            assert "__precomputed__" in result
            assert "__index__" in result

    def test_load_templates_with_nonexistent_file(self):
        """Test loading templates when file doesn't exist returns empty dict."""
        LazyDataLoader.load_templates.cache_clear()
        # Act
        result = LazyDataLoader.load_templates("nonexistent_template")

        # Assert
        assert "__precomputed__" in result
        assert isinstance(result, dict)

    def test_load_keyword_mappings_with_existing_file(self, tmp_path):
        """Test loading keyword mappings from existing JSON file."""
        LazyDataLoader.load_keyword_mappings.cache_clear()
        # Clear any cached results first

        # Arrange
        mapping_data = {
            "ssh_connect": [
                "SSHLibrary",
                "Open Connection",
            ],  # JSON deserializes as lists
            "ssh_execute": ["SSHLibrary", "Execute Command"],
            "web_navigate": ["SeleniumLibrary", "Go To"],
        }

        # Create the expected directory structure
        keywords_dir = tmp_path / "data" / "keywords"
        keywords_dir.mkdir(parents=True)
        mapping_file = (
            keywords_dir / "ssh_mappings.json"
        )  # Method adds "_mappings" suffix to library_type
        mapping_file.write_text(json.dumps(mapping_data))

        # Mock the path resolution
        mock_file_path = tmp_path / "utils" / "lazy_loader.py"
        with patch("importobot.utils.lazy_loader.__file__", str(mock_file_path)):
            # Act
            result = LazyDataLoader.load_keyword_mappings("ssh")

            # Assert
            assert "ssh_connect" in result
            assert result["ssh_connect"] == ["sshlibrary", "open connection"]
            assert "__reverse_index__" in result
            assert "__precomputed__" in result

    def test_load_keyword_mappings_with_nonexistent_file(self):
        """Test loading keyword mappings when file doesn't exist returns empty dict."""
        LazyDataLoader.load_keyword_mappings.cache_clear()
        # Act
        result = LazyDataLoader.load_keyword_mappings("nonexistent_mappings")

        # Assert
        assert "__precomputed__" in result
        assert isinstance(result, dict)

    def test_caching_behavior_templates(self, tmp_path):
        """Test that templates are cached using LRU cache."""
        LazyDataLoader.load_templates.cache_clear()
        # Arrange
        template_data = {"test": "data"}
        template_dir = tmp_path / "data" / "templates"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "cached_test.json"
        template_file.write_text(json.dumps(template_data))

        mock_file_path = tmp_path / "utils" / "lazy_loader.py"
        with patch("importobot.utils.lazy_loader.__file__", str(mock_file_path)):
            # Act - Load same template multiple times
            result1 = LazyDataLoader.load_templates("cached_test")
            result2 = LazyDataLoader.load_templates("cached_test")

            # Assert - Both results should be identical (cached)
            assert result1 == result2
            assert result1 is result2  # Should be same object due to caching

    def test_caching_behavior_keyword_mappings(self, tmp_path):
        """Test that keyword mappings are cached using LRU cache."""
        LazyDataLoader.load_keyword_mappings.cache_clear()
        # Arrange
        mapping_data = {"test": "mapping"}
        keywords_dir = tmp_path / "data" / "keywords"
        keywords_dir.mkdir(parents=True)
        mapping_file = keywords_dir / "cached_mappings.json"
        mapping_file.write_text(json.dumps(mapping_data))

        mock_file_path = tmp_path / "utils" / "lazy_loader.py"
        with patch("importobot.utils.lazy_loader.__file__", str(mock_file_path)):
            # Act - Load same mappings multiple times
            result1 = LazyDataLoader.load_keyword_mappings("cached_mappings")
            result2 = LazyDataLoader.load_keyword_mappings("cached_mappings")

            # Assert - Both results should be identical (cached)
            assert result1 == result2
            assert result1 is result2  # Should be same object due to caching

    def test_create_summary_comment_empty_structure(self):
        """Test summary comment creation for empty data structure."""
        # Act
        result = LazyDataLoader.create_summary_comment({})

        # Assert
        assert result == "# Empty data structure"

    def test_create_summary_comment_small_structure(self):
        """Test summary comment creation for small data structure."""
        # Arrange
        data = {"key1": "value1", "key2": "value2"}

        # Act
        result = LazyDataLoader.create_summary_comment(data)

        # Assert
        assert "key1, key2" in result
        assert "# Data structure with:" in result
        assert (
            "(2 total items)" not in result
        )  # Should not show count for small structures

    def test_create_summary_comment_large_structure(self):
        """Test summary comment creation for large data structure."""
        # Arrange
        data = {f"key{i}": f"value{i}" for i in range(10)}

        # Act
        result = LazyDataLoader.create_summary_comment(data, max_items=3)

        # Assert
        assert "key0, key1, key2" in result
        assert "(10 total items)" in result
        assert "# Data structure with:" in result

    def test_create_summary_comment_custom_max_items(self):
        """Test summary comment creation with custom max items."""
        # Arrange
        data = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}

        # Act
        result = LazyDataLoader.create_summary_comment(data, max_items=2)

        # Assert
        assert "a, b" in result
        assert "(5 total items)" in result

    def test_json_file_encoding_utf8(self, tmp_path):
        """Test that JSON files are read with UTF-8 encoding."""
        # Arrange
        template_data = {"unicode_test": "测试数据"}
        template_dir = tmp_path / "data" / "templates"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "unicode_test.json"
        template_file.write_text(
            json.dumps(template_data, ensure_ascii=False), encoding="utf-8"
        )

        mock_file_path = tmp_path / "utils" / "lazy_loader.py"
        with patch("importobot.utils.lazy_loader.__file__", str(mock_file_path)):
            # Act
            LazyDataLoader.load_templates.cache_clear()
            result = LazyDataLoader.load_templates("unicode_test")

            # Assert
            assert result["unicode_test"] == "测试数据"
            assert "__precomputed__" in result

    def test_file_path_construction(self):
        """Test that file paths are constructed correctly."""
        # This test verifies the path construction logic
        with patch("importobot.utils.lazy_loader.Path") as mock_path:
            mock_file = (
                mock_path.return_value.parent.parent
                / "data"
                / "templates"
                / "test.json"
            )
            mock_file.exists.return_value = False

            # Act
            LazyDataLoader.load_templates.cache_clear()
            result = LazyDataLoader.load_templates("test")

            # Assert
            assert "__precomputed__" in result
            mock_path.assert_called()

    def test_json_parsing_error_handling(self, tmp_path):
        """Test handling of malformed JSON files."""
        # Arrange
        template_dir = tmp_path / "data" / "templates"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "malformed.json"
        template_file.write_text("{ invalid json")

        with patch("importobot.utils.lazy_loader.Path") as mock_path:
            mock_path.return_value.parent.parent = tmp_path

            # Act & Assert
            with pytest.raises(json.JSONDecodeError):
                LazyDataLoader.load_templates("malformed")
