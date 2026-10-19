"""Vérification de reprise : API saine ET transaction de test réussie."""

from __future__ import annotations

from app.domain.models import Incident, RecoveryReport
from app.domain.ports import HealthChecker, TransactionProbe


class HealthAndProbeVerifier:
    """Un conteneur qui redémarre ne prouve rien : on exige aussi une transaction qui passe."""

    def __init__(self, health: HealthChecker, probe: TransactionProbe) -> None:
        self._health = health
        self._probe = probe

    def verify(self, incident: Incident) -> RecoveryReport:
        service = incident.anomaly.target_service
        if not self._health.is_healthy(service):
            return RecoveryReport(False, False, f"{service} non sain")
        try:
            probe_ok = self._probe.run()
        except Exception as exc:  # la sonde ne doit jamais faire planter le pipeline
            return RecoveryReport(True, False, f"sonde en erreur : {exc}")
        detail = "reprise prouvée" if probe_ok else "transaction de test refusée"
        return RecoveryReport(True, probe_ok, detail)
