"""Tests for CLI parser fetch options."""

from argparse import Namespace

import pytest

from importobot.cli.parser import create_parser
from importobot.medallion.interfaces.enums import SupportedFormat


def parse_args(args: list[str]) -> Namespace:
    """Helper to parse arguments with the shared parser."""
    parser = create_parser()
    return parser.parse_args(args)


def test_fetch_arguments_registered() -> None:
    """Parser should accept API fetch related flags."""
    args = parse_args(
        [
            "--fetch-format",
            "testrail",
            "--api-url",
            "https://testrail.example/api",
            "--tokens",
            "token-a",
            "--tokens",
            "token-b",
            "--api-user",
            "automation",
            "--project",
            "QA",
            "--input-dir",
            "downloads",
        ]
    )

    assert args.fetch_format is SupportedFormat.TESTRAIL
    assert args.api_url == "https://testrail.example/api"
    assert args.api_tokens == ["token-a", "token-b"]
    assert args.api_user == "automation"
    assert args.project == "QA"
    assert args.input_dir == "downloads"


@pytest.mark.parametrize(
    ("token_args", "expected"),
    [
        (["--tokens", "alpha,beta,gamma"], ["alpha", "beta", "gamma"]),
        (
            ["--tokens", "alpha", "--tokens", "beta,gamma"],
            ["alpha", "beta", "gamma"],
        ),
    ],
)
def test_tokens_support_comma_and_repeat(
    token_args: list[str], expected: list[str]
) -> None:
    """Tokens should support comma separated usage and repeated flags."""
    args = parse_args(
        [
            "--fetch-format",
            "zephyr",
            "--api-url",
            "https://jira.example/api",
            *token_args,
        ]
    )

    assert args.fetch_format is SupportedFormat.ZEPHYR
    assert args.api_tokens == expected
