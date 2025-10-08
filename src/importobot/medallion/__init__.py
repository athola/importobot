"""Medallion architecture implementation for Importobot.

This package implements the Databricks Medallion architecture pattern with
Bronze (raw), Silver (curated), and Gold (consumption-ready) data layers
for enhanced data quality, auditability, and scalable processing.

The medallion architecture provides:
- Progressive data quality improvement across layers
- Complete data lineage and audit trails
- Scalable processing with parallelization capabilities
- Separation of concerns with clear layer responsibilities
"""

from importobot.medallion.bronze_layer import BronzeLayer
from importobot.medallion.gold_layer import GoldLayer
from importobot.medallion.interfaces.base_interfaces import DataLayer
from importobot.medallion.interfaces.data_models import (
    DataQualityMetrics,
    LayerMetadata,
    LineageInfo,
    ProcessingResult,
)
from importobot.medallion.silver_layer import SilverLayer
from importobot.utils.validation_models import ValidationResult

__all__ = [
    "BronzeLayer",
    "SilverLayer",
    "GoldLayer",
    "DataLayer",
    "LayerMetadata",
    "DataQualityMetrics",
    "ProcessingResult",
    "ValidationResult",
    "LineageInfo",
]
