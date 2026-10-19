from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.models import Anomaly, Incident, IncidentKind


class AnomalyIn(BaseModel):
    score: float
    source: str
    kind: IncidentKind
    attacker_ip: str | None = None
    target_service: str = Field(default="api")

    def to_domain(self) -> Anomaly:
        return Anomaly(
            score=self.score,
            source=self.source,
            kind_hint=self.kind,
            attacker_ip=self.attacker_ip,
            target_service=self.target_service,
        )


class IncidentOut(BaseModel):
    id: str
    trace_id: str
    kind: IncidentKind
    status: str

    @classmethod
    def from_domain(cls, incident: Incident) -> IncidentOut:
        return cls(
            id=incident.id,
            trace_id=incident.trace_id,
            kind=incident.kind,
            status=incident.status.value,
        )
