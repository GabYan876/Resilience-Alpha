"""Signalement d'une anomalie au moteur de remédiation (`POST /incidents`, jeton Bearer)."""

from __future__ import annotations

import httpx

from app.domain.models import Detection


class HttpAnomalyReporter:
    def __init__(self, client: httpx.Client, base_url: str, token: str) -> None:
        self._client = client
        self._url = f"{base_url}/incidents"
        self._headers = {"Authorization": f"Bearer {token}"}

    def report(self, detection: Detection) -> None:
        response = self._client.post(
            self._url,
            headers=self._headers,
            json={
                "score": detection.score,
                "source": detection.source,
                "kind": detection.kind.value,
                "attacker_ip": detection.attacker_ip,
                "target_service": detection.target_service,
            },
        )
        response.raise_for_status()
