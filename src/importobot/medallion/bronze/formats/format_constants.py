"""Shared constants for format definitions."""

from typing import Any

# Standard format metadata
FORMAT_METADATA = {
    "version": "1.0",
    "author": "Bronze Layer Format Detection System",
    "created_date": "2025-09-23",
}

# Standard confidence parameters for formats with unique indicators
UNIQUE_INDICATORS_CONFIDENCE: dict[str, int | float] = {
    "confidence_boost_threshold": 0.33,  # Lower threshold due to unique indicators
    "confidence_boost_factor": 0.8,
    "min_score_threshold": 4,
}

# Standard confidence parameters for formats with weak indicators
WEAK_INDICATORS_CONFIDENCE: dict[str, int | float] = {
    "confidence_boost_threshold": 0.5,
    "confidence_boost_factor": 0.6,
    "min_score_threshold": 6,
}


def get_standard_format_kwargs(
    confidence_params: dict[str, int | float],
) -> dict[str, Any]:
    """Get standard format definition kwargs to reduce duplicate code.

    Args:
        confidence_params: Confidence parameters dict

    Returns:
        Dictionary with standard format metadata and confidence parameters
    """
    return {
        # Confidence parameters
        "confidence_boost_threshold": confidence_params["confidence_boost_threshold"],
        "confidence_boost_factor": confidence_params["confidence_boost_factor"],
        "min_score_threshold": int(confidence_params["min_score_threshold"]),
        # Metadata
        "version": FORMAT_METADATA["version"],
        "author": FORMAT_METADATA["author"],
        "created_date": FORMAT_METADATA["created_date"],
    }
