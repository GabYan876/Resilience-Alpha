from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models import Anomaly, Incident, IncidentKind


class AnomalyIn(BaseModel):
    score: float
    source: str
    kind: IncidentKind
    attacker_ip: str | None = None
    attacker_subject: str | None = None
    target_service: str = Field(default="api")

    def to_domain(self) -> Anomaly:
        return Anomaly(
            score=self.score,
            source=self.source,
            kind_hint=self.kind,
            attacker_ip=self.attacker_ip,
            attacker_subject=self.attacker_subject,
            target_service=self.target_service,
        )


class IncidentOut(BaseModel):
    id: str
    trace_id: str
    kind: IncidentKind
    status: str
    started_at: datetime
    target_service: str
    source: str
    score: float
    attacker_ip: str | None = None
    attacker_subject: str | None = None

    @classmethod
    def from_domain(cls, incident: Incident) -> IncidentOut:
        return cls(
            id=incident.id,
            trace_id=incident.trace_id,
            kind=incident.kind,
            status=incident.status.value,
            started_at=incident.started_at,
            target_service=incident.anomaly.target_service,
            source=incident.anomaly.source,
            score=incident.anomaly.score,
            attacker_ip=incident.anomaly.attacker_ip,
            attacker_subject=incident.anomaly.attacker_subject,
        )


class BlocklistOut(BaseModel):
    """Lecture seule de `blocked.txt` : vide = personne bloqué (état attendu avant une démo)."""

    entries: list[str]
