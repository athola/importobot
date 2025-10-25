"""Medallion architecture internals.

The Bronze/Silver/Gold layers are implementation details that power Importobot's
own ingestion pipelines. They are intentionally **not** part of the public API
surface and may change without notice.
"""

from typing import NoReturn

__all__: list[str] = []


def __getattr__(name: str) -> NoReturn:
    """Guard against accidental use of medallion layers from the public API."""
    raise ModuleNotFoundError(
        "importobot.medallion is internal and not covered by the stability guarantee."
    )
