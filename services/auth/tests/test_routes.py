"""Couche API : codes HTTP, contrat du front, aucune fuite de secret. Aucune base réelle."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.security import Argon2PasswordHasher, JwtTokenIssuer
from app.api.routes import build_router
from app.application.use_cases import LoginUser, RegisterUser
from tests.fakes import HealthyProbe, InMemoryUserRepository, RecordingPublisher

SECRET = "x" * 32
REGISTER = {
    "name": "Alice Martin",
    "email": "Alice@Resilience.local",
    "number": "0612345678",
    "password": "motdepasse-fictif",
}


def _client(*, database_up: bool = True) -> tuple[TestClient, RecordingPublisher]:
    users, hasher = InMemoryUserRepository(), Argon2PasswordHasher()
    tokens, publisher = JwtTokenIssuer(SECRET, 60), RecordingPublisher()
    app = FastAPI()
    app.include_router(
        build_router(
            lambda: RegisterUser(users, hasher, tokens, publisher, 100_000),
            lambda: LoginUser(users, hasher, tokens, publisher),
            HealthyProbe(database_up),
        )
    )
    return TestClient(app, raise_server_exceptions=False), publisher


def test_inscription_puis_connexion_renvoient_le_contrat_du_front() -> None:
    client, _ = _client()

    registered = client.post("/auth/register", json=REGISTER)
    logged = client.post(
        "/auth/login", json={"email": "alice@resilience.local", "password": REGISTER["password"]}
    )

    assert registered.status_code == 200
    resp = registered.json()["resp"]
    assert resp["_id"] and resp["balance_cents"] == 100_000
    assert resp["email"] == "alice@resilience.local"
    assert "password" not in str(registered.json())
    assert logged.status_code == 200 and logged.json()["token"]


def test_email_deja_inscrit_donne_409() -> None:
    client, _ = _client()
    client.post("/auth/register", json=REGISTER)

    response = client.post("/auth/register", json={**REGISTER, "number": "0699999999"})

    assert response.status_code == 409


def test_mauvais_mot_de_passe_donne_401_sans_fuiter_la_saisie() -> None:
    client, publisher = _client()
    client.post("/auth/register", json=REGISTER)

    response = client.post(
        "/auth/login", json={"email": "alice@resilience.local", "password": "mauvais-mdp"}
    )

    assert response.status_code == 401
    assert "mauvais-mdp" not in str(publisher.events)


def test_saisie_invalide_donne_422() -> None:
    client, _ = _client()

    assert client.post("/auth/register", json={**REGISTER, "password": "court"}).status_code == 422
    assert client.post("/auth/register", json={**REGISTER, "number": "abc"}).status_code == 422


def test_health_signale_une_base_indisponible() -> None:
    client, _ = _client(database_up=False)

    assert client.get("/health").status_code == 503
