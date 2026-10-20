"""Détection de panne par sondage de santé : un service qui ne répond plus est tombé."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.models import Anomaly, IncidentKind
from app.domain.ports import HealthChecker


class HealthWatchDetector:
    """Signale un service après `failure_threshold` sondages consécutifs en échec.

    Une panne binaire (conteneur arrêté, processus mort) n'a pas besoin du modèle ML : le
    sondage suffit, et une seule réponse manquée ne doit pas déclencher de redémarrage.
    """

    def __init__(
        self, health: HealthChecker, services: Sequence[str], failure_threshold: int = 3
    ) -> None:
        self._health = health
        self._services = tuple(services)
        self._failure_threshold = failure_threshold
        self._failures = dict.fromkeys(self._services, 0)

    def detect(self) -> Anomaly | None:
        for service in self._services:
            if self._health.is_healthy(service):
                self._failures[service] = 0
                continue
            self._failures[service] += 1
            if self._failures[service] >= self._failure_threshold:
                self._failures[service] = 0  # repart de zéro : la vérification prend le relais
                return Anomaly(
                    score=1.0,
                    source=f"healthcheck:{service}",
                    kind_hint=IncidentKind.CRASH,
                    target_service=service,
                )
        return None
