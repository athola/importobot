"""Test category management and enumeration."""

from enum import Enum
from pathlib import Path

from typing_extensions import TypedDict


class CategoryInfo(TypedDict):
    """TypedDict for category information."""

    dir: Path
    count: int


class CategoryEnum(Enum):
    """Enumeration of supported test categories for distribution weights."""

    REGRESSION = "regression"
    SMOKE = "smoke"
    INTEGRATION = "integration"
    E2E = "e2e"

    @classmethod
    def get_default_weights(cls) -> dict["CategoryEnum", float]:
        """Get default distribution weights."""
        return {
            cls.REGRESSION: 0.3125,  # 31.25%
            cls.SMOKE: 0.1875,  # 18.75%
            cls.INTEGRATION: 0.25,  # 25%
            cls.E2E: 0.25,  # 25%
        }

    @classmethod
    def from_string(cls, category_str: str) -> "CategoryEnum":
        """Convert string to CategoryEnum enum."""
        for category in cls:
            if category.value == category_str:
                return category
        raise ValueError(f"Unknown category: {category_str}")

    @classmethod
    def get_all_values(cls) -> list[str]:
        """Get all category values as strings."""
        return [category.value for category in cls]
