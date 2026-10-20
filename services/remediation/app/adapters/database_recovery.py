"""Client HTTP du service de restauration, protégé par le jeton de sonde partagé."""

from __future__ import annotations

import httpx


class HttpDatabaseRestorer:
    def __init__(self, client: httpx.Client, base_url: str, token: str) -> None:
        self._client = client
        self._url = f"{base_url.rstrip('/')}/restore"
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    def restore_latest(self) -> None:
        response = self._client.post(self._url, headers=self._headers, timeout=120.0)
        response.raise_for_status()
