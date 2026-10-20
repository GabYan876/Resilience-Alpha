"""Ports du détecteur : petits et ciblés, implémentés par les adaptateurs."""

from __future__ import annotations

from typing import Protocol

from app.domain.models import Detection, IntegritySnapshot, MetricSample, Verdict


class MetricsSource(Protocol):
    """Lit l'état courant du service surveillé."""

    def sample(self) -> MetricSample: ...


class AnomalyModel(Protocol):
    """Juge un échantillon ; le seuil est appris avec le modèle, jamais codé en dur."""

    def evaluate(self, sample: MetricSample) -> Verdict: ...


class ModelTrainer(Protocol):
    def fit(self, samples: list[MetricSample]) -> AnomalyModel: ...


class ModelStore(Protocol):
    def save(self, model: AnomalyModel) -> None: ...

    def load(self) -> AnomalyModel: ...


class SampleRecorder(Protocol):
    """Ajoute un échantillon au jeu de données d'entraînement."""

    def record(self, sample: MetricSample) -> None: ...


class SampleReader(Protocol):
    def read_all(self) -> list[MetricSample]: ...


class AttackerLocator(Protocol):
    """Identifie la source du trafic anormal ; `None` si personne ne se détache nettement."""

    def locate(self) -> str | None: ...


class AnomalyReporter(Protocol):
    """Transmet une anomalie confirmée au moteur de remédiation."""

    def report(self, detection: Detection) -> None: ...


class VerdictObserver(Protocol):
    """Observe chaque jugement (métrique Prometheus, journal) sans influer sur la décision."""

    def observe(self, sample: MetricSample, verdict: Verdict) -> None: ...


class IntegritySource(Protocol):
    """Lit les compteurs d'intégrité de la base (sans accès aux données)."""

    def snapshot(self) -> IntegritySnapshot: ...
