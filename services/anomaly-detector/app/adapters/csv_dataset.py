"""Jeu de données d'entraînement au format CSV (`ml/data/`)."""

from __future__ import annotations

import csv
from pathlib import Path

from app.domain.models import FEATURE_NAMES, MetricSample


class CsvDataset:
    def __init__(self, path: Path) -> None:
        self._path = path

    def record(self, sample: MetricSample) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not self._path.exists()
        with self._path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if is_new:
                writer.writerow(FEATURE_NAMES)
            writer.writerow(sample.as_vector())

    def read_all(self) -> list[MetricSample]:
        with self._path.open(newline="", encoding="utf-8") as handle:
            return [
                MetricSample.from_vector([float(row[name]) for name in FEATURE_NAMES])
                for row in csv.DictReader(handle)
            ]
