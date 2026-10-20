"""Cas d'usage hors ligne : constituer le jeu de données puis entraîner le modèle."""

from __future__ import annotations

from collections.abc import Callable

from app.domain.ports import MetricsSource, ModelStore, ModelTrainer, SampleReader, SampleRecorder

MIN_TRAINING_SAMPLES = 30


def collect_samples(
    source: MetricsSource,
    recorder: SampleRecorder,
    *,
    count: int,
    interval_s: float,
    sleep: Callable[[float], None],
) -> int:
    """Enregistre `count` échantillons de trafic **normal** ; retourne le nombre écrit."""
    for i in range(count):
        recorder.record(source.sample())
        if i < count - 1:
            sleep(interval_s)
    return count


def train_model(reader: SampleReader, trainer: ModelTrainer, store: ModelStore) -> int:
    """Entraîne sur le jeu de données, sauvegarde le modèle ; retourne le nombre d'échantillons."""
    samples = reader.read_all()
    if len(samples) < MIN_TRAINING_SAMPLES:
        raise ValueError(
            f"{len(samples)} échantillons, il en faut au moins {MIN_TRAINING_SAMPLES} "
            "pour apprendre le trafic normal"
        )
    store.save(trainer.fit(samples))
    return len(samples)
