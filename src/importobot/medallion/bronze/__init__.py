"""Bronze layer implementation for raw data ingestion.

The Bronze layer is the first layer in the Medallion architecture, responsible for:
- Raw data ingestion with minimal processing
- Format detection and basic validation
- Metadata capture and audit trail creation
- Immutable storage with versioning
"""

from importobot.medallion.bronze.format_detector import FormatDetector
from importobot.medallion.bronze.raw_data_processor import RawDataProcessor
from importobot.medallion.bronze.validation import BronzeValidator

__all__ = [
    "BronzeValidator",
    "FormatDetector",
    "RawDataProcessor",
]
