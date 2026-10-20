"""Source d'intégrité : `GET /integrity` du service privé `db-recovery`."""

from __future__ import annotations

import httpx

from app.domain.models import IntegritySnapshot


class HttpIntegritySource:
    def __init__(self, client: httpx.Client, base_url: str) -> None:
        self._client = client
        self._url = f"{base_url}/integrity"

    def snapshot(self) -> IntegritySnapshot:
        response = self._client.get(self._url)
        response.raise_for_status()
        body = response.json()
        return IntegritySnapshot(
            transactions=int(body["transactions"]),
            ledger_entries=int(body["ledger_entries"]),
            unbalanced_transactions=int(body["unbalanced_transactions"]),
        )
