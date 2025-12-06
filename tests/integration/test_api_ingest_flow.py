"""Integration-style tests for API ingestion feeding conversion."""

import json
from argparse import Namespace
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import pytest

from importobot.cli.handlers import handle_api_ingest, handle_positional_args
from importobot.cli.parser import create_parser
from importobot.config import APIIngestConfig
from importobot.medallion.interfaces.enums import SupportedFormat

SAMPLE_TOKEN = "alpha-access-hash-1234"


class DummyClient:
    """Simple client streaming predefined payloads."""

    def __init__(self, payloads: Iterable[dict[str, object]]) -> None:
        self.payloads = list(payloads)

    def fetch_all(self, progress_cb: Callable[..., None]) -> Iterable[dict[str, Any]]:
        """Yield payloads while emitting progress callbacks."""
        for payload in self.payloads:
            items = payload.get("items", [])
            progress_cb(
                items=len(items) if isinstance(items, list) else 0,
                total=None,
                page=None,
            )
            yield payload


def make_args(tmp_path: Path) -> Namespace:
    """Construct CLI args namespace for integration tests."""
    return Namespace(
        fetch_format=SupportedFormat.TESTRAIL,
        api_url="https://testrail.example/api/v2/get_runs/1",
        api_tokens=[SAMPLE_TOKEN],
        api_user="testrail-user",
        project="TR",
        input_dir=str(tmp_path),
        max_concurrency=None,
        insecure=False,
        no_suggestions=True,
        apply_suggestions=False,
        files=None,
        directory=None,
        output=None,
        output_file=str(tmp_path / "suite.robot"),
        input=None,
    )


def test_ingestion_then_conversion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Fetched payload should feed into existing conversion flow."""
    payloads: list[dict[str, object]] = [{"items": [{"id": 1}]}]
    monkeypatch.setattr(
        "importobot.cli.handlers.resolve_api_ingest_config",
        lambda args: APIIngestConfig(
            fetch_format=args.fetch_format,
            api_url=args.api_url,
            tokens=args.api_tokens,
            user=args.api_user,
            project_name=args.project,
            project_id=None,
            output_dir=Path(args.input_dir),
            max_concurrency=None,
            insecure=False,
        ),
    )
    monkeypatch.setattr(
        "importobot.cli.handlers.get_api_client",
        lambda fmt, **kwargs: DummyClient(payloads),
    )

    converted_inputs: list[str] = []
    monkeypatch.setattr(
        "importobot.cli.handlers.convert_file",
        lambda input_file, output_file: converted_inputs.append(input_file),
    )

    args = make_args(tmp_path)

    saved_path = handle_api_ingest(args)
    parser = create_parser()
    handle_positional_args(args, parser=parser)

    assert converted_inputs == [saved_path]
    assert Path(saved_path).exists()


def test_ingest_metadata_tracks_payloads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Metadata file reflects payload counts with multi-stage progress callbacks."""

    class MultiStageClient:
        """Client that emits key discovery and detail fetch progress events."""

        def fetch_all(
            self, progress_cb: Callable[..., None]
        ) -> Iterable[dict[str, Any]]:
            """Fetch all test items with progress callback."""
            progress_cb(items=0, total=None, page=None)
            payload = {
                "results": [{"id": 1}, {"id": 2}],
                "total": 2,
            }
            progress_cb(items=2, total=2, page=1)
            yield payload

    project_name = "Project-Alpha"
    output_dir = tmp_path / "downloads"
    output_dir.mkdir()

    monkeypatch.setattr(
        "importobot.cli.handlers.resolve_api_ingest_config",
        lambda args: APIIngestConfig(
            fetch_format=args.fetch_format,
            api_url=args.api_url,
            tokens=args.api_tokens,
            user=args.api_user,
            project_name=project_name,
            project_id=None,
            output_dir=output_dir,
            max_concurrency=None,
            insecure=False,
        ),
    )
    monkeypatch.setattr(
        "importobot.cli.handlers.get_api_client",
        lambda fmt, **kwargs: MultiStageClient(),
    )

    args = Namespace(
        fetch_format=SupportedFormat.ZEPHYR,
        api_url="https://zephyr.example/rest/api/testcase",
        api_tokens=["primary-token"],
        api_user=None,
        project=project_name,
        input_dir=str(output_dir),
        max_concurrency=None,
        insecure=False,
        no_suggestions=True,
        apply_suggestions=False,
        files=None,
        directory=None,
        output=None,
        output_file=str(tmp_path / "suite.robot"),
        input=None,
    )

    saved_path = handle_api_ingest(args)
    metadata_path = Path(saved_path).with_suffix(".meta.json")

    assert Path(saved_path).exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["pages"] == 1
    assert metadata["items"] == 2
    assert metadata["project_name"] == project_name
    assert metadata["project"] == project_name
    assert metadata["format"] == SupportedFormat.ZEPHYR.value
    assert Path(saved_path).name.startswith("zephyr-project-alpha-")
