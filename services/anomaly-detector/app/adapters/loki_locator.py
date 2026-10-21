"""Désigne le compte qui émet l'essentiel du trafic, d'après le journal d'accès du WAF dans Loki.

Le WAF journalise le `sub` du jeton JWT de chaque requête authentifiée. On compte les requêtes
par compte sur la fenêtre récente ; un compte n'est désigné que s'il dépasse un volume minimal
ET une part minimale du trafic identifié (voir `Settings`), pour ne pas accuser un utilisateur
légitime pendant un pic.
"""

from __future__ import annotations

import httpx


class LokiAttackerLocator:
    def __init__(
        self,
        client: httpx.Client,
        base_url: str,
        *,
        window: str = "30s",
        min_requests: int = 100,
        min_share: float = 0.5,
    ) -> None:
        self._client = client
        self._url = f"{base_url}/loki/api/v1/query"
        self._query = (
            f'sum by (sub) (count_over_time({{service="waf", event="waf.request"}} | json | sub != "" [{window}]))'
        )
        self._min_requests = min_requests
        self._min_share = min_share

    def locate(self) -> str | None:
        response = self._client.get(self._url, params={"query": self._query})
        response.raise_for_status()
        counts = {
            row["metric"]["sub"]: float(row["value"][1])
            for row in response.json()["data"]["result"]
        }
        total = sum(counts.values())
        if not counts or total == 0:
            return None
        top, top_count = max(counts.items(), key=lambda item: item[1])
        if top_count < self._min_requests or top_count / total < self._min_share:
            return None
        return top
