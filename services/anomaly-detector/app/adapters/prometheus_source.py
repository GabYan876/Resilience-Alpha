"""Source de mesures : requêtes instantanées sur l'API HTTP de Prometheus."""

from __future__ import annotations

import math

import httpx

from app.domain.models import MetricSample


class PrometheusMetricsSource:
    def __init__(
        self, client: httpx.Client, base_url: str, service: str, *, window: str = "30s"
    ) -> None:
        self._client = client
        self._url = f"{base_url}/api/v1/query"
        sel = f'service="{service}"'
        self._queries = {
            "request_rate": f"sum(rate(http_requests_total{{{sel}}}[{window}]))",
            "error_ratio": (
                f'sum(rate(http_requests_total{{{sel},status=~"5.*"}}[{window}]))'
                f" / sum(rate(http_requests_total{{{sel}}}[{window}]))"
            ),
            "latency_p95_s": (
                "histogram_quantile(0.95, sum by (le) "
                f"(rate(http_request_duration_seconds_bucket{{{sel}}}[{window}])))"
            ),
            "up": f"min(up{{{sel}}})",
        }

    def sample(self) -> MetricSample:
        values = {name: self._query(promql) for name, promql in self._queries.items()}
        return MetricSample(**values)

    def _query(self, promql: str) -> float:
        response = self._client.get(self._url, params={"query": promql})
        response.raise_for_status()
        result = response.json()["data"]["result"]
        if not result:  # série absente (aucun trafic, cible jamais vue) : 0 plutôt qu'une erreur
            return 0.0
        value = float(result[0]["value"][1])
        return 0.0 if math.isnan(value) else value  # NaN = division par zéro sans trafic
