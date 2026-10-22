"""API de l'agent : jeton obligatoire, codes HTTP, échec fermé."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import build_router
from app.application.face_agent import FaceAgent
from tests.test_face_agent import ALICE, BOB, FakeEmbedder, FakeSource, MemoryTemplates

TOKEN = "t" * 32
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _client(embedding: list[float], *, camera_broken: bool = False) -> TestClient:
    agent = FaceAgent(
        FakeSource(broken=camera_broken), FakeEmbedder(embedding), MemoryTemplates(a=ALICE), 0.9
    )
    app = FastAPI()
    app.include_router(build_router(agent, TOKEN))
    return TestClient(app)


def test_sans_jeton_ou_mauvais_jeton_401() -> None:
    client = _client(ALICE)

    assert client.post("/camera/start").status_code == 401
    assert client.post("/camera/start", headers={"Authorization": "Bearer x"}).status_code == 401
    assert client.post("/verify", json={"identifier": "a"}).status_code == 401


def test_parcours_demarrer_verifier_arreter() -> None:
    client = _client(ALICE)

    assert client.post("/camera/start", headers=AUTH).json() == {"status": "on"}
    assert client.post("/verify", json={"identifier": "a"}, headers=AUTH).json() == {"match": True}
    assert client.post("/camera/stop", headers=AUTH).json() == {"status": "off"}


def test_autre_visage_match_faux() -> None:
    client = _client(BOB)
    client.post("/camera/start", headers=AUTH)

    assert client.post("/verify", json={"identifier": "a"}, headers=AUTH).json() == {"match": False}


def test_verifier_sans_demarrer_503() -> None:
    client = _client(ALICE)

    assert client.post("/verify", json={"identifier": "a"}, headers=AUTH).status_code == 503


def test_camera_absente_503() -> None:
    client = _client(ALICE, camera_broken=True)

    assert client.post("/camera/start", headers=AUTH).status_code == 503
