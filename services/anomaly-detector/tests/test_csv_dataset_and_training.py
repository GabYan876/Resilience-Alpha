import pytest

from app.adapters.csv_dataset import CsvDataset
from app.application.training import MIN_TRAINING_SAMPLES, collect_samples, train_model
from tests.fakes import NORMAL, ScriptedSource


class StubTrainer:
    def fit(self, samples):
        self.seen = samples
        return "modele"


class MemoryStore:
    def save(self, model):
        self.saved = model


def test_csv_aller_retour_et_entete_unique(tmp_path):
    dataset = CsvDataset(tmp_path / "data" / "normal.csv")
    dataset.record(NORMAL)
    dataset.record(NORMAL)
    assert dataset.read_all() == [NORMAL, NORMAL]
    assert (tmp_path / "data" / "normal.csv").read_text().count("request_rate") == 1


def test_collecte_n_echantillons_et_attend_entre_deux(tmp_path):
    dataset = CsvDataset(tmp_path / "n.csv")
    pauses: list[float] = []
    written = collect_samples(
        ScriptedSource([NORMAL] * 3), dataset, count=3, interval_s=5, sleep=pauses.append
    )
    assert written == 3
    assert pauses == [5, 5]
    assert len(dataset.read_all()) == 3


def test_entrainement_sauvegarde_le_modele(tmp_path):
    dataset = CsvDataset(tmp_path / "n.csv")
    for _ in range(MIN_TRAINING_SAMPLES):
        dataset.record(NORMAL)
    store = MemoryStore()
    assert train_model(dataset, StubTrainer(), store) == MIN_TRAINING_SAMPLES
    assert store.saved == "modele"


def test_entrainement_refuse_un_jeu_trop_petit(tmp_path):
    dataset = CsvDataset(tmp_path / "n.csv")
    dataset.record(NORMAL)
    with pytest.raises(ValueError, match="au moins"):
        train_model(dataset, StubTrainer(), MemoryStore())
