"""Central services for Importobot architecture.

This package consolidates core business services to reduce coupling
and improve maintainability as identified in the staff engineering review.
"""

# Import only services that don't cause circular imports
from .optimization_service import OptimizationService
from .performance_cache import PerformanceCache, cached_json_dumps, cached_string_lower
from .security_gateway import SecurityError, SecurityGateway
from .security_types import SecurityLevel
from .validation_service import ValidationService

# Note: FormatDetectionService, DataIngestionService, MetadataService, and
# QualityAssessmentService are excluded from __init__.py to break circular imports.
# Import them directly from their modules when needed.

__all__ = [
    "ValidationService",
    "PerformanceCache",
    "OptimizationService",
    "SecurityGateway",
    "SecurityError",
    "SecurityLevel",
    "cached_string_lower",
    "cached_json_dumps",
]
