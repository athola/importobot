"""TestLink API client for retrieving test suites."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from importobot.integrations.clients.base import BaseAPIClient, ProgressCallback


class TestLinkClient(BaseAPIClient):
    """Client for interacting with the TestLink XML-RPC JSON bridge endpoint."""

    __test__ = False

    def fetch_all(self, progress_cb: ProgressCallback) -> Iterator[dict[str, Any]]:
        """Retrieve all test suites from the TestLink API, handling pagination."""
        next_cursor: str | None = None
        page = 1
        while True:
            payload = {
                "devKey": self.tokens[0] if self.tokens else "",
                "command": "fetchTestSuite",
                "project": self._project_value(),
            }
            if next_cursor:
                payload["next"] = next_cursor

            response = self._request(
                "POST",
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            body = response.json()
            data = body.get("data", [])
            progress_cb(items=len(data), total=body.get("total"), page=page)
            yield body

            next_cursor = body.get("next")
            if not next_cursor:
                break
            page += 1


__all__ = ["TestLinkClient"]
