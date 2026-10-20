"""Cas d'usage : surveiller l'intégrité du grand livre et signaler une corruption.

Transactions et écritures sont en ajout seul (le rôle applicatif n'a pas de `DELETE`) : un
compteur qui baisse, ou une transaction qui ne s'équilibre plus, prouve une altération. C'est
un invariant du modèle de données, pas un seuil : il complète le détecteur ML (disponibilité).
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.domain.models import Detection, IncidentKind, IntegritySnapshot
from app.domain.ports import AnomalyReporter, IntegritySource

log = logging.getLogger("detector")


class IntegrityWatchService:
    """Signale `database_corruption` dès qu'un invariant du grand livre est violé.

    Après un signalement le moteur restaure une archive, donc les compteurs reculent
    légitimement : la référence est oubliée et réapprise au tick suivant.
    """

    def __init__(
        self,
        source: IntegritySource,
        reporter: AnomalyReporter,
        *,
        target_service: str,
        cooldown_s: float,
        clock: Callable[[], float],
    ) -> None:
        self._source = source
        self._reporter = reporter
        self._target = target_service
        self._cooldown_s = cooldown_s
        self._clock = clock
        self._baseline: IntegritySnapshot | None = None
        self._quiet_until = 0.0

    def tick(self) -> Detection | None:
        try:
            snapshot = self._source.snapshot()
        except Exception:  # base ou db-recovery injoignable : pas une preuve de corruption
            log.exception("intégrité illisible", extra={"event": "detector.integrity_failed"})
            return None

        if not self._is_corrupted(snapshot):
            self._baseline = snapshot
            return None
        now = self._clock()
        if now < self._quiet_until:
            return None

        detection = Detection(
            score=1.0,
            source="db-recovery:integrity",
            kind=IncidentKind.DATABASE_CORRUPTION,
            target_service=self._target,
        )
        try:
            self._reporter.report(detection)
        except Exception:  # on retentera au tick suivant, la violation persiste
            log.exception("signalement impossible", extra={"event": "detector.report_failed"})
            return None
        self._baseline = None
        self._quiet_until = now + self._cooldown_s
        return detection

    def _is_corrupted(self, snapshot: IntegritySnapshot) -> bool:
        if snapshot.unbalanced_transactions > 0:
            return True
        baseline = self._baseline
        return baseline is not None and (
            snapshot.transactions < baseline.transactions
            or snapshot.ledger_entries < baseline.ledger_entries
        )
