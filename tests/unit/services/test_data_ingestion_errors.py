"""Error handling tests for DataIngestionService."""

from __future__ import annotations

from unittest.mock import MagicMock

from importobot.medallion.interfaces.enums import ProcessingStatus
from importobot.services.data_ingestion_service import DataIngestionService


def test_ingest_data_dict_returns_failure_when_bronze_errors() -> None:
    """Bronze layer failures should surface as FAILED results without partial state."""
    bronze_layer = MagicMock()
    bronze_layer.ingest.side_effect = RuntimeError("boom")

    service = DataIngestionService(bronze_layer=bronze_layer)

    result = service.ingest_data_dict({"foo": "bar"}, source_name="failing_dict")

    assert result.status == ProcessingStatus.FAILED
    assert result.success_count == 0
    assert result.processed_count == 0
    assert result.error_count == 1
    assert any("boom" in err for err in result.errors)
    bronze_layer.ingest.assert_called_once()


def test_ingest_json_string_invalid_json_reports_failure() -> None:
    """Malformed JSON input should return a FAILED processing result."""
    bronze_layer = MagicMock()
    service = DataIngestionService(bronze_layer=bronze_layer)

    result = service.ingest_json_string("{invalid json", source_name="bad.json")

    assert result.status == ProcessingStatus.FAILED
    assert "Invalid JSON string" in result.errors[0]
    bronze_layer.ingest.assert_not_called()
