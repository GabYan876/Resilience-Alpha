"""Orchestration : Detector -> DecisionPolicy -> RemediationAction[] -> RecoveryVerifier."""

from __future__ import annotations

import threading

from app.domain.models import (
    ActionResult,
    Anomaly,
    Incident,
    IncidentStatus,
    PipelineEvent,
)
from app.domain.ports import (
    DecisionPolicy,
    Detector,
    EventPublisher,
    IncidentStore,
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
        store: IncidentStore | None = None,
    ) -> None:
        self._detector = detector
        self._policy = policy
        self._verifier = verifier
        self._publisher = publisher
        self._max_attempts = max_attempts
        self._store = store
        # Un seul incident à la fois : un flood et un crash simultanés visent le même service,
        # deux redémarrages concurrents se perturberaient et fausseraient la vérification.
        self._lock = threading.Lock()

    def run_once(self) -> Incident | None:
        """Traite au plus un incident. Retourne None si aucune anomalie n'est détectée.

        Ne bloque jamais : si un incident est déjà en cours, la sonde passe son tour (la santé
        mesurée pendant un redémarrage n'est pas un nouvel incident).
        """
        if not self._lock.acquire(blocking=False):
            return None
        try:
            anomaly = self._detector.detect()
            if anomaly is None:
                return None
            return self._handle_unlocked(anomaly)
        finally:
            self._lock.release()

    def handle(self, anomaly: Anomaly) -> Incident:
        """Traite une anomalie déjà détectée (ex. remontée par le détecteur via l'API)."""
        with self._lock:
            return self._handle_unlocked(anomaly)

    def _handle_unlocked(self, anomaly: Anomaly) -> Incident:
        incident = Incident(anomaly)
        self._save(incident)
        try:
            return self._process(incident)
        finally:
            self._save(incident)  # état final (résolu / en échec) pour GET /incidents

    def _save(self, incident: Incident) -> None:
        if self._store is not None:
            self._store.save(incident)

    def _process(self, incident: Incident) -> Incident:
        anomaly = incident.anomaly
        self._emit(
            incident,
            "incident.detected",
            kind=incident.kind.value,
            score=anomaly.score,
            source=anomaly.source,
            attacker_ip=anomaly.attacker_ip,
            attacker_subject=anomaly.attacker_subject,
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
            if not actions:
                # Sans action, une API « saine » ne prouverait aucune remédiation.
                incident.status = IncidentStatus.FAILED
                self._emit(incident, "incident.failed", reason="no_action")
                return incident
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
