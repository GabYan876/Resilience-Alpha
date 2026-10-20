"""Cas d'usage hors ligne : mesurer la qualité du modèle sur des jeux de données étiquetés.

Le trafic normal sert à compter les faux positifs, le trafic d'attaque à vérifier la détection.
Les alertes rejouent la règle du service en ligne (`confirmations` jugements anormaux de suite),
sans le délai de grâce : on mesure la détection, pas la remédiation.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import MetricSample
from app.domain.ports import AnomalyModel


@dataclass(frozen=True)
class EvaluationReport:
    normal_samples: int
    false_positive_samples: int  # mesures normales jugées anormales
    false_alarms: int  # alertes qui auraient été signalées à tort sur le trafic normal
    attack_samples: int
    detected_samples: int  # mesures d'attaque jugées anormales
    attack_detected: bool  # une alerte confirmée aurait été signalée pendant l'attaque
    detection_delay_samples: int | None  # rang de la mesure qui confirme l'alerte (1 = première)

    @property
    def false_positive_rate(self) -> float:
        return self.false_positive_samples / self.normal_samples if self.normal_samples else 0.0

    @property
    def detection_rate(self) -> float:
        return self.detected_samples / self.attack_samples if self.attack_samples else 0.0


def count_alarms(flags: list[bool], confirmations: int) -> tuple[int, int | None]:
    """Nombre d'alertes sur une série de jugements, et rang de la première (None si aucune)."""
    streak = 0
    alarms = 0
    first: int | None = None
    for rank, anomalous in enumerate(flags, start=1):
        streak = streak + 1 if anomalous else 0
        if streak >= confirmations:
            alarms += 1
            first = first or rank
            streak = 0  # comme en ligne : une alerte signalée remet la série à zéro
    return alarms, first


def evaluate_model(
    model: AnomalyModel,
    normal: list[MetricSample],
    attack: list[MetricSample],
    *,
    confirmations: int,
) -> EvaluationReport:
    normal_flags = [model.evaluate(s).anomalous for s in normal]
    attack_flags = [model.evaluate(s).anomalous for s in attack]
    false_alarms, _ = count_alarms(normal_flags, confirmations)
    attack_alarms, first = count_alarms(attack_flags, confirmations)
    return EvaluationReport(
        normal_samples=len(normal),
        false_positive_samples=sum(normal_flags),
        false_alarms=false_alarms,
        attack_samples=len(attack),
        detected_samples=sum(attack_flags),
        attack_detected=attack_alarms > 0,
        detection_delay_samples=first,
    )
