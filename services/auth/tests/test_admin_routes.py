"""Routes de connexion du back-office : codes HTTP, Retry-After, aucune logique métier."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.memory_stores import InMemoryFaceSessionStore, InMemoryLockoutStore
from app.api.routes import build_admin_router
from app.application.backoffice_login import BackOfficeLogin
from app.domain.models import NewUser
from tests.fakes import (
    FakeCamera,
    FakeClock,
    FakeFaceVerifier,
    InMemoryUserRepository,
    PlainHasher,
    RecordingLed,
    RecordingPublisher,
    StaticTokenIssuer,
)

ADMIN = "admin@resilience.test"


async def _seed(users: InMemoryUserRepository) -> None:
    await users.create(NewUser("Admin", ADMIN, "0600000000", PlainHasher().hash("bon-mdp")), 0)


def _client(*, agent_broken: bool = False) -> tuple[TestClient, FakeFaceVerifier]:
    import anyio

    users = InMemoryUserRepository()
    anyio.run(_seed, users)
    faces = FakeFaceVerifier({ADMIN}, broken=agent_broken)
    login = BackOfficeLogin(
        users,
        PlainHasher(),
        StaticTokenIssuer(),
        FakeCamera(),
        faces,
        RecordingLed(),
        InMemoryLockoutStore(),
        InMemoryFaceSessionStore(),
        FakeClock(),
        RecordingPublisher(),
    )
    app = FastAPI()
    app.include_router(build_admin_router(lambda: login))
    return TestClient(app, raise_server_exceptions=False), faces


def test_parcours_complet_visage_puis_mot_de_passe() -> None:
    client, _ = _client()

    identified = client.post("/auth/admin/identify", json={"identifier": ADMIN})
    logged = client.post("/auth/admin/login", json={"identifier": ADMIN, "password": "bon-mdp"})

    assert identified.status_code == 200
    assert logged.status_code == 200 and logged.json()["token"]


def test_mot_de_passe_sans_visage_donne_403() -> None:
    client, _ = _client()

    response = client.post("/auth/admin/login", json={"identifier": ADMIN, "password": "bon-mdp"})

    assert response.status_code == 403


def test_visage_refuse_donne_403_puis_423_avec_retry_after() -> None:
    client, faces = _client()
    faces.present = False

    first = client.post("/auth/admin/identify", json={"identifier": ADMIN})
    second = client.post("/auth/admin/identify", json={"identifier": ADMIN})
    third = client.post("/auth/admin/identify", json={"identifier": ADMIN})

    assert (first.status_code, second.status_code) == (403, 403)
    assert third.status_code == 423 and int(third.headers["Retry-After"]) > 0


def test_mauvais_mot_de_passe_donne_401() -> None:
    client, _ = _client()
    client.post("/auth/admin/identify", json={"identifier": ADMIN})

    response = client.post("/auth/admin/login", json={"identifier": ADMIN, "password": "faux"})

    assert response.status_code == 401


def test_agent_en_panne_donne_503() -> None:
    client, _ = _client(agent_broken=True)

    response = client.post("/auth/admin/identify", json={"identifier": ADMIN})

    assert response.status_code == 503
