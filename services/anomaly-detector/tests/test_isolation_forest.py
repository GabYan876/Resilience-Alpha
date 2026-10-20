import random

from app.adapters.isolation_forest import IsolationForestTrainer, JoblibModelStore
from app.domain.models import MetricSample
from tests.fakes import FLOOD


def normal_samples(n: int = 300, seed: int = 1) -> list[MetricSample]:
    rng = random.Random(seed)
    return [
        MetricSample(
            request_rate=rng.uniform(5, 40),
            error_ratio=rng.uniform(0, 0.01),
            latency_p95_s=rng.uniform(0.02, 0.12),
            up=1.0,
        )
        for _ in range(n)
    ]


def test_trafic_normal_n_est_pas_signale():
    model = IsolationForestTrainer().fit(normal_samples())
    false_alarms = [s for s in normal_samples(100, seed=2) if model.evaluate(s).anomalous]
    assert false_alarms == []


def test_flood_est_signale_avec_un_score_superieur_au_normal():
    model = IsolationForestTrainer().fit(normal_samples())
    flood = model.evaluate(FLOOD)
    normal = model.evaluate(normal_samples(1, seed=3)[0])
    assert flood.anomalous
    assert flood.score > normal.score


def test_modele_sauvegarde_puis_recharge_juge_pareil(tmp_path):
    model = IsolationForestTrainer().fit(normal_samples())
    store = JoblibModelStore(tmp_path / "sous" / "model.joblib")
    store.save(model)
    assert store.load().evaluate(FLOOD) == model.evaluate(FLOOD)
