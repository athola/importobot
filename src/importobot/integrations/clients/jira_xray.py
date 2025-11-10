"""JIRA/Xray API client for retrieving test issues."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from importobot.integrations.clients.base import BaseAPIClient, ProgressCallback


class JiraXrayClient(BaseAPIClient):
    """Client for performing Jira/Xray issue searches."""

    __test__ = False
    _page_size = 200

    def fetch_all(self, progress_cb: ProgressCallback) -> Iterator[dict[str, Any]]:
        """Retrieve all issues from the Jira/Xray API, handling pagination."""
        start_at = 0
        total: int | None = None
        while True:
            params: dict[str, Any] = {
                "startAt": start_at,
                "maxResults": self._page_size,
            }
            project_ref = self._project_value()
            if project_ref is not None:
                params["jql"] = f"project={project_ref}"

            response = self._request(
                "GET", self.api_url, params=params, headers=self._auth_headers()
            )
            payload = response.json()
            issues = payload.get("issues", [])
            total = payload.get("total", total)
            progress_cb(
                items=len(issues),
                total=total,
                page=(start_at // self._page_size) + 1,
            )
            yield payload

            start_at = payload.get("startAt", start_at) + len(issues)
            if total is not None and start_at >= total:
                break
            if not issues:
                break


__all__ = ["JiraXrayClient"]
