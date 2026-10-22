"""Routes du back-office : codes HTTP, Retry-After, jeton requis, aucune logique métier."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.memory_stores import (
    InMemoryAccessJournal,
    InMemoryFaceSessionStore,
    InMemoryLockoutStore,
    InMemoryRoleStore,
)
from app.api.routes import build_admin_router
from app.application.backoffice_admin import BackOfficeAdmin
from app.application.backoffice_login import BackOfficeLogin
from app.domain.models import NewUser, Role
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
OPERATOR = "ops@resilience.test"
ALICE = "alice@resilience.test"


async def _seed(users: InMemoryUserRepository) -> None:
    for i, email in enumerate((ADMIN, OPERATOR, ALICE)):
        await users.create(NewUser(email, email, f"060000000{i}", PlainHasher().hash("bon-mdp")), 0)


class Env:
    def __init__(self, *, agent_broken: bool = False) -> None:
        import anyio

        self.users = InMemoryUserRepository()
        anyio.run(_seed, self.users)
        self.faces = FakeFaceVerifier({ADMIN, OPERATOR, ALICE}, broken=agent_broken)
        self.roles = InMemoryRoleStore({ADMIN: Role.ADMIN, OPERATOR: Role.OPERATOR})
        self.lockouts = InMemoryLockoutStore()
        journal = InMemoryAccessJournal()
        clock = FakeClock()
        publisher = RecordingPublisher()
        tokens = StaticTokenIssuer()
        login = BackOfficeLogin(
            self.users,
            PlainHasher(),
            tokens,
            FakeCamera(),
            self.faces,
            RecordingLed(),
            self.lockouts,
            InMemoryFaceSessionStore(),
            clock,
            publisher,
            self.roles,
            journal,
        )
        admin = BackOfficeAdmin(self.users, self.roles, self.lockouts, journal, clock, publisher)
        app = FastAPI()
        app.include_router(build_admin_router(lambda: login, lambda: admin, tokens))
        self.client = TestClient(app, raise_server_exceptions=False)

    def connect(self, identifier: str) -> dict[str, str]:
        self.client.post("/auth/admin/identify", json={"identifier": identifier})
        body = self.client.post(
            "/auth/admin/login", json={"identifier": identifier, "password": "bon-mdp"}
        ).json()
        return {"Authorization": f"Bearer {body['token']}"}


def test_parcours_complet_visage_puis_mot_de_passe() -> None:
    env = Env()

    identified = env.client.post("/auth/admin/identify", json={"identifier": ADMIN})
    logged = env.client.post("/auth/admin/login", json={"identifier": ADMIN, "password": "bon-mdp"})

    assert identified.status_code == 200
    assert logged.status_code == 200
    assert logged.json() == {
        "token": f"admin-{ADMIN}",
        "identifier": ADMIN,
        "name": ADMIN,
        "role": "admin",
    }


def test_mot_de_passe_sans_visage_donne_403() -> None:
    env = Env()

    response = env.client.post(
        "/auth/admin/login", json={"identifier": ADMIN, "password": "bon-mdp"}
    )

    assert response.status_code == 403


def test_visage_refuse_donne_403_puis_423_avec_retry_after() -> None:
    env = Env()
    env.faces.present = False

    first = env.client.post("/auth/admin/identify", json={"identifier": ADMIN})
    second = env.client.post("/auth/admin/identify", json={"identifier": ADMIN})
    third = env.client.post("/auth/admin/identify", json={"identifier": ADMIN})

    assert (first.status_code, second.status_code) == (403, 403)
    assert third.status_code == 423 and int(third.headers["Retry-After"]) > 0


def test_mauvais_mot_de_passe_donne_401() -> None:
    env = Env()
    env.client.post("/auth/admin/identify", json={"identifier": ADMIN})

    response = env.client.post("/auth/admin/login", json={"identifier": ADMIN, "password": "faux"})

    assert response.status_code == 401


def test_agent_en_panne_donne_503() -> None:
    env = Env(agent_broken=True)

    response = env.client.post("/auth/admin/identify", json={"identifier": ADMIN})

    assert response.status_code == 503


def test_compte_sans_habilitation_donne_403_motif_no_role() -> None:
    env = Env()
    env.client.post("/auth/admin/identify", json={"identifier": ALICE})

    response = env.client.post(
        "/auth/admin/login", json={"identifier": ALICE, "password": "bon-mdp"}
    )

    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "no_role"


def test_routes_d_administration_exigent_un_jeton_de_back_office() -> None:
    env = Env()

    missing = env.client.get("/auth/admin/habilitations")
    customer = env.client.get(
        "/auth/admin/habilitations", headers={"Authorization": "Bearer token-client"}
    )

    assert (missing.status_code, customer.status_code) == (401, 401)


def test_admin_habilite_puis_retire_un_compte() -> None:
    env = Env()
    headers = env.connect(ADMIN)

    granted = env.client.post(
        "/auth/admin/habilitations",
        json={"identifier": ALICE, "role": "operator"},
        headers=headers,
    )
    listed = env.client.get("/auth/admin/habilitations", headers=headers).json()
    revoked = env.client.post(
        "/auth/admin/habilitations/revoke", json={"identifier": ALICE}, headers=headers
    )

    assert granted.status_code == 200 and revoked.status_code == 200
    assert {"identifier": ALICE, "role": "operator"} in listed
    assert ALICE not in [
        h["identifier"] for h in env.client.get("/auth/admin/habilitations", headers=headers).json()
    ]


def test_operateur_lit_mais_ne_modifie_pas() -> None:
    env = Env()
    headers = env.connect(OPERATOR)

    read = env.client.get("/auth/admin/journal", headers=headers)
    write = env.client.post(
        "/auth/admin/habilitations", json={"identifier": ALICE, "role": "admin"}, headers=headers
    )

    assert read.status_code == 200 and write.status_code == 403


def test_codes_404_compte_inconnu_et_409_auto_retrait() -> None:
    env = Env()
    headers = env.connect(ADMIN)

    unknown = env.client.post(
        "/auth/admin/habilitations",
        json={"identifier": "inconnu@resilience.test", "role": "operator"},
        headers=headers,
    )
    self_revoke = env.client.post(
        "/auth/admin/habilitations/revoke", json={"identifier": ADMIN}, headers=headers
    )

    assert (unknown.status_code, self_revoke.status_code) == (404, 409)


def test_admin_debloque_un_identifiant() -> None:
    env = Env()
    headers = env.connect(ADMIN)
    env.faces.present = False
    for _ in range(2):
        env.client.post("/auth/admin/identify", json={"identifier": ALICE})

    locked = env.client.get("/auth/admin/lockouts", headers=headers).json()
    unlocked = env.client.post(
        "/auth/admin/lockouts/unlock", json={"identifier": ALICE}, headers=headers
    )

    assert [entry["identifier"] for entry in locked] == [ALICE]
    assert unlocked.status_code == 200
    assert env.client.get("/auth/admin/lockouts", headers=headers).json() == []


def test_me_renvoie_le_role_courant() -> None:
    env = Env()
    headers = env.connect(OPERATOR)

    response = env.client.get("/auth/admin/me", headers=headers)

    assert response.json() == {"identifier": OPERATOR, "role": "operator"}
