"""Internal service implementations.

The classes in this package power Importobot's own workflows and are **not**
part of the public API surface. Import stability is only guaranteed through
`importobot.JsonToRobotConverter` and the modules under `importobot.api`.
"""

from typing import NoReturn

__all__: list[str] = []


def __getattr__(name: str) -> NoReturn:
    """Prevent accidental access to internal service modules via attribute lookup."""
    raise ModuleNotFoundError(
        "importobot.services is internal and not part of the public API. "
        "Import concrete modules directly or use importobot.api.* helpers."
    )
