"""Public converter interfaces for enterprise integration.

This module exposes the core conversion functionality needed for
bulk JSON to Robot Framework conversion in enterprise pipelines.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importobot.core.converter import JsonToRobotConverter
    from importobot.core.engine import GenericConversionEngine
else:
    # Import at runtime to avoid circular imports
    from importobot.core.converter import JsonToRobotConverter
    from importobot.core.engine import GenericConversionEngine

__all__ = ["JsonToRobotConverter", "GenericConversionEngine"]
