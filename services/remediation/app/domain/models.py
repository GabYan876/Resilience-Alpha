"""Entités et valeurs du domaine de remédiation (aucune dépendance framework)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class IncidentKind(StrEnum):
    """Nature d'un incident : détermine la famille d'actions à appliquer."""

    AVAILABILITY = "availability"  # flood / DoS : restaurer le service
    COMPROMISE = "compromise"  # SQLi / exfiltration : corriger la compromission


class IncidentStatus(StrEnum):
    DETECTED = "detected"
    REMEDIATING = "remediating"
    VERIFYING = "verifying"
    RESOLVED = "resolved"
    FAILED = "failed"


@dataclass(frozen=True)
class Anomaly:
    """Sortie brute du détecteur ML."""

    score: float  # plus élevé = plus anormal
    source: str  # ex. "prometheus:http_requests_rate"
    kind_hint: IncidentKind
    attacker_ip: str | None = None
    attacker_subject: str | None = None  # `sub` du jeton JWT, quand l'IP ne distingue personne
    target_service: str = "api"
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Incident:
    anomaly: Anomaly
    id: str = field(default_factory=lambda: uuid4().hex)
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    status: IncidentStatus = IncidentStatus.DETECTED
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def kind(self) -> IncidentKind:
        return self.anomaly.kind_hint


@dataclass(frozen=True)
class ActionResult:
    action: str
    success: bool
    detail: str = ""


@dataclass(frozen=True)
class RecoveryReport:
    """Preuve de reprise : API saine ET transaction de test réussie."""

    api_healthy: bool
    probe_transaction_ok: bool
    detail: str = ""

    @property
    def recovered(self) -> bool:
        return self.api_healthy and self.probe_transaction_ok


@dataclass(frozen=True)
class PipelineEvent:
    """Événement structuré émis à chaque étape (dashboard + Loki)."""

    event: str  # ex. "incident.detected", "action.executed", "incident.resolved"
    trace_id: str
    incident_id: str
    data: dict[str, object] = field(default_factory=dict)
    service: str = "remediation"
    at: datetime = field(default_factory=lambda: datetime.now(UTC))
