"""Cas d'usage : une itération de surveillance (mesurer, juger, confirmer, signaler)."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

from app.domain.models import Detection, IncidentKind
from app.domain.ports import AnomalyModel, AnomalyReporter, MetricsSource, VerdictObserver

log = logging.getLogger("detector")


class DetectionService:
    """Signale une anomalie après `confirmations` jugements anormaux consécutifs.

    Le délai de grâce évite de re-signaler pendant que le moteur de remédiation répare : il
    redémarre le service, ce qui reste anormal quelques secondes.
    """

    def __init__(
        self,
        source: MetricsSource,
        model: AnomalyModel,
        reporter: AnomalyReporter,
        *,
        target_service: str,
        confirmations: int,
        cooldown_s: float,
        clock: Callable[[], float],
        observers: Sequence[VerdictObserver] = (),
    ) -> None:
        self._source = source
        self._model = model
        self._reporter = reporter
        self._target = target_service
        self._confirmations = confirmations
        self._cooldown_s = cooldown_s
        self._clock = clock
        self._observers = observers
        self._streak = 0
        self._quiet_until = 0.0

    def tick(self) -> Detection | None:
        """Retourne la détection signalée à cette itération, sinon `None`."""
        try:
            sample = self._source.sample()
        except Exception:  # Prometheus injoignable ne doit pas arrêter la surveillance
            log.exception("mesure impossible", extra={"event": "detector.sample_failed"})
            return None

        verdict = self._model.evaluate(sample)
        for observer in self._observers:
            observer.observe(sample, verdict)

        self._streak = self._streak + 1 if verdict.anomalous else 0
        now = self._clock()
        if self._streak < self._confirmations or now < self._quiet_until:
            return None

        detection = Detection(
            score=verdict.score,
            source=f"prometheus:{self._target}",
            kind=IncidentKind.AVAILABILITY,
            target_service=self._target,
        )
        try:
            self._reporter.report(detection)
        except Exception:  # on retentera à l'itération suivante, la série reste confirmée
            log.exception("signalement impossible", extra={"event": "detector.report_failed"})
            return None
        self._streak = 0
        self._quiet_until = now + self._cooldown_s
        return detection
