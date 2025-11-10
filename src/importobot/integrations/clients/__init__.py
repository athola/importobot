"""HTTP clients for integrating with external test management platform APIs.

This module provides clients for retrieving test data directly from test management
systems via their REST APIs. Each client manages authentication, pagination, and
payload parsing specific to its platform.

Example usage:

    from importobot.integrations.clients import get_api_client, SupportedFormat

    # Zephyr client with automatic discovery
    client = get_api_client(
        SupportedFormat.ZEPHYR,
        api_url="https://your-zephyr.example.com",
        tokens=["your-api-token"],
        project_name="PROJECT",
    )

    # Fetch all test cases
    for payload in client.fetch_all():
        print(f"Fetched {len(payload.get('testCases', []))} test cases")

    # TestRail client
    client = get_api_client(
        SupportedFormat.TESTRAIL,
        api_url="https://testrail.example.com/api/v2",
        tokens=["api-token"],
        user="automation@example.com",
        project_name="QA",
    )

    # JIRA/Xray client
    client = get_api_client(
        SupportedFormat.JIRA_XRAY,
        api_url="https://jira.example.com/rest/api/2/search",
        tokens=["jira-token"],
        project_name="ENG-QA",
    )

All clients offer the following features:
- Automatic API discovery and authentication strategy selection.
- Configurable pagination with rate limiting.
- Progress callbacks for large fetch operations.
- Error handling with exponential backoff.
- Flexible configuration via environment variables or constructor arguments.
"""

from __future__ import annotations

from importobot.integrations.clients.base import APISource, BaseAPIClient
from importobot.integrations.clients.jira_xray import JiraXrayClient
from importobot.integrations.clients.testlink import TestLinkClient
from importobot.integrations.clients.testrail import TestRailClient
from importobot.integrations.clients.zephyr import ZephyrClient
from importobot.medallion.interfaces.enums import SupportedFormat


def get_api_client(
    fetch_format: SupportedFormat,
    *,
    api_url: str,
    tokens: list[str],
    user: str | None,
    project_name: str | None,
    project_id: int | None,
    max_concurrency: int | None,
    verify_ssl: bool,
) -> APISource:
    """Create a platform-specific API client from format and configuration."""
    mapping = {
        SupportedFormat.JIRA_XRAY: JiraXrayClient,
        SupportedFormat.ZEPHYR: ZephyrClient,
        SupportedFormat.TESTRAIL: TestRailClient,
        SupportedFormat.TESTLINK: TestLinkClient,
    }
    if fetch_format not in mapping:
        raise ValueError(f"Unsupported fetch format {fetch_format}")
    client_cls = mapping[fetch_format]
    client: APISource = client_cls(
        api_url=api_url,
        tokens=tokens,
        user=user,
        project_name=project_name,
        project_id=project_id,
        max_concurrency=max_concurrency,
        verify_ssl=verify_ssl,
    )
    return client


__all__ = [
    "APISource",
    "BaseAPIClient",
    "JiraXrayClient",
    "TestLinkClient",
    "TestRailClient",
    "ZephyrClient",
    "get_api_client",
]
