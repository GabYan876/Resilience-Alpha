"""Santé d'un service via son endpoint HTTP."""

from __future__ import annotations

from collections.abc import Mapping

import httpx


class HttpHealthChecker:
    def __init__(self, client: httpx.Client, health_urls: Mapping[str, str]) -> None:
        self._client = client
        self._health_urls = health_urls

    def is_healthy(self, service: str) -> bool:
        url = self._health_urls.get(service)
        if url is None:
            return False
        try:
            return self._client.get(url).is_success
        except httpx.HTTPError:
            return False
