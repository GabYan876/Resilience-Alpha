"""Entités et valeurs du domaine de détection (aucune dépendance framework)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

FEATURE_NAMES = ("request_rate", "error_ratio", "latency_p95_s", "up")


class IncidentKind(StrEnum):
    """Même vocabulaire que le moteur de remédiation (contrat de `POST /incidents`)."""

    AVAILABILITY = "availability"
    COMPROMISE = "compromise"
    DATABASE_CORRUPTION = "database_corruption"  # accepté par le moteur ; aucun signal ML encore


@dataclass(frozen=True)
class MetricSample:
    """Un point de mesure d'un service : l'entrée du modèle."""

    request_rate: float  # requêtes/s
    error_ratio: float  # part des réponses 5xx, 0 si aucun trafic
    latency_p95_s: float  # latence p95 en secondes
    up: float  # 1.0 si la cible est jointe par Prometheus, sinon 0.0

    def as_vector(self) -> list[float]:
        return [self.request_rate, self.error_ratio, self.latency_p95_s, self.up]

    @classmethod
    def from_vector(cls, values: list[float]) -> MetricSample:
        return cls(*values)


@dataclass(frozen=True)
class Verdict:
    """Jugement du modèle sur un échantillon."""

    score: float  # plus élevé = plus anormal
    anomalous: bool


@dataclass(frozen=True)
class Detection:
    """Anomalie confirmée, prête à être transmise au moteur de remédiation."""

    score: float
    source: str
    kind: IncidentKind
    target_service: str
    attacker_ip: str | None = None
    attacker_subject: str | None = None  # compte (`sub` du JWT) qui émet l'essentiel du trafic
