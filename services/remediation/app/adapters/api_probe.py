"""Sonde de transaction : rejoue un paiement de test fictif de bout en bout via l'API métier."""

from __future__ import annotations

import httpx


class ApiTransactionProbe:
    # Compte et montant fictifs : aucune donnée réelle.
    _PAYLOAD = {"from_account": "TEST-0001", "to_account": "TEST-0002", "amount": 1.0}

    def __init__(self, client: httpx.Client, base_url: str, token: str = "") -> None:
        self._client = client
        self._url = f"{base_url.rstrip('/')}/transactions"
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    def run(self) -> bool:
        try:
            response = self._client.post(self._url, json=self._PAYLOAD, headers=self._headers)
        except httpx.HTTPError:
            return False
        return response.is_success
