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
    # Records
    "BronzeRecord",
    # Abstract interfaces
    "DataLayer",
    # Data models
    "DataLineage",
    # Enums
    "DataQuality",
    "DataQualityMetrics",
    "FormatDetectionResult",
    "LayerData",
    "LayerMetadata",
    "LayerQuery",
    "LineageInfo",
    "ProcessingResult",
    "ProcessingStatus",
    "RecordMetadata",
    "StorageBackend",
    "SupportedFormat",
]
