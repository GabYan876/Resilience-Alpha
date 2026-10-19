"""Vérification de reprise : API saine ET transaction de test réussie."""

from __future__ import annotations

import time
from collections.abc import Callable

from app.domain.models import Incident, RecoveryReport
from app.domain.ports import HealthChecker, TransactionProbe


class HealthAndProbeVerifier:
    """Un conteneur qui redémarre ne prouve rien : on exige aussi une transaction qui passe."""

    def __init__(
        self,
        health: HealthChecker,
        probe: TransactionProbe,
        health_wait_s: float = 0.0,
        poll_interval_s: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._health = health
        self._probe = probe
        self._health_wait_s = health_wait_s
        self._poll_interval_s = poll_interval_s
        self._sleep = sleep
        self._monotonic = monotonic

    def _wait_until_healthy(self, service: str) -> bool:
        """Un redémarrage rend la main avant que l'API ait fini de démarrer : on laisse un délai."""
        deadline = self._monotonic() + self._health_wait_s
        while not self._health.is_healthy(service):
            if self._monotonic() >= deadline:
                return False
            self._sleep(self._poll_interval_s)
        return True

    def verify(self, incident: Incident) -> RecoveryReport:
        service = incident.anomaly.target_service
        if not self._wait_until_healthy(service):
            return RecoveryReport(False, False, f"{service} non sain")
        try:
            probe_ok = self._probe.run()
        except Exception as exc:  # la sonde ne doit jamais faire planter le pipeline
            return RecoveryReport(True, False, f"sonde en erreur : {exc}")
        detail = "reprise prouvée" if probe_ok else "transaction de test refusée"
        return RecoveryReport(True, probe_ok, detail)
