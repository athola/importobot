from __future__ import annotations

from typing import Any

from . import api as api
from . import config as config
from . import exceptions as exceptions
from .core.converter import JsonToRobotConverter as _JsonToRobotConverter
from .exceptions import (
    ConfigurationError as _ConfigurationError,
)
from .exceptions import (
    ConversionError as _ConversionError,
)
from .exceptions import (
    FileAccessError as _FileAccessError,
)
from .exceptions import (
    FileNotFound as _FileNotFound,
)
from .exceptions import (
    ImportobotError as _ImportobotError,
)
from .exceptions import (
    ParseError as _ParseError,
)
from .exceptions import (
    SecurityError as _SecurityError,
)
from .exceptions import (
    SuggestionError as _SuggestionError,
)
from .exceptions import (
    ValidationError as _ValidationError,
)

JsonToRobotConverter: type[_JsonToRobotConverter]
ImportobotError: type[_ImportobotError]
ConfigurationError: type[_ConfigurationError]
ValidationError: type[_ValidationError]
ConversionError: type[_ConversionError]
FileNotFound: type[_FileNotFound]
FileAccessError: type[_FileAccessError]
ParseError: type[_ParseError]
SuggestionError: type[_SuggestionError]
SecurityError: type[_SecurityError]
__version__: str
__all__: list[str]

def convert(payload: dict[str, Any] | str) -> str: ...
def convert_file(input_file: str, output_file: str) -> dict[str, Any]: ...
def convert_directory(input_dir: str, output_dir: str) -> dict[str, Any]: ...
