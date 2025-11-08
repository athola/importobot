"""TestRail API client for fetching test runs and cases."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from urllib.parse import parse_qs, urlparse

from importobot.integrations.clients.base import BaseAPIClient, ProgressCallback


class TestRailClient(BaseAPIClient):
    """Client for TestRail API pagination."""

    __test__ = False

    def __init__(self, **kwargs: Any) -> None:
        """Initialize TestRailClient with API connection parameters."""
        super().__init__(**kwargs)
        if self.user and self.tokens:
            self._session.auth = (self.user, self.tokens[0])

    def _auth_headers(self) -> dict[str, str]:
        """Override to rely on requests' built-in Basic auth handling."""
        return {}

    def fetch_all(self, progress_cb: ProgressCallback) -> Iterator[dict[str, Any]]:
        """Fetch all test runs from TestRail API with pagination."""
        offset = 0
        page = 1
        while True:
            params = {"offset": offset}
            response = self._request(
                "GET", self.api_url, params=params, headers=self._auth_headers()
            )
            payload = response.json()

            runs = payload.get("runs") or payload.get("cases") or []
            progress_cb(items=len(runs), total=None, page=page)
            yield payload

            next_link = payload.get("_links", {}).get("next")
            if not next_link:
                break

            parsed = urlparse(next_link)
            query = parse_qs(parsed.query)
            if "offset" in query:
                try:
                    offset = int(query["offset"][0])
                except (ValueError, TypeError, IndexError):
                    offset += len(runs)
            else:
                offset += len(runs)
            page += 1


__all__ = ["TestRailClient"]
