"""Core interfaces for Medallion architecture."""

# Enums
# Abstract interfaces
from .base_interfaces import (
    DataLayer,
    StorageBackend,
)

# Data models
from .data_models import (
    DataLineage,
    DataQualityMetrics,
    FormatDetectionResult,
    LayerData,
    LayerMetadata,
    LayerQuery,
    LineageInfo,
    ProcessingResult,
)
from .enums import (
    DataQuality,
    ProcessingStatus,
    SupportedFormat,
)

# Records
from .records import (
    BronzeRecord,
    RecordMetadata,
)

__all__ = [
    # Enums
    "DataQuality",
    "ProcessingStatus",
    "SupportedFormat",
    # Data models
    "DataLineage",
    "DataQualityMetrics",
    "FormatDetectionResult",
    "LayerData",
    "LayerMetadata",
    "LayerQuery",
    "LineageInfo",
    "ProcessingResult",
    # Records
    "BronzeRecord",
    "RecordMetadata",
    # Abstract interfaces
    "DataLayer",
    "StorageBackend",
]
