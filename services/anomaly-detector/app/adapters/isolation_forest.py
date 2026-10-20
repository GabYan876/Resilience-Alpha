"""Modèle IsolationForest (scikit-learn) et sa persistance.

Aucune règle codée en dur sur le trafic : le seuil d'alerte est dérivé des scores obtenus sur
le trafic normal d'entraînement, avec une marge pour absorber la variabilité non observée.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from app.domain.models import MetricSample, Verdict
from app.domain.ports import AnomalyModel


@dataclass(frozen=True)
class IsolationForestModel:
    forest: IsolationForest
    threshold: float  # `score_samples` en dessous de cette valeur = anormal

    def evaluate(self, sample: MetricSample) -> Verdict:
        raw = float(self.forest.score_samples(np.array([sample.as_vector()]))[0])
        return Verdict(score=-raw, anomalous=raw < self.threshold)


class IsolationForestTrainer:
    def __init__(self, *, margin: float = 0.02, n_estimators: int = 200, seed: int = 42) -> None:
        self._margin = margin
        self._n_estimators = n_estimators
        self._seed = seed

    def fit(self, samples: list[MetricSample]) -> IsolationForestModel:
        data = np.array([s.as_vector() for s in samples])
        forest = IsolationForest(n_estimators=self._n_estimators, random_state=self._seed)
        forest.fit(data)
        threshold = float(forest.score_samples(data).min()) - self._margin
        return IsolationForestModel(forest, threshold)


class JoblibModelStore:
    """Le fichier modèle est du code désérialisé : il doit être monté en lecture seule."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, model: AnomalyModel) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, self._path)

    def load(self) -> AnomalyModel:
        model: AnomalyModel = joblib.load(self._path)
        return model
