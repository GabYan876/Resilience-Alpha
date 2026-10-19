"""Orchestration : Detector -> DecisionPolicy -> RemediationAction[] -> RecoveryVerifier."""

from __future__ import annotations

from app.domain.models import (
    ActionResult,
    Incident,
    IncidentStatus,
    PipelineEvent,
)
from app.domain.ports import (
    DecisionPolicy,
    Detector,
    EventPublisher,
    RecoveryVerifier,
    RemediationAction,
)


class RemediationPipeline:
    """Cas d'usage principal. Ne connaît que des ports, jamais d'implémentation concrète."""

    def __init__(
        self,
        detector: Detector,
        policy: DecisionPolicy,
        verifier: RecoveryVerifier,
        publisher: EventPublisher,
        max_attempts: int = 2,
    ) -> None:
        self._detector = detector
        self._policy = policy
        self._verifier = verifier
        self._publisher = publisher
        self._max_attempts = max_attempts

    def run_once(self) -> Incident | None:
        """Traite au plus un incident. Retourne None si aucune anomalie n'est détectée."""
        anomaly = self._detector.detect()
        if anomaly is None:
            return None

        incident = Incident(anomaly)
        self._emit(
            incident,
            "incident.detected",
            kind=incident.kind.value,
            score=anomaly.score,
            source=anomaly.source,
            attacker_ip=anomaly.attacker_ip,
            target=anomaly.target_service,
        )

        for attempt in range(1, self._max_attempts + 1):
            incident.status = IncidentStatus.REMEDIATING
            actions = self._policy.decide(incident)
            self._emit(
                incident,
                "decision.made",
                attempt=attempt,
                actions=[a.name for a in actions],
            )
            for action in actions:
                self._emit_action(incident, self._execute(action, incident))

            incident.status = IncidentStatus.VERIFYING
            report = self._verifier.verify(incident)
            self._emit(
                incident,
                "verification.completed",
                attempt=attempt,
                api_healthy=report.api_healthy,
                probe_transaction_ok=report.probe_transaction_ok,
                detail=report.detail,
            )
            if report.recovered:
                incident.status = IncidentStatus.RESOLVED
                self._emit(incident, "incident.resolved", attempts=attempt)
                return incident

        incident.status = IncidentStatus.FAILED
        self._emit(incident, "incident.failed", attempts=self._max_attempts)
        return incident

    @staticmethod
    def _execute(action: RemediationAction, incident: Incident) -> ActionResult:
        try:
            return action.execute(incident)
        except Exception as exc:  # une action en échec n'arrête pas les suivantes
            return ActionResult(action.name, False, f"exception : {exc}")

    def _emit_action(self, incident: Incident, result: ActionResult) -> None:
        self._emit(
            incident,
            "action.executed",
            action=result.action,
            success=result.success,
            detail=result.detail,
        )

    def _emit(self, incident: Incident, event: str, **data: object) -> None:
        self._publisher.publish(
            PipelineEvent(
                event=event, trace_id=incident.trace_id, incident_id=incident.id, data=data
            )
        )
