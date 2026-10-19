"""Ports du moteur de remédiation.

Pipeline : Detector -> DecisionPolicy -> RemediationAction[] -> RecoveryVerifier.
Les ports « capacité » (ContainerRestarter, IpBlocker...) sont volontairement
petits (ISP) : une action ne dépend que de ce dont elle a besoin.
"""

from __future__ import annotations

from typing import Protocol, Sequence

from app.domain.models import (
    ActionResult,
    Anomaly,
    Incident,
    PipelineEvent,
    RecoveryReport,
)

# --- Pipeline -------------------------------------------------------------


class Detector(Protocol):
    """Retourne une anomalie si le modèle ML en voit une, sinon None."""

    def detect(self) -> Anomaly | None: ...


class RemediationAction(Protocol):
    """Stratégie de remédiation. Ajouter une action = ajouter une classe (OCP)."""

    name: str

    def execute(self, incident: Incident) -> ActionResult: ...


class DecisionPolicy(Protocol):
    """Choisit les actions selon la nature de l'incident (disponibilité ≠ compromission)."""

    def decide(self, incident: Incident) -> Sequence[RemediationAction]: ...


class RecoveryVerifier(Protocol):
    """Clôt l'incident seulement si l'API est saine ET une transaction de test passe."""

    def verify(self, incident: Incident) -> RecoveryReport: ...


# --- Capacités utilisées par les actions (implémentées dans adapters/) -----


class ContainerRestarter(Protocol):
    def restart(self, service: str) -> None: ...


class ServiceScaler(Protocol):
    def scale(self, service: str, replicas: int) -> None: ...


class IpBlocker(Protocol):
    def block(self, ip: str) -> None: ...

    def unblock(self, ip: str) -> None: ...  # nécessaire au reset de démo


class SecretRotator(Protocol):
    def rotate(self, secret_name: str) -> None: ...


# --- Capacités utilisées par la vérification -------------------------------


class HealthChecker(Protocol):
    def is_healthy(self, service: str) -> bool: ...


class TransactionProbe(Protocol):
    """Joue une transaction de test fictive de bout en bout."""

    def run(self) -> bool: ...


# --- Observabilité du pipeline ---------------------------------------------


class EventPublisher(Protocol):
    """Émet un événement JSON structuré (stdout -> Loki, flux -> dashboard)."""

    def publish(self, event: PipelineEvent) -> None: ...
