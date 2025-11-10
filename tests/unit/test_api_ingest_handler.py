"""Tests for API ingestion CLI handler."""

from argparse import Namespace
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

from importobot.cli.handlers import handle_api_ingest
from importobot.config import APIIngestConfig
from importobot.medallion.interfaces.enums import SupportedFormat


class DummyClient:
    """Simple client that yields predefined payloads."""

    def __init__(self, payloads: Iterable[dict[str, object]]) -> None:
        self._payloads = list(payloads)
        self.calls: list[dict[str, object]] = []

    def fetch_all(self, progress_cb: Any) -> Iterable[dict[str, object]]:
        for payload in self._payloads:
            items = payload.get("items", [])
            progress_cb(
                items=len(items) if isinstance(items, list) else 0,
                total=payload.get("total"),
                page=payload.get("page"),
            )
            yield payload


def make_args(**overrides: object) -> Namespace:
    """Create CLI namespace with defaults suitable for ingestion tests."""
    defaults: dict[str, object] = {
        "fetch_format": SupportedFormat.JIRA_XRAY,
        "api_url": "https://jira.example/rest",
        "api_tokens": ["token"],
        "api_user": "jira-user",
        "project": "JIRA",
        "input_dir": None,
        "max_concurrency": None,
        "insecure": False,
        "output": None,
        "files": None,
        "directory": None,
        "input": None,
        "output_file": None,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


@pytest.fixture
def fake_config(monkeypatch: pytest.MonkeyPatch) -> APIIngestConfig:
    """Provide a configuration fixture and patch resolver to return it."""
    config = APIIngestConfig(
        fetch_format=SupportedFormat.JIRA_XRAY,
        api_url="https://jira.example/rest",
        tokens=["token"],
        user="jira-user",
        project_name="JIRA",
        project_id=None,
        output_dir=Path.cwd(),
        max_concurrency=None,
        insecure=False,
    )

    monkeypatch.setattr(
        "importobot.cli.handlers.resolve_api_ingest_config", lambda args: config
    )
    return config


def test_handle_api_ingest_writes_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Handler should stream payloads to a single JSON file."""
    payloads = [
        {"items": [{"id": 1}], "page": 1, "total": 2},
        {"items": [{"id": 2}], "page": 2, "total": 2},
    ]
    client = DummyClient(payloads)
    monkeypatch.setattr(
        "importobot.cli.handlers.get_api_client",
        lambda fmt, **kwargs: client,
    )

    args = make_args(input_dir=str(tmp_path / "downloads"))

    saved_path = handle_api_ingest(args)

    assert saved_path.startswith(str(tmp_path))
    path = Path(saved_path)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert '"id": 1' in content
    assert '"id": 2' in content

    meta_path = path.with_suffix(".meta.json")
    assert meta_path.exists()
    metadata = meta_path.read_text(encoding="utf-8")
    assert '"project_name": "JIRA"' in metadata


def test_handler_provides_progress_feedback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Progress callback should be invoked for each page."""
    calls: list[dict[str, object]] = []

    class TrackingClient(DummyClient):
        """A client that tracks API calls for testing purposes."""

        def fetch_all(self, progress_cb: Any) -> Iterable[dict[str, object]]:
            for payload in super().fetch_all(progress_cb):
                calls.append(payload)
                yield payload

    payloads = [
        {"items": [{"id": "A"}], "page": 1, "total": 3},
        {"items": [{"id": "B"}], "page": 2, "total": 3},
        {"items": [{"id": "C"}], "page": 3, "total": 3},
    ]

    monkeypatch.setattr(
        "importobot.cli.handlers.resolve_api_ingest_config",
        lambda args: APIIngestConfig(
            fetch_format=args.fetch_format,
            api_url=args.api_url,
            tokens=args.api_tokens,
            user=args.api_user,
            project_name=args.project if isinstance(args.project, str) else None,
            project_id=None,
            output_dir=tmp_path,
            max_concurrency=None,
            insecure=False,
        ),
    )

    monkeypatch.setattr(
        "importobot.cli.handlers.get_api_client",
        lambda fmt, **kwargs: TrackingClient(payloads),
    )

    args = make_args(input_dir=str(tmp_path))

    handle_api_ingest(args)

    assert len(calls) == 3


def test_handle_api_ingest_returns_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Handler should return saved path and attach it to args for downstream use."""
    payloads: list[dict[str, object]] = [{"items": []}]
    client = DummyClient(payloads)
    monkeypatch.setattr(
        "importobot.cli.handlers.resolve_api_ingest_config",
        lambda args: APIIngestConfig(
            fetch_format=args.fetch_format,
            api_url=args.api_url,
            tokens=args.api_tokens,
            user=args.api_user,
            project_name=None,
            project_id=None,
            output_dir=tmp_path,
            max_concurrency=None,
            insecure=False,
        ),
    )
    monkeypatch.setattr(
        "importobot.cli.handlers.get_api_client",
        lambda fmt, **kwargs: client,
    )

    args = make_args()
    path = handle_api_ingest(args)

    assert args.input == path
    assert Path(path).exists()
