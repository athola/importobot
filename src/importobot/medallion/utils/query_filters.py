"""Shared query filtering utilities for medallion layers."""

from importobot.medallion.interfaces.data_models import LayerMetadata, LayerQuery


def matches_query_filters(
    data_id: str, metadata: LayerMetadata, query: LayerQuery
) -> bool:
    """Check if data matches query filters.

    Args:
        data_id: Identifier for the data
        metadata: Data metadata to check
        query: Query with filter criteria

    Returns:
        True if data matches all query filters
    """
    # Apply ID filter
    if query.data_ids and data_id not in query.data_ids:
        return False

    # Apply format type filter
    if query.format_types and metadata.format_type not in query.format_types:
        return False

    # Apply date range filter
    if query.date_range:
        start_date, end_date = query.date_range
        if not start_date <= metadata.ingestion_timestamp <= end_date:
            return False

    return True
