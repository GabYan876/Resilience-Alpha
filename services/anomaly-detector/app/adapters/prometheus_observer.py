"""Expose le score d'anomalie en métrique, pour le dashboard (avant / pendant / après)."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Gauge

from app.domain.models import MetricSample, Verdict


class PrometheusVerdictObserver:
    def __init__(self, registry: CollectorRegistry) -> None:
        self._score = Gauge("anomaly_score", "Score d'anomalie du modèle ML", registry=registry)
        self._anomalous = Gauge(
            "anomaly_detected", "1 si le dernier échantillon est jugé anormal", registry=registry
        )

    def observe(self, sample: MetricSample, verdict: Verdict) -> None:
        self._score.set(verdict.score)
        self._anomalous.set(1.0 if verdict.anomalous else 0.0)
