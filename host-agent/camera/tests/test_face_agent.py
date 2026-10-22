"""Cas d'usage de l'agent avec des doubles : ni caméra, ni OpenCV, ni disque."""

from __future__ import annotations

import pytest

from app.application.face_agent import FaceAgent
from app.domain.errors import CameraError
from app.domain.similarity import cosine

ALICE = [1.0, 0.0, 0.0]
BOB = [0.0, 1.0, 0.0]


class FakeSource:
    def __init__(self, broken: bool = False) -> None:
        self.broken = broken
        self.is_on = False

    def open(self) -> None:
        if self.broken:
            raise CameraError("caméra introuvable")
        self.is_on = True

    def close(self) -> None:
        self.is_on = False

    def read(self) -> object:
        return object()


class FakeEmbedder:
    """Renvoie la file de gabarits donnée (None = pas exactement un visage), puis le dernier."""

    def __init__(self, *embeddings: list[float] | None) -> None:
        self._queue = list(embeddings)

    def embed(self, frame: object) -> list[float] | None:
        return self._queue.pop(0) if len(self._queue) > 1 else self._queue[0]


class MemoryTemplates:
    def __init__(self, **templates: list[float]) -> None:
        self.data = dict(templates)

    def get(self, identifier: str) -> list[float] | None:
        return self.data.get(identifier)

    def put(self, identifier: str, template: list[float]) -> None:
        self.data[identifier] = list(template)

    def delete(self, identifier: str) -> None:
        self.data.pop(identifier, None)


def _agent(embedder: FakeEmbedder, templates: MemoryTemplates, source: FakeSource | None = None):
    agent = FaceAgent(source or FakeSource(), embedder, templates, threshold=0.9, attempts=3)
    agent.start()
    return agent


def test_cosine() -> None:
    assert cosine(ALICE, ALICE) == pytest.approx(1.0)
    assert cosine(ALICE, BOB) == pytest.approx(0.0)
    assert cosine(ALICE, [1.0]) == -1.0  # tailles différentes
    assert cosine([0.0, 0.0, 0.0], ALICE) == -1.0


def test_visage_conforme_reconnu() -> None:
    assert _agent(FakeEmbedder(ALICE), MemoryTemplates(alice=ALICE)).verify("alice") is True


def test_autre_visage_rejete() -> None:
    assert _agent(FakeEmbedder(BOB), MemoryTemplates(alice=ALICE)).verify("alice") is False


def test_comparaison_1_pour_1_le_gabarit_d_un_autre_ne_compte_pas() -> None:
    templates = MemoryTemplates(alice=ALICE, bob=BOB)

    assert _agent(FakeEmbedder(ALICE), templates).verify("bob") is False


def test_identifiant_sans_gabarit_ou_sans_visage_rejete() -> None:
    assert _agent(FakeEmbedder(ALICE), MemoryTemplates()).verify("alice") is False
    assert _agent(FakeEmbedder(None), MemoryTemplates(alice=ALICE)).verify("alice") is False


def test_visage_trouve_apres_quelques_images_sans_visage() -> None:
    agent = _agent(FakeEmbedder(None, None, ALICE), MemoryTemplates(alice=ALICE))

    assert agent.verify("alice") is True


def test_verification_exige_la_camera_demarree() -> None:
    agent = FaceAgent(FakeSource(), FakeEmbedder(ALICE), MemoryTemplates(alice=ALICE), 0.9)

    with pytest.raises(CameraError):
        agent.verify("alice")


def test_arret_eteint_la_camera() -> None:
    source = FakeSource()
    agent = _agent(FakeEmbedder(ALICE), MemoryTemplates(), source)
    assert source.is_on

    agent.stop()

    assert not source.is_on
    with pytest.raises(CameraError):
        agent.verify("alice")


def test_camera_absente_leve_camera_error() -> None:
    agent = FaceAgent(FakeSource(broken=True), FakeEmbedder(ALICE), MemoryTemplates(), 0.9)

    with pytest.raises(CameraError):
        agent.start()


def test_enrolement_stocke_la_moyenne_des_echantillons() -> None:
    templates = MemoryTemplates()
    agent = _agent(FakeEmbedder([1.0, 0.0], None, [0.0, 1.0]), templates)

    agent.enroll("alice", samples=2)

    assert templates.data["alice"] == [0.5, 0.5]


def test_enrolement_echoue_sans_assez_d_images_exploitables() -> None:
    agent = _agent(FakeEmbedder(None), MemoryTemplates())

    with pytest.raises(CameraError):
        agent.enroll("alice", samples=2)
