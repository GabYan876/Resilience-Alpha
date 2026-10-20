"""Signalement d'une anomalie au moteur de remédiation (`POST /incidents`, jeton Bearer).

`POST /incidents` exécute tout le pipeline de remédiation de façon synchrone côté moteur
(détection déjà faite -> décision -> action -> vérification) avant de répondre : largement
plus long que le délai d'une requête Prometheus. Un timeout trop court ferait croire à un
échec alors que le moteur a bien agi, et empêcherait le délai de grâce de s'enclencher (la
série de jugements anormaux resterait confirmée, donc un nouveau signalement partirait au
tick suivant) : on utilise ici un timeout propre à cet appel, pas celui du client HTTP
partagé avec les requêtes Prometheus.
"""

from __future__ import annotations

import httpx

from app.domain.models import Detection


class HttpAnomalyReporter:
    def __init__(
        self, client: httpx.Client, base_url: str, token: str, *, timeout_s: float = 75.0
    ) -> None:
        self._client = client
        self._url = f"{base_url}/incidents"
        self._headers = {"Authorization": f"Bearer {token}"}
        self._timeout_s = timeout_s

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
            timeout=self._timeout_s,
        )
        response.raise_for_status()
