"""Secret detection utilities for test data generation."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SecretFinding:
    """Represents a potential secret discovered during scanning."""

    secret_type: str
    preview: str


class SecretsDetector:
    """Detect potential secrets in test data payloads."""

    SECRET_PATTERNS: Sequence[tuple[str, str]] = (
        (
            r'(?i)(api[_-]?key|apikey)[\s:="\']+([A-Za-z0-9_\-]{20,})',
            "API Key",
        ),
        (
            r'(?i)(aws[_-]?access[_-]?key[_-]?id)[\s:="\']+([A-Z0-9]{20})',
            "AWS Access Key",
        ),
        (
            r'(?i)(aws[_-]?secret[_-]?access[_-]?key)[\s:="\']+'
            r"([A-Za-z0-9/+=]{40})",
            "AWS Secret",
        ),
        (
            r'(?i)(password|passwd|pwd)[\s:="\']+([^\s"\']{8,})',
            "Password",
        ),
        (r"-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----", "Private Key"),
        (r"(?i)bearer\s+[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+", "JWT Token"),
    )

    def scan(self, data: Any) -> list[SecretFinding]:
        """Scan arbitrary data for potential secrets."""
        corpus = self._flatten_to_strings(data)
        findings: list[SecretFinding] = []
        for text in corpus:
            for pattern, secret_type in self.SECRET_PATTERNS:
                for match in re.finditer(pattern, text):
                    preview = match.group(0)
                    if len(preview) > 20:
                        preview = preview[:20] + "..."
                    findings.append(
                        SecretFinding(secret_type=secret_type, preview=preview)
                    )
        return findings

    def _flatten_to_strings(self, data: Any) -> Iterable[str]:
        """Flatten nested data to a sequence of strings for scanning."""
        if isinstance(data, str):
            yield data
        elif isinstance(data, bytes):  # pragma: no cover - defensive path
            yield data.decode("utf-8", errors="ignore")
        elif isinstance(data, dict):
            for key, value in data.items():
                yield from self._flatten_to_strings(str(key))
                yield from self._flatten_to_strings(value)
        elif isinstance(data, list | tuple | set):
            for item in data:
                yield from self._flatten_to_strings(item)
        else:
            yield str(data)
