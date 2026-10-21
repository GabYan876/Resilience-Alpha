"""Sonde de transaction : rejoue un paiement de test fictif de bout en bout via l'API métier."""

from __future__ import annotations

import uuid

import httpx


class ApiTransactionProbe:
    def __init__(
        self,
        client: httpx.Client,
        base_url: str,
        token: str = "",
        from_account: str = "TEST-0001",
        to_account: str = "TEST-0002",
        amount_cents: int = 100,
    ) -> None:
        self._client = client
        self._url = f"{base_url.rstrip('/')}/transactions"
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._from_account = from_account
        self._to_account = to_account
        self._amount_cents = amount_cents

    def run(self) -> bool:
        try:
            response = self._client.post(
                self._url,
                json={
                    "from_account": self._from_account,
                    "to_account": self._to_account,
                    "amount_cents": self._amount_cents,
                    "idempotency_key": f"check-{uuid.uuid4().hex}",
                },
                headers=self._headers,
            )
        except httpx.HTTPError:
            return False
        if not response.is_success:
            return False
        try:
            body = response.json()
        except ValueError:
            return False
        return isinstance(body, dict) and body.get("status") == "settled"
